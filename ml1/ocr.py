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
    timeout: float = 120
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
            timeout=float(os.getenv("PADDLEOCR_VL_TIMEOUT", "120")),
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
               settings: OcrSettings | None = None) -> str:
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
        timeout=(5, settings.timeout),
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
    if not boxes:
        logger.info("PaddleOCR-VL returned text without Spotting boxes; deriving line boxes locally")
        boxes = run_tesseract_ocr(image)["boxes"]
    return {"text": recognized_text, "boxes": boxes}


def run_tesseract_ocr(image: np.ndarray) -> dict[str, Any]:
    """Get local OCR text and line boxes as a fallback when Spotting has no geometry."""
    import pytesseract
    from pytesseract import Output

    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    data = pytesseract.image_to_data(
        rgb, lang="rus+eng", config="--psm 6", output_type=Output.DICT,
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
        left, top = int(data["left"][index]), int(data["top"][index])
        right = left + int(data["width"][index])
        bottom = top + int(data["height"][index])
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

