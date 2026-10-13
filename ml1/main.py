import logging

import requests
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from ml1.preprocess import prepare_image
from ml1.detector import detect_marks
from ml1.ocr import OcrResponseError, run_ocr

MAX_FILE_SIZE = 10 * 1024 * 1024


class OcrResponse(BaseModel):
    text: str
    coordinates: list[dict]
    image: dict
    visual_features: dict


app = FastAPI(title="ML 1: OCR")
logger = logging.getLogger(__name__)


# health-check
@app.get("/health")
def health():
    return {"status": "ok"}


# принимает файл, возвращает текст и координаты блоков
@app.post("/ocr", response_model=OcrResponse)
async def ocr(file: UploadFile = File(...),
              rotation: int = Form(0, ge=0, le=270, multiple_of=90)):
    try:
        content = await file.read(MAX_FILE_SIZE + 1)
        if not content:
            raise HTTPException(400, "Файл пустой")
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(413, "Максимальный размер файла — 10 МБ")
        try:
            prepared = await run_in_threadpool(prepare_image, content, rotation)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        try:
            result = await run_in_threadpool(run_ocr, prepared.pixels)
        except requests.Timeout as exc:
            raise HTTPException(504, "Превышено время ожидания OCR-модели") from exc
        except requests.ConnectionError as exc:
            raise HTTPException(503, "OCR-модель недоступна. Проверьте llama-server.") from exc
        except requests.RequestException as exc:
            response = getattr(exc, "response", None)
            if response is not None:
                logger.error("llama-server rejected OCR request: HTTP %s %s",
                             response.status_code, response.reason)
            else:
                logger.error("llama-server OCR request failed: %s", type(exc).__name__)
            raise HTTPException(502, "OCR-модель отклонила запрос") from exc
        except OcrResponseError as exc:
            raise HTTPException(502, str(exc)) from exc
        marks = await run_in_threadpool(detect_marks, prepared.pixels)
        boxes = result["boxes"] + marks.pop("boxes")
        coordinates = [{**box, "bbox": prepared.original_bbox(box["bbox"])} for box in boxes]
        return OcrResponse(text=result["text"], coordinates=coordinates,
                           image=prepared.metadata(), visual_features=marks)
    finally:
        await file.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("ml1.main:app", host="0.0.0.0", port=8001)
