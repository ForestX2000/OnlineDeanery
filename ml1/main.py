from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from ml1.preprocess import preprocess
from ml1.ocr import run_ocr


class OcrResponse(BaseModel):
    text: str
    coordinates: list[dict]


app = FastAPI(title="ML 1: OCR")


# health-check
@app.get("/health")
def health():
    return {"status": "ok"}


# принимает файл, возвращает текст и координаты блоков
@app.post("/ocr", response_model=OcrResponse)
async def ocr(file: UploadFile = File(...)):
    content = await file.read()
    if not content:
        raise HTTPException(400, "Файл пустой")
    try:
        image = await run_in_threadpool(preprocess, content)
        result = await run_in_threadpool(run_ocr, image)
    except Exception as exc:
        raise HTTPException(500, f"Ошибка OCR: {exc}") from exc
    return OcrResponse(
        text=result["text"],
        coordinates=[
            {"text": b["text"], "bbox": b["bbox"], "confidence": b["confidence"]}
            for b in result["boxes"]
        ],
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("ml1.main:app", host="0.0.0.0", port=8001)