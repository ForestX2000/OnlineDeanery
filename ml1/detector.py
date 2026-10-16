"""Optional CPU signature/stamp detector; missing weights never mean absence.

Два независимых источника (v0, замерено на baton.png 2026-10-12):
- подпись: Mels22 YOLO11s 4cls (signature/initials/redaction/date) — находит
  подпись conf 0.349 там, где tech4humans давал 0 боксов;
- печать: собственная YOLOv8n (signature/stamp, StaVer + синтетика) — находит
  печать conf 0.513 (бокс грубый, см. CONTEXT.md).
Без файла весов источник возвращает status disabled/error, а поля —
None («проверка не выполнена»), а не «печати нет» (см. ml2/visual.py).
Исключение: печать без YOLO ищется классикой detect_blue_seal (синее кольцо);
срабатывает только при сильном отклике, иначе stamp остаётся None.
"""

import ast
import importlib
import json
import logging
import math
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def unavailable(status: str) -> dict:
    return {"status": status, "signature": None, "stamp": None, "boxes": []}


def letterbox(image: np.ndarray, size: int) -> tuple[np.ndarray, float, int, int]:
    h, w = image.shape[:2]
    scale = min(size / w, size / h)
    width, height = round(w * scale), round(h * scale)
    left, top = (size - width) // 2, (size - height) // 2
    resized = cv2.resize(image, (width, height), interpolation=cv2.INTER_LINEAR)
    padded = cv2.copyMakeBorder(resized, top, size - height - top,
                               left, size - width - left, cv2.BORDER_CONSTANT,
                               value=(114, 114, 114))
    tensor = padded[:, :, ::-1].transpose(2, 0, 1)[None].astype(np.float32) / 255.0
    return np.ascontiguousarray(tensor), scale, left, top


def nms(boxes: np.ndarray, scores: np.ndarray, threshold: float = 0.45) -> list[int]:
    order = np.argsort(-scores, kind="stable")[:1000]
    keep = []
    while order.size and len(keep) < 100:
        index = int(order[0])
        keep.append(index)
        rest = order[1:]
        a, b = boxes[index], boxes[rest]
        widths = np.maximum(0, np.minimum(a[2], b[:, 2]) - np.maximum(a[0], b[:, 0]))
        heights = np.maximum(0, np.minimum(a[3], b[:, 3]) - np.maximum(a[1], b[:, 1]))
        intersection = widths * heights
        area_a = (a[2] - a[0]) * (a[3] - a[1])
        area_b = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
        iou = intersection / np.maximum(area_a + area_b - intersection, 1e-9)
        order = rest[iou <= threshold]
    return keep


def _ring_support(ink, cx, cy, radius, height, width, samples=64):
    angles = np.linspace(0, 2 * math.pi, samples, endpoint=False)
    xs = np.clip((cx + radius * np.cos(angles)).astype(int), 0, width - 1)
    ys = np.clip((cy + radius * np.sin(angles)).astype(int), 0, height - 1)
    return float(ink[ys, xs].mean())


def detect_blue_seal(image):
    """Find a clearly visible circular blue stamp; weak color patterns are ignored."""
    height, width = image.shape[:2]
    if min(height, width) < 200:
        return None
    scale = min(1.0, 800.0 / max(height, width))
    small = image if scale == 1.0 else cv2.resize(
        image, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA)
    out_height, out_width = small.shape[:2]
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    ink = (cv2.inRange(hsv, np.array([85, 35, 60]),
                       np.array([145, 255, 255])) > 0).astype(np.float32)
    if float(ink.mean()) < 0.0005:
        return None
    min_dim = min(out_height, out_width)
    radii = range(int(min_dim * 0.06), int(min_dim * 0.2) + 1,
                  max(4, int(min_dim * 0.015)))
    step = max(12, int(min_dim * 0.04))
    best = (0.0, 0.0, 0.0, 0)
    for cy in range(step, out_height - step, step):
        for cx in range(step, out_width - step, step):
            for radius in radii:
                if cx - radius < 0 or cy - radius < 0:
                    continue
                if cx + radius >= out_width or cy + radius >= out_height:
                    continue
                score = _ring_support(ink, float(cx), float(cy), float(radius),
                                      out_height, out_width, samples=48)
                if score > best[0]:
                    best = (score, float(cx), float(cy), radius)
    score, cx, cy, radius = best
    for _ in range(2):
        improved = False
        for dcx in (-step / 4, 0.0, step / 4):
            for dcy in (-step / 4, 0.0, step / 4):
                for dr in (-2.0, 0.0, 2.0):
                    cand = _ring_support(ink, cx + dcx, cy + dcy, radius + dr,
                                         out_height, out_width)
                    if cand > score:
                        score, cx, cy, radius = cand, cx + dcx, cy + dcy, radius + dr
                        improved = True
        if not improved:
            break
    if score < 0.5 or radius <= 0:
        return None
    box = [(cx - radius) / scale, (cy - radius) / scale,
           (cx + radius) / scale, (cy + radius) / scale]
    box = [round(max(0.0, min(v, bound)), 2)
           for v, bound in zip(box, [width, height, width, height])]
    if box[2] <= box[0] or box[3] <= box[1]:
        return None
    return {"field": "stamp", "text": "\u041f\u0435\u0447\u0430\u0442\u044c", "bbox": box,
            "confidence": round(min(0.9, 0.35 + score * 0.6), 6),
            "source": "color", "page": 1}


class SignatureStampDetector:
    """YOLO-ONNX детектор с фильтром нужных классов.

    keep — подмножество имён классов модели (например, {"signature"} для
    Mels22 или {"stamp"} для собственной). Проверяется, что keep входит
    в names модели; выход [1, 4+nc, N] без встроенного NMS.
    """

    def __init__(self, session, keep: frozenset):
        self.session = session
        self.keep = keep
        metadata = session.get_modelmeta().custom_metadata_map
        raw_names = ast.literal_eval(metadata.get("names", "{}"))
        if isinstance(raw_names, list):
            raw_names = dict(enumerate(raw_names))
        if not isinstance(raw_names, dict):
            raise ValueError("ONNX metadata.names отсутствует")
        self.names = {int(k): str(v).lower().strip() for k, v in raw_names.items()}
        if not keep or not keep <= set(self.names.values()):
            raise ValueError(f"Модель не содержит классы {sorted(keep)}: {sorted(set(self.names.values()))}")
        if metadata.get("task") != "detect":
            raise ValueError("ONNX должна быть моделью object detection")
        inputs = session.get_inputs()
        if len(inputs) != 1:
            raise ValueError("Ожидается один вход YOLO")
        inp = inputs[0]
        shape = inp.shape
        if (len(shape) != 4 or shape[:2] != [1, 3] or not isinstance(shape[2], int)
                or shape[2] != shape[3] or shape[2] < 32 or inp.type != "tensor(float)"):
            raise ValueError("Экспортируйте YOLO в ONNX: batch=1, dynamic=False, half=False")
        self.input_name, self.size = inp.name, shape[2]
        self.num_classes = len(self.names)

    def predict(self, image: np.ndarray, threshold: float) -> dict:
        tensor, scale, left, top = letterbox(image, self.size)
        output = np.asarray(self.session.run(None, {self.input_name: tensor})[0])
        if (output.ndim != 3 or output.shape[0] != 1
                or output.shape[1] != 4 + self.num_classes):
            raise ValueError("Нужен YOLO ONNX без встроенного NMS: [1,4+nc,N]")
        rows = output[0].T
        if not np.isfinite(rows).all():
            raise ValueError("YOLO вернула нечисловые координаты")
        class_ids = rows[:, 4:].argmax(axis=1)
        confidence = rows[np.arange(len(rows)), class_ids + 4]
        valid = ((confidence >= threshold) & (confidence <= 1)
                 & (rows[:, 2] > 0) & (rows[:, 3] > 0))
        rows, class_ids, confidence = rows[valid], class_ids[valid], confidence[valid]
        boxes = np.empty((len(rows), 4), dtype=np.float32)
        boxes[:, :2] = rows[:, :2] - rows[:, 2:4] / 2
        boxes[:, 2:] = rows[:, :2] + rows[:, 2:4] / 2
        boxes[:, [0, 2]] = np.clip((boxes[:, [0, 2]] - left) / scale, 0, image.shape[1])
        boxes[:, [1, 3]] = np.clip((boxes[:, [1, 3]] - top) / scale, 0, image.shape[0])
        valid = (boxes[:, 2] > boxes[:, 0]) & (boxes[:, 3] > boxes[:, 1])
        boxes, class_ids, confidence = boxes[valid], class_ids[valid], confidence[valid]
        detections = []
        for class_id, name in self.names.items():
            if name not in self.keep:
                continue
            indices = np.flatnonzero(class_ids == class_id)
            for local in nms(boxes[indices], confidence[indices]):
                index = indices[local]
                detections.append({
                    "field": "signature" if name == "signature" else "stamp",
                    "text": "Подпись" if name == "signature" else "Печать",
                    "bbox": [round(float(v), 2) for v in boxes[index]],
                    "confidence": round(float(confidence[index]), 6), "source": "yolo", "page": 1,
                })
        present = {b["field"] for b in detections}
        return {"status": "ready",
                "signature": ("signature" in present) if "signature" in self.keep else None,
                "stamp": ("stamp" in present) if "stamp" in self.keep else None,
                "boxes": detections}


@lru_cache(maxsize=4)
def load_detector(path: str, modified: int, keep: tuple) -> SignatureStampDetector:
    import onnxruntime as ort
    options = ort.SessionOptions()
    options.intra_op_num_threads = int(os.getenv("YOLO_INTRA_OP_THREADS", "0"))
    return SignatureStampDetector(ort.InferenceSession(path, sess_options=options,
                                                       providers=["CPUExecutionProvider"]),
                                  frozenset(keep))


# ---------- RF-DETR support ----------

_RFDETR_FIELD_ALIASES = {
    "signature": "signature", "подпись": "signature", "sig": "signature",
    "stamp": "stamp", "печать": "stamp", "seal": "stamp", "print": "stamp",
}


def _rfdetr_field_name(class_id: int, names: dict[int, str]) -> str | None:
    name = str(names.get(class_id, class_id)).lower().strip()
    return _RFDETR_FIELD_ALIASES.get(name)


def _rfdetr_detections(boxes: np.ndarray, scores: np.ndarray, labels: np.ndarray,
                       names: dict[int, str], threshold: float,
                       image_h: int, image_w: int) -> list[dict]:
    """Convert RF-DETR raw outputs to detection dicts in pixel coords [x1,y1,x2,y2]."""
    detections: list[dict] = []
    keep = scores >= threshold
    boxes, scores, labels = boxes[keep], scores[keep], labels[keep]
    if len(boxes) == 0:
        return detections

    order = np.argsort(-scores, kind="stable")
    boxes, scores, labels = boxes[order], scores[order], labels[order]

    # Simple per-class NMS
    suppressed = np.zeros(len(boxes), dtype=bool)
    for i in range(len(boxes)):
        if suppressed[i]:
            continue
        for j in range(i + 1, len(boxes)):
            if suppressed[j] or labels[i] != labels[j]:
                continue
            x1 = max(float(boxes[i][0]), float(boxes[j][0]))
            y1 = max(float(boxes[i][1]), float(boxes[j][1]))
            x2 = min(float(boxes[i][2]), float(boxes[j][2]))
            y2 = min(float(boxes[i][3]), float(boxes[j][3]))
            inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
            area_i = max(0.0, float(boxes[i][2]) - float(boxes[i][0])) * max(
                0.0, float(boxes[i][3]) - float(boxes[i][1]))
            area_j = max(0.0, float(boxes[j][2]) - float(boxes[j][0])) * max(
                0.0, float(boxes[j][3]) - float(boxes[j][1]))
            iou = inter / max(area_i + area_j - inter, 1e-9)
            if iou > 0.45:
                suppressed[j] = True

    for i in range(len(boxes)):
        if suppressed[i]:
            continue
        x1, y1, x2, y2 = (float(v) for v in boxes[i])
        x1 = max(0.0, min(x1, image_w))
        y1 = max(0.0, min(y1, image_h))
        x2 = max(0.0, min(x2, image_w))
        y2 = max(0.0, min(y2, image_h))
        if x2 <= x1 or y2 <= y1:
            continue
        field = _rfdetr_field_name(int(labels[i]), names)
        if field is None:
            continue
        detections.append({
            "field": field,
            "text": "Подпись" if field == "signature" else "Печать",
            "bbox": [round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)],
            "confidence": round(float(scores[i]), 6),
            "source": "rfdetr", "page": 1,
        })
    return detections


@lru_cache(maxsize=2)
def load_rfdetr_detector(model_path: str, config_path: str, modified: int):
    """Load RF-DETR model from best.pth + config.json.

    Tries the rfdetr package first. Returns (predict_callable, names_dict).
    predict(image) -> (boxes, scores, labels) with boxes in pixel coords [x1,y1,x2,y2].
    """
    model_file = Path(model_path)
    config_file = Path(config_path)
    if not model_file.exists():
        raise FileNotFoundError(f"RF-DETR модель не найдена: {model_path}")
    if not config_file.exists():
        raise FileNotFoundError(f"RF-DETR конфиг не найден: {config_path}")

    names: dict[int, str] = {}
    try:
        config = json.loads(config_file.read_text(encoding="utf-8"))
        if isinstance(config, dict):
            for key in ("label_map", "classes", "names", "id2label", "labels"):
                val = config.get(key)
                if isinstance(val, dict):
                    names = {int(k): str(v) for k, v in val.items()}
                    break
            if not names and config.get("num_classes"):
                names = {i: f"class_{i}" for i in range(int(config["num_classes"]))}
    except Exception as exc:
        logger.warning("RF-DETR конфиг не прочитан (%s), будут числовые классы", exc)

    # Try rfdetr package
    try:
        rfdetr = importlib.import_module("rfdetr")
        if hasattr(rfdetr, "RFDETR"):
            model = rfdetr.RFDETR(pretrained_weights=str(model_file), device="cpu")

            def predict(image: np.ndarray):
                from PIL import Image
                pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
                results = model.predict(pil, threshold=0.0)
                boxes = getattr(results, "boxes", None)
                scores = getattr(results, "scores", None)
                labels = getattr(results, "labels", None)
                if boxes is None and isinstance(results, dict):
                    boxes = results.get("boxes")
                    scores = results.get("scores")
                    labels = results.get("labels")
                if boxes is None:
                    raise ValueError("rfdetr predict не вернул boxes")
                boxes = np.asarray(boxes, dtype=np.float32)
                scores = np.asarray(scores, dtype=np.float32).ravel()
                labels = np.asarray(labels, dtype=np.int64).ravel()
                h, w = image.shape[:2]
                if boxes.size and float(boxes.max()) <= 1.0 + 1e-6:
                    boxes[:, [0, 2]] *= w
                    boxes[:, [1, 3]] *= h
                return boxes, scores, labels

            return predict, names
    except Exception as exc:
        logger.warning("rfdetr пакет недоступен (%s)", exc)

    raise RuntimeError(
        "RF-DETR требует пакет rfdetr. Установите: pip install rfdetr "
        "(или используйте YOLO_ONNX / цветовой поиск печати)"
    )


def _run_rfdetr(image: np.ndarray, env_model: str, env_config: str,
                threshold: float) -> dict:
    model_path = os.getenv(env_model, "").strip()
    config_path = os.getenv(env_config, "").strip()
    if not model_path or not config_path:
        return unavailable("disabled")
    try:
        model_path_obj = Path(model_path).resolve(strict=True)
        config_path_obj = Path(config_path).resolve(strict=True)
        predict, names = load_rfdetr_detector(str(model_path_obj),
                                              str(config_path_obj),
                                              model_path_obj.stat().st_mtime_ns)
        boxes, scores, labels = predict(image)
        detections = _rfdetr_detections(boxes, scores, labels, names,
                                        threshold, image.shape[0], image.shape[1])
        present = {b["field"] for b in detections}
        return {"status": "ready",
                "signature": ("signature" in present),
                "stamp": ("stamp" in present),
                "boxes": detections}
    except Exception as exc:
        logger.warning("RF-DETR detection unavailable (%s): %s", env_model, exc)
        return unavailable("error")


def _run_source(image: np.ndarray, env_var: str, keep: frozenset, threshold: float) -> dict:
    path = os.getenv(env_var, "").strip()
    if not path:
        return unavailable("disabled")
    try:
        model_path = Path(path).resolve(strict=True)
        if model_path.suffix.lower() != ".onnx":
            raise ValueError(f"{env_var} должен указывать на .onnx")
        detector = load_detector(str(model_path), model_path.stat().st_mtime_ns, tuple(sorted(keep)))
        return detector.predict(image, threshold)
    except Exception as exc:
        logger.warning("Signature/stamp detection unavailable (%s): %s", env_var, exc)
        return unavailable("error")


def detect_marks(image: np.ndarray) -> dict:
    """Подпись и печать: YOLO-ONNX и/или RF-DETR, плюс цветовой поиск печати.

    Источники:
    - YOLO_SIG_MODEL_PATH — подпись (ONNX)
    - YOLO_MODEL_PATH — печать (ONNX)
    - RFDETR_MODEL_PATH + RFDETR_CONFIG_PATH — подпись и/или печать (RF-DETR best.pth)
    - YOLO_STAMP_HEURISTIC=1 — печать цветом (синее кольцо), если нет весов

    Каждый отсутствующий/упавший источник даёт None по своему полю.
    status: ready — хоть один источник готов; disabled — оба не настроены;
    error — настроены, но упали.
    """
    try:
        threshold = float(os.getenv("YOLO_CONFIDENCE", "0.3"))
        if not math.isfinite(threshold) or not 0 < threshold <= 1:
            raise ValueError("YOLO_CONFIDENCE должен быть в (0,1]")
    except Exception as exc:
        logger.warning("Signature/stamp detection unavailable: %s", exc)
        return unavailable("error")

    sig = _run_source(image, "YOLO_SIG_MODEL_PATH", frozenset({"signature"}), threshold)
    stamp = _run_source(image, "YOLO_MODEL_PATH", frozenset({"stamp"}), threshold)
    rfdetr = _run_rfdetr(image, "RFDETR_MODEL_PATH", "RFDETR_CONFIG_PATH", threshold)

    # RF-DETР может находить и подпись, и печать: заполняет пробелы YOLO-источников
    if rfdetr["status"] == "ready":
        rf_boxes = rfdetr["boxes"]
        rf_sig_boxes = [b for b in rf_boxes if b["field"] == "signature"]
        rf_stamp_boxes = [b for b in rf_boxes if b["field"] == "stamp"]

        if sig["status"] != "ready" and rf_sig_boxes:
            sig = {"status": "ready", "signature": True, "stamp": None,
                   "boxes": rf_sig_boxes}

        if stamp["status"] != "ready" and rf_stamp_boxes:
            stamp = {"status": "ready", "signature": None, "stamp": True,
                     "boxes": rf_stamp_boxes}

    # Печать цветом — только если ningún источник печати не настроен
    if stamp["status"] == "disabled" and os.getenv("YOLO_STAMP_HEURISTIC", "1") == "1":
        try:
            seal = detect_blue_seal(image)
        except Exception as exc:
            logger.warning("Blue-seal heuristic failed: %s", exc)
            stamp = unavailable("error")
        else:
            stamp = {"status": "ready", "signature": None,
                     "stamp": True if seal is not None else None,
                     "boxes": [seal] if seal else []}

    statuses = {sig["status"], stamp["status"]}
    if statuses == {"disabled"}:
        return unavailable("disabled")
    status = "ready" if "ready" in statuses else "error"
    boxes = [b for src in (sig, stamp) if src["status"] == "ready" for b in src["boxes"]]
    return {
        "status": status,
        # Поле берём только из своего источника; чужой источник не голосует.
        "signature": sig.get("signature"),
        "stamp": stamp.get("stamp"),
        "boxes": boxes,
    }
