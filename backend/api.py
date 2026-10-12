import os
import time
import uuid
import warnings
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Literal

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field, JsonValue, ValidationError
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from backend.models import ApiModel, ApiResponse, Document, ServiceAnswer

MAX_FILE_SIZE = 10 * 1024 * 1024
MAX_QUESTION_LENGTH = 5000
MAX_IMAGE_PIXELS = 25_000_000
MAX_SESSIONS = 1000
SESSION_TTL_SECONDS = 3600
MAX_HISTORY_MESSAGES = 20
ALLOWED_FORMATS = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".pdf": "PDF"}
MIME_TYPES = {"JPEG": "image/jpeg", "PNG": "image/png", "PDF": "application/pdf"}
ML1_URL: "${ML1_URL:-http://host.docker.internal:8001/ocr}"
ML2_URL = os.getenv("ML2_URL", "http://localhost:8003/extract")
BACKEND2_URL = os.getenv("BACKEND2_URL", "http://localhost:8002/answer")
DocumentType = Literal["study_certificate", "academic_leave", "internship_certificate"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with httpx.AsyncClient(timeout=180) as client:
        app.state.http_client = client
        yield
    sessions.clear()
    active_sessions.clear()


app = FastAPI(title="Онлайн-деканат API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",") if origin.strip()],
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)


class ChatMessage(ApiModel):
    message: str = Field(max_length=MAX_QUESTION_LENGTH)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=100)


class OcrResult(ApiModel):
    text: str
    coordinates: list[JsonValue] = Field(default_factory=list)


class ExtractedDocument(ApiModel):
    document_type: str | None = None
    fields: dict[str, JsonValue]


@dataclass
class Session:
    history: list[dict[str, str]] = field(default_factory=list)
    document: Document | None = None
    updated_at: float = field(default_factory=time.monotonic)


# Для локального MVP: один worker. Общее хранилище потребуется при масштабировании.
sessions: dict[str, Session] = {}
active_sessions: set[str] = set()


def validate_question(question: str) -> str:
    question = question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Вопрос не должен быть пустым")
    if len(question) > MAX_QUESTION_LENGTH:
        raise HTTPException(status_code=400, detail="Максимальная длина вопроса — 5000 символов")
    return question


@contextmanager
def use_session(conversation_id: str | None):
    now = time.monotonic()
    for key, session in list(sessions.items()):
        if key not in active_sessions and now - session.updated_at > SESSION_TTL_SECONDS:
            del sessions[key]
    if conversation_id is not None:
        if conversation_id not in sessions:
            raise HTTPException(status_code=404, detail="Диалог не найден или срок его хранения истёк")
        session = sessions[conversation_id]
    else:
        if len(sessions.keys() | active_sessions) >= MAX_SESSIONS:
            raise HTTPException(status_code=503, detail="Слишком много активных диалогов. Попробуйте позже")
        conversation_id, session = str(uuid.uuid4()), Session()
    if conversation_id in active_sessions:
        raise HTTPException(status_code=409, detail="Дождитесь ответа на предыдущий вопрос")
    active_sessions.add(conversation_id)
    try:
        yield conversation_id, session
    finally:
        active_sessions.discard(conversation_id)


def inspect_file(content: bytes, file_format: str) -> None:
    if file_format in ("JPEG", "PNG"):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(BytesIO(content)) as image:
                    if image.format != file_format:
                        raise HTTPException(status_code=400, detail="Формат файла не соответствует расширению")
                    if image.width * image.height > MAX_IMAGE_PIXELS:
                        raise HTTPException(status_code=400, detail="Изображение слишком большое: максимум 25 мегапикселей")
                    image.verify()
                with Image.open(BytesIO(content)) as image:
                    image.load()
        except (UnidentifiedImageError, OSError, ValueError,
                Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
            raise HTTPException(status_code=400, detail="Изображение повреждено или слишком большое") from exc
    else:
        if not content.startswith(b"%PDF-"):
            raise HTTPException(status_code=400, detail="Некорректный PDF")
        try:
            reader = PdfReader(BytesIO(content))
            if reader.is_encrypted or not reader.pages:
                raise HTTPException(status_code=400, detail="PDF защищён или не содержит страниц")
        except (PdfReadError, ValueError, OSError) as exc:
            raise HTTPException(status_code=400, detail="PDF повреждён") from exc


async def validate_file(file: UploadFile) -> tuple[bytes, str]:
    extension = Path(file.filename or "").suffix.lower()
    if extension not in ALLOWED_FORMATS:
        raise HTTPException(status_code=400, detail="Разрешены JPG, PNG и PDF")
    content = await file.read(MAX_FILE_SIZE + 1)
    if not content:
        raise HTTPException(status_code=400, detail="Файл пустой")
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Максимальный размер файла — 10 МБ")
    file_format = ALLOWED_FORMATS[extension]
    await run_in_threadpool(inspect_file, content, file_format)
    return content, MIME_TYPES[file_format]


async def send_request(url: str, **kwargs) -> dict:
    service = {ML1_URL: "OCR (ML 1)", ML2_URL: "Extract (ML 2)", BACKEND2_URL: "Backend 2"}.get(url, "внутренний сервис")
    try:
        response = await app.state.http_client.post(url, **kwargs)
        response.raise_for_status()
        result = response.json()
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="Превышено время ожидания сервиса") from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail="Внутренний сервис вернул ошибку") from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=503, detail=f"Сервис {service} недоступен. Проверьте его запуск и адрес подключения.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Сервис вернул некорректный JSON") from exc
    if not isinstance(result, dict):
        raise HTTPException(status_code=502, detail="Сервис вернул неверный формат ответа")
    return result


def parse_service(model: type[BaseModel], data: dict, service: str):
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        raise HTTPException(status_code=502, detail=f"{service} вернул некорректные данные") from exc


async def get_answer(question: str, conversation_id: str, session: Session,
                     document: Document | None) -> ApiResponse:
    response = await send_request(BACKEND2_URL, json={
        "question": question,
        "conversation_id": conversation_id,
        "document": document.model_dump() if document else None,
        "history": session.history,
    })
    answer = parse_service(ServiceAnswer, response, "Backend 2")
    if not answer.answer.strip():
        raise HTTPException(status_code=502, detail="Backend 2 не вернул ответ")
    result = ApiResponse(**answer.model_dump(), conversation_id=conversation_id, document=document)
    # Сохраняем историю только после проверки всего ответа сервиса.
    session.history = (session.history + [
        {"role": "user", "content": question},
        {"role": "assistant", "content": answer.answer},
    ])[-MAX_HISTORY_MESSAGES:]
    session.document = document
    session.updated_at = time.monotonic()
    sessions[conversation_id] = session
    return result


@app.post("/chat", response_model=ApiResponse)
async def chat(data: ChatMessage):
    question = validate_question(data.message)
    with use_session(data.conversation_id) as (conversation_id, session):
        return await get_answer(question, conversation_id, session, session.document)


@app.post("/analyze", response_model=ApiResponse)
async def analyze(
    file: UploadFile = File(...),
    question: str = Form(..., max_length=MAX_QUESTION_LENGTH),
    conversation_id: str | None = Form(None, min_length=1, max_length=100),
    document_type: DocumentType | None = Form(None),
):
    try:
        question = validate_question(question)
        with use_session(conversation_id) as (conversation_id, session):
            content, mime = await validate_file(file)
            ocr_payload = await send_request(ML1_URL, files={
                "file": (Path(file.filename).name, content, mime),
            })
            ocr = parse_service(OcrResult, ocr_payload, "ML 1")
            extract_payload = {"ocr_result": ocr_payload}
            if document_type:
                extract_payload["document_type"] = document_type
            extracted = parse_service(ExtractedDocument,
                                      await send_request(ML2_URL, json=extract_payload), "ML 2")
            document = Document(
                type=extracted.document_type or document_type,
                fields=extracted.fields,
                ocr_text=ocr.text,
                coordinates=ocr.coordinates,
            )
            return await get_answer(question, conversation_id, session, document)
    finally:
        await file.close()
