from functools import lru_cache
from typing import Any
import numpy as np
from paddleocr import PaddleOCR


# singleton PaddleOCR — модель грузится один раз
@lru_cache(maxsize=1)
def get_ocr() -> PaddleOCR:
    return PaddleOCR(
        lang="ru",
        use_angle_cls=True,
        show_log=False,
        use_gpu=False,
    )


# запускает OCR и возвращает текст + координаты блоков
def run_ocr(image: np.ndarray) -> dict[str, Any]:
    ocr = get_ocr()
    raw = ocr.ocr(image, cls=True)

    boxes: list[dict[str, Any]] = []
    lines: list[str] = []

    for page in raw or []:
        for item in page or []:
            bbox, (text, conf) = item[0], item[1]
            boxes.append({
                "text": text,
                "bbox": bbox,
                "confidence": float(conf),
            })
            lines.append(text)

    return {"text": "\n".join(lines), "boxes": boxes}