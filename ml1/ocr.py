"""Deterministic PaddleOCR-VL inference through a local llama.cpp server."""

import base64
import logging
import math
import os
import re
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np
import requests

logger = logging.getLogger(__name__)

_LOCATION_TOKEN = re.compile(r"<\|LOC_(\d{1,4})\|>")


class OcrResponseError(RuntimeError):
    """The model did not return a usable, complete transcription."""


class OcrTruncatedError(OcrResponseError):
    pass


@dataclass(frozen=True)
class OcrSettings:
    url: str = "http://127.0.0.1:8080/v1/chat/completions"
    timeout: float = 180
    max_tokens: int = 4096
    # The existing server needs the legacy marker. Recent llama.cpp versions
    # insert their own marker and need plain "OCR:" instead.
    # Verified 2026-10-12 on llama.cpp b11569 + PaddleOCR-VL-1.5: plain "OCR:"
    # transcribes the full page (CER 0.10), the legacy marker stops after
    # the header (CER 0.85). Default is plain; set PADDLEOCR_VL_LEGACY_MEDIA=1
    # only for llama.cpp builds older than the placeholder fix (ad19f21).
    legacy_media: bool = False

    def __post_init__(self):
        if not self.url.startswith(("http://", "https://")):
            raise ValueError("PADDLEOCR_VL_URL должен быть HTTP(S)-адресом")
        if not math.isfinite(self.timeout) or self.timeout <= 0:
            raise ValueError("PADDLEOCR_VL_TIMEOUT должен быть положительным")
        if self.max_tokens <= 0:
            raise ValueError("PADDLEOCR_VL_MAX_TOKENS должен быть положительным")

    @classmethod
    def from_env(cls):
        legacy = os.getenv("PADDLEOCR_VL_LEGACY_MEDIA", "0").lower()
        if legacy not in {"0", "1", "false", "true"}:
            raise ValueError("PADDLEOCR_VL_LEGACY_MEDIA: допустимы 0 или 1")
        return cls(
            url=os.getenv("PADDLEOCR_VL_URL", cls.url),
            timeout=float(os.getenv("PADDLEOCR_VL_TIMEOUT", "180")),
            max_tokens=int(os.getenv("PADDLEOCR_VL_MAX_TOKENS", "4096")),
            legacy_media=legacy in {"1", "true"},
        )


def read_transcription(payload: Any) -> str:
    if not isinstance(payload, dict):
        raise OcrResponseError("OCR-модель вернула неверный формат ответа")
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise OcrResponseError("В ответе OCR-модели нет результата распознавания")
    choice = choices[0]
    if choice.get("finish_reason") == "length":
        raise OcrTruncatedError(
            "OCR-текст обрезан лимитом токенов. Увеличьте PADDLEOCR_VL_MAX_TOKENS "
            "и контекст llama-server или распознайте меньший фрагмент документа."
        )
    if choice.get("finish_reason") not in {None, "stop"}:
        raise OcrResponseError("OCR-модель не завершила распознавание текста")
    message = choice.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str) or not content.strip():
        raise OcrResponseError(
            "OCR-модель вернула пустой текст. Проверьте читаемость снимка, "
            "соответствие модели и mmproj, а также PADDLEOCR_VL_LEGACY_MEDIA."
        )
    return content.strip()


def run_vl_ocr(image: np.ndarray, task: str = "OCR:", *,
               settings: OcrSettings | None = None,
               timeout: float | None = None) -> str:
    settings = settings or OcrSettings.from_env()
    ok, buf = cv2.imencode(".png", image)
    if not ok:
        raise ValueError("Не удалось закодировать изображение в PNG")
    img_b64 = base64.b64encode(buf.tobytes()).decode("ascii")
    prompt = ("<__media__>" if settings.legacy_media else "") + task

    response = requests.post(
        settings.url,
        json={
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                    {"type": "text", "text": prompt},
                ],
            }],
            "temperature": 0,
            "max_tokens": settings.max_tokens,
            "stream": False,
        },
        timeout=(5, settings.timeout if timeout is None else timeout),
    )
    response.raise_for_status()
    try:
        payload = response.json()
    except ValueError as exc:
        raise OcrResponseError("OCR-модель вернула некорректный JSON") from exc
    return read_transcription(payload)


def run_ocr(image: np.ndarray) -> dict[str, Any]:
    """Read text and line boxes from PaddleOCR-VL's grounded Spotting task."""
    try:
        raw = run_vl_ocr(image, "Spotting:")
    except (requests.RequestException, OcrResponseError) as exc:
        logger.warning("PaddleOCR-VL request failed (%s); using local text detection",
                       type(exc).__name__)
        fallback = run_tesseract_ocr(image)
        if not fallback["text"]:
            raise OcrResponseError("OCR-модель недоступна, а локальное распознавание не нашло текст") from exc
        return fallback
    tokens = list(_LOCATION_TOKEN.finditer(raw))
    width, height = image.shape[1], image.shape[0]
    boxes = []
    text_lines = []
    content_cursor = 0

    for index in range(0, len(tokens) - 7, 8):
        group = tokens[index:index + 8]
        line = raw[content_cursor:group[0].start()].strip()
        # Spotting emits four (x, y) corners as LOC tokens normalized to 0..1000.
        values = [int(token.group(1)) for token in group]
        content_cursor = group[-1].end()
        if line:
            text_lines.append(line)
        if not line or any(value > 1000 for value in values):
            continue

        xs, ys = values[0::2], values[1::2]
        x1, y1 = min(xs) * width / 1000, min(ys) * height / 1000
        x2, y2 = max(xs) * width / 1000, max(ys) * height / 1000
        if x2 <= x1 or y2 <= y1:
            continue

        boxes.append({
            "field": None,
            "text": line,
            "bbox": [round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)],
            "confidence": None,
            "source": "spotting",
            "page": 1,
        })

    # Keep text that has no complete coordinate sequence instead of dropping it.
    trailing = _LOCATION_TOKEN.sub("", raw[content_cursor:]).strip()
    if trailing:
        text_lines.append(trailing)
    recognized_text = "\n".join(text_lines).strip()
    if not recognized_text:
        recognized_text = _LOCATION_TOKEN.sub("", raw).strip()
    if not recognized_text:
        raise OcrResponseError("OCR-модель не вернула распознанный текст")

    spotting_text = recognized_text
    if not boxes:
        logger.info("PaddleOCR-VL returned text without Spotting boxes; deriving line boxes locally")
        boxes = run_tesseract_ocr(image)["boxes"]

    # Spotting provides geometry for the image overlay. OCR is a separate
    # model task trained to transcribe the page as a whole, so use its text
    # and retain any lines that Spotting found but OCR omitted.
    try:
        settings = OcrSettings.from_env()
        transcription = run_vl_ocr(
            image, "OCR:", settings=settings, timeout=min(settings.timeout, 90.0),
        ).strip()
        if transcription:
            recognized_text = _append_unique_lines(transcription, spotting_text.splitlines())
    except (requests.RequestException, OcrResponseError) as exc:
        logger.warning("Full-page OCR pass unavailable (%s); keeping Spotting transcription",
                       type(exc).__name__)

    # PaddleOCR-VL is the primary transcription. A contrast-enhanced local
    # pass recovers clear lines it omitted (dates, order numbers, headings),
    # while the overlap check prevents duplicate lines from changing parsing.
    try:
        supplement = run_tesseract_ocr(image, enhanced=True)
        existing_lines = recognized_text.splitlines()
        existing_tokens = _ocr_tokens(recognized_text)
        added = 0
        for box in supplement["boxes"]:
            line = box["text"].strip()
            line_tokens = _ocr_tokens(line)
            if (
                (box.get("confidence") or 0) < 0.72
                or len(re.findall(r"[0-9A-Za-zА-Яа-яЁё]", line)) < 6
                or not line_tokens
                or len(line_tokens & existing_tokens) / len(line_tokens) >= 0.78
            ):
                continue
            recognized_text += "\n" + line
            existing_lines.append(line)
            existing_tokens.update(line_tokens)
            boxes.append({**box, "source": "tesseract_supplement"})
            added += 1
            if added >= 40:
                break
        if added:
            logger.info("Local OCR recovered %d additional high-confidence lines", added)
    except Exception as exc:
        logger.warning("Local OCR supplement unavailable (%s)", type(exc).__name__)
    return {"text": recognized_text, "boxes": boxes}


def _ocr_tokens(text: str) -> set[str]:
    return set(re.findall(r"[0-9A-Za-zА-Яа-яЁё]{2,}", text.casefold()))


def _append_unique_lines(text: str, lines: list[str]) -> str:
    result = text.strip()
    known = _ocr_tokens(result)
    for line in lines:
        line = line.strip()
        tokens = _ocr_tokens(line)
        if not tokens or len(tokens & known) / len(tokens) >= 0.78:
            continue
        result += "\n" + line
        known.update(tokens)
    return result


def run_tesseract_ocr(image: np.ndarray, *, enhanced: bool = False) -> dict[str, Any]:
    """Get local OCR text and line boxes as a fallback when Spotting has no geometry."""
    import pytesseract
    from pytesseract import Output

    scale = 1.0
    if enhanced:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        contrast = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
        blurred = cv2.GaussianBlur(contrast, (0, 0), 1.1)
        sharpened = cv2.addWeighted(contrast, 1.45, blurred, -0.45, 0)
        scale = min(1.5, max(1.0, 2600 / max(image.shape[:2])))
        ocr_image = cv2.resize(sharpened, None, fx=scale, fy=scale,
                               interpolation=cv2.INTER_CUBIC)
    else:
        ocr_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    data = pytesseract.image_to_data(
        ocr_image, lang="rus+eng", config="--oem 1 --psm 6", output_type=Output.DICT,
    )
    grouped: dict[tuple[int, int, int], dict[str, Any]] = {}
    for index, raw_text in enumerate(data["text"]):
        text = raw_text.strip()
        try:
            confidence = float(data["conf"][index])
        except (TypeError, ValueError):
            continue
        if not text or confidence < 0:
            continue

        key = (data["block_num"][index], data["par_num"][index], data["line_num"][index])
        left = round(int(data["left"][index]) / scale)
        top = round(int(data["top"][index]) / scale)
        right = round((int(data["left"][index]) + int(data["width"][index])) / scale)
        bottom = round((int(data["top"][index]) + int(data["height"][index])) / scale)
        line = grouped.setdefault(key, {
            "words": [], "left": left, "top": top, "right": right, "bottom": bottom,
            "confidences": [],
        })
        line["words"].append(text)
        line["left"] = min(line["left"], left)
        line["top"] = min(line["top"], top)
        line["right"] = max(line["right"], right)
        line["bottom"] = max(line["bottom"], bottom)
        line["confidences"].append(confidence / 100)

    boxes = []
    text_lines = []
    for line in grouped.values():
        text = " ".join(line["words"])
        text_lines.append(text)
        boxes.append({
            "field": None,
            "text": text,
            "bbox": [line["left"], line["top"], line["right"], line["bottom"]],
            "confidence": round(sum(line["confidences"]) / len(line["confidences"]), 4),
            "source": "tesseract",
            "page": 1,
        })

    return {"text": "\n".join(text_lines), "boxes": boxes}

