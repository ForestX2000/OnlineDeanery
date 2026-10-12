"""OCR: PaddleOCR-VL через llama-server (llama.cpp)."""

import base64
import os
from typing import Any

import cv2
import numpy as np
import requests

# URL llama-server с PaddleOCR-VL.
# В Docker переопределяется через environment в docker-compose.yml.
VL_URL = os.getenv("PADDLEOCR_VL_URL", "http://host.docker.internal:8080/v1/chat/completions")
VL_TIMEOUT = 120


# отправляет картинку в PaddleOCR-VL, возвращает plain text
def run_vl_ocr(image: np.ndarray, task: str = "OCR:") -> str:
    ok, buf = cv2.imencode(".png", image)
    if not ok:
        raise RuntimeError("Не удалось закодировать картинку в PNG")
    img_b64 = base64.b64encode(buf.tobytes()).decode()

    resp = requests.post(
        VL_URL,
        json={
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                    {"type": "text", "text": f"<__media__>{task}"},
                ],
            }],
            "temperature": 0,
            "max_tokens": 1500,
        },
        timeout=VL_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


# главная функция: возвращает текст от PaddleOCR-VL
def run_ocr(image: np.ndarray) -> dict[str, Any]:
    text = run_vl_ocr(image, task="OCR:")
    return {"text": text, "boxes": []}

