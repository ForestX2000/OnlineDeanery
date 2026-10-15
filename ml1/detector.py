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
from functools import lru_cache
import logging
import math
import os
from pathlib import Path

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
    if score < 0.3 or radius <= 0:
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
    """Подпись — из YOLO_SIG_MODEL_PATH, печать — из YOLO_MODEL_PATH.

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
    if stamp["status"] == "disabled" and os.getenv("YOLO_STAMP_HEURISTIC", "1") == "1":
        # YOLO-весов печати нет: классический поиск синего кольца, только True.
        # Слабая/бледная печать (как на фото школьной справки) не должна
        # превращаться в уверенное «печати нет»: отсутствие сильного отклика —
        # это «не подтверждено» (None), а не False.
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
