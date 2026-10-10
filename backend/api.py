import os
import uuid
from io import BytesIO
from pathlib import Path

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel
from pypdf import PdfReader
from pypdf.errors import PdfReadError

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["POST"],
    allow_headers=["*"],
)
MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_FORMATS = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".pdf": "PDF"}
MIME_TYPES = {"JPEG": "image/jpeg", "PNG": "image/png", "PDF": "application/pdf"}
ML1_URL = os.getenv("ML1_URL", "http://localhost:8001/ocr")
ML2_URL = os.getenv("ML2_URL", "http://localhost:8003/extract")
BACKEND2_URL = os.getenv("BACKEND2_URL", "http://localhost:8002/answer")
sessions = {}

class ChatMessage(BaseModel):
    message: str
    conversation_id: str | None = None

def validate_question(question: str) -> str:
    question = question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Вопрос не должен быть пустым")
    return question

def get_session(conversation_id: str | None) -> tuple[str, dict]:
    if conversation_id is None:
        return str(uuid.uuid4()), {"history": [], "document": None}
    if conversation_id not in sessions:
        raise HTTPException(status_code=404, detail="Диалог не найден")
    return conversation_id, sessions[conversation_id]

async def validate_file(file: UploadFile) -> tuple[bytes, str]:
    extension = Path(file.filename or "").suffix.lower()
    if extension not in ALLOWED_FORMATS:
        raise HTTPException(status_code=400, detail="Разрешены JPG, PNG и PDF")
    content = await file.read(MAX_FILE_SIZE + 1)
    if not content:
        raise HTTPException(status_code=400, detail="Файл пустой")
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Максимальный размер файла - 10 МБ")
    file_format = ALLOWED_FORMATS[extension]
    if file_format in ("JPEG", "PNG"):
        try:
            with Image.open(BytesIO(content)) as image:
                if image.format != file_format:
                    raise HTTPException(status_code=400, detail="Формат файла не соответствует расширению")
                image.verify()
            with Image.open(BytesIO(content)) as image:
                image.load()
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
            raise HTTPException(status_code=400, detail="Изображение повреждено")
    else:
        if not content.startswith(b"%PDF-"):
            raise HTTPException(status_code=400, detail="Некорректный PDF")
        try:
            reader = PdfReader(BytesIO(content))
            if reader.is_encrypted or not reader.pages:
                raise HTTPException(status_code=400, detail="PDF защищён или не содержит страниц")
        except (PdfReadError, ValueError, OSError):
            raise HTTPException(status_code=400, detail="PDF повреждён")
    return content, MIME_TYPES[file_format]

async def send_request(url: str, **kwargs) -> dict:
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, **kwargs)
            response.raise_for_status()
            result = response.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Превышено время ожидания сервиса")
    except httpx.HTTPStatusError:
        raise HTTPException(status_code=502, detail="Внутренний сервис вернул ошибку")
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Внутренний сервис недоступен")
    except ValueError:
        raise HTTPException(status_code=502, detail="Сервис вернул некорректный JSON")
    if not isinstance(result, dict):
        raise HTTPException(status_code=502, detail="Сервис вернул неверный формат ответа")
    return result

async def get_answer(question: str, conversation_id: str, session: dict, document: dict | None) -> dict:
    response = await send_request(BACKEND2_URL, json={"question": question, "conversation_id": conversation_id, "document": document, "history": session["history"]})
    answer = response.get("answer")
    if not isinstance(answer, str):
        raise HTTPException(status_code=502, detail="Backend 2 не вернул ответ")
    session["history"].extend([{"role": "user", "content": question}, {"role": "assistant", "content": answer}])
    session["document"] = document
    sessions[conversation_id] = session
    return {"conversation_id": conversation_id, "answer": answer, "sources": response.get("sources", []), "document": document}

@app.post("/chat")
async def chat(data: ChatMessage):
    question = validate_question(data.message)
    conversation_id, session = get_session(data.conversation_id)
    return await get_answer(question, conversation_id, session, session["document"])

@app.post("/analyze")
async def analyze(file: UploadFile = File(...), question: str = Form(...), conversation_id: str | None = Form(None)):
    question = validate_question(question)
    conversation_id, session = get_session(conversation_id)
    content, mime = await validate_file(file)
    ocr = await send_request(ML1_URL, files={"file": (file.filename, content, mime)})
    extracted = await send_request(ML2_URL, json={"ocr_result": ocr})
    if not isinstance(extracted.get("fields"), dict):
        raise HTTPException(status_code=502, detail="ML 2 не вернул поля документа")
    document = {"type": extracted.get("document_type"), "fields": extracted["fields"], "ocr_text": ocr.get("text", ""), "coordinates": ocr.get("coordinates", [])}
    return await get_answer(question, conversation_id, session, document)