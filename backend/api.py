import os
import time
import uuid
import logging
import warnings
import secrets
import string
import smtplib
from email.message import EmailMessage
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Literal

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Depends, status
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field, JsonValue, ValidationError
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from sqlalchemy import select

from backend.models import ApiModel, ApiResponse, Document, DocumentImage, ServiceAnswer
from backend.database import engine, Base, SessionLocal
from backend.models import UserDB, DocumentDB, ExtractedFieldDB, RuleDB, RequestDB, AuditLogDB

MAX_FILE_SIZE = 10 * 1024 * 1024
MAX_QUESTION_LENGTH = 5000
MAX_IMAGE_PIXELS = 25_000_000
MAX_SESSIONS = 1000
SESSION_TTL_SECONDS = 3600
MAX_HISTORY_MESSAGES = 20
ALLOWED_FORMATS = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".pdf": "PDF"}
MIME_TYPES = {"JPEG": "image/jpeg", "PNG": "image/png", "PDF": "application/pdf"}

# Настройки URL сервисов
ML1_URL = os.getenv("ML1_URL", "http://host.docker.internal:8001/ocr")
ML2_URL = os.getenv("ML2_URL", "http://localhost:8003/extract")
BACKEND2_URL = os.getenv("BACKEND2_URL", "http://localhost:8002/answer")
DocumentType = Literal["study_certificate", "academic_leave", "internship_certificate"]
logger = logging.getLogger(__name__)
# Внутренние сервисы: 60с каждый, браузер ждёт до 200с за цепочку из трёх.
INTERNAL_TIMEOUT = float(os.getenv("INTERNAL_TIMEOUT", "60"))

# Настройки SMTP для отправки реальной почты
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "noreply@university.ru")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # БД опциональна: без DATABASE_URL/недоступного Postgres API работает на памяти сессий.
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Таблицы БД готовы: %s", list(Base.metadata.tables.keys()))
    except Exception as exc:
        logger.warning("БД недоступна, работа без персистентности: %s", exc)
    async with httpx.AsyncClient(timeout=INTERNAL_TIMEOUT) as client:
        app.state.http_client = client
        yield
    sessions.clear()
    active_sessions.clear()
    try:
        await engine.dispose()
    except Exception:
        pass


app = FastAPI(title="Онлайн-деканат API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",") if origin.strip()],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "sessions": len(sessions)}


# Асинхронная зависимость для получения сессии БД
async def get_db():
    async with SessionLocal() as session:
        yield session


# Схемы аутентификации и управления пользователями
class LoginRequest(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    email: str
    firstName: str = ""
    lastName: str = ""
    name: str = ""
    first_name: str = ""
    last_name: str = ""
    role: str
    id: int | str = 1
    user_id: int | str = 1

class LoginResponse(BaseModel):
    success: bool
    token: str
    user: UserResponse

class CreateUserRequest(BaseModel):
    email: str
    password: str
    username: str
    role: str = "student"

class ForgotPasswordRequest(BaseModel):
    email: str

class MessageResponse(BaseModel):
    success: bool
    message: str


# Схема чата и документов
class ChatMessage(ApiModel):
    message: str = Field(max_length=MAX_QUESTION_LENGTH)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=100)


class OcrResult(ApiModel):
    text: str
    coordinates: list[JsonValue] = Field(default_factory=list)
    image: DocumentImage | None = None
    visual_features: dict[str, JsonValue] | None = None


class ExtractedDocument(ApiModel):
    document_type: str | None = None
    fields: dict[str, JsonValue]
    coordinates: list[JsonValue] | None = None


@dataclass
class Session:
    history: list[dict[str, str]] = field(default_factory=list)
    document: Document | None = None
    updated_at: float = field(default_factory=time.monotonic)


sessions: dict[str, Session] = {}
active_sessions: set[str] = set()


# Вспомогательная функция отправки email через SMTP
def send_email_sync(to_email: str, subject: str, body: str):
    msg = EmailMessage()
    msg.set_content(body)
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to_email

    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("SMTP credentials not set. Email simulation active (see logs).")
        return False

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as exc:
        logger.error(f"Failed to send email via SMTP: {exc}")
        return False


# Эндпоинты входа и управления пользователями
@app.post("/api/auth/login", response_model=LoginResponse)
async def login(data: LoginRequest, db = Depends(get_db)):
    normalized_email = data.email.lower().strip()
    result = await db.execute(select(UserDB).where(UserDB.email == normalized_email))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь с таким email не найден. Обратитесь в деканат для регистрации учетной записи."
        )
    
    if user.password_hash != data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный пароль. Пожалуйста, проверьте правильность ввода."
        )
        
    name_parts = user.username.split(" ", 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    role_str = user.role.value if hasattr(user.role, "value") else str(user.role)

    return {
        "success": True,
        "token": f"fake-jwt-token-{user.user_id}-{int(time.time())}",
        "user": {
            "email": user.email,
            "firstName": first_name,
            "lastName": last_name,
            "name": user.username,
            "first_name": first_name,
            "last_name": last_name,
            "role": role_str,
            "id": user.user_id,
            "user_id": user.user_id
        }
    }


@app.post("/api/admin/users", response_model=MessageResponse)
async def admin_create_user(data: CreateUserRequest, db = Depends(get_db)):
    normalized_email = data.email.lower().strip()
    
    existing = await db.execute(select(UserDB).where(UserDB.email == normalized_email))
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует в базе деканата."
        )
    
    try:
        from backend.models import UserRole
        role_val = UserRole(data.role) if hasattr(UserRole, "__call__") or isinstance(UserRole, type) else data.role
    except Exception:
        role_val = data.role

    new_user = UserDB(
        email=normalized_email,
        password_hash=data.password,
        username=data.username,
        role=role_val
    )
    db.add(new_user)
    await db.commit()

    return {
        "success": True,
        "message": f"Пользователь {normalized_email} успешно создан деканатом."
    }


@app.post("/api/auth/forgot-password", response_model=MessageResponse)
async def forgot_password(data: ForgotPasswordRequest, db = Depends(get_db)):
    normalized_email = data.email.lower().strip()
    result = await db.execute(select(UserDB).where(UserDB.email == normalized_email))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Указанный email не зарегистрирован в базе деканата."
        )
        
    # Генерируем новый постоянный случайный пароль (8 символов)
    alphabet = string.ascii_letters + string.digits
    new_password = ''.join(secrets.choice(alphabet) for _ in range(8))
    
    # Обновляем пароль в базе данных PostgreSQL
    user.password_hash = new_password
    await db.commit()

    email_body = (
        f"Здравствуйте, {user.username}!\n\n"
        f"Был запрошен сброс пароля для вашей учетной записи в Онлайн-деканате.\n"
        f"Ваш новый постоянный пароль для входа: {new_password}\n\n"
        f"Используйте его для авторизации в системе."
    )

    # Отправляем через SMTP и выводим в логи бэкенда для тестирования
    await run_in_threadpool(send_email_sync, normalized_email, "Восстановление пароля — Онлайн-деканат", email_body)
    print(f"\n[NEW PERMANENT PASSWORD for {normalized_email}]: {new_password}\n")

    return {
        "success": True,
        "message": "Новый постоянный пароль успешно сгенерирован и отправлен на ваш email."
    }


# Вспомогательные функции логики документов
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
        if len(set(sessions) | active_sessions) >= MAX_SESSIONS:
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
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            # Пробрасываем тело upstream для отладки, обрезаем до 500 символов.
            try:
                detail = response.text[:500]
            except Exception:
                detail = ""
            logger.warning("Сервис %s вернул %s: %s", service, response.status_code, detail)
            raise HTTPException(
                status_code=502,
                detail=f"{service} вернул ошибку {response.status_code}" + (f": {detail}" if detail else ""),
            ) from exc
        result = response.json()
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail=f"Превышено время ожидания сервиса {service} ({INTERNAL_TIMEOUT:g}с)") from exc
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
                     database_document: Document | None) -> ApiResponse:
    response = await send_request(BACKEND2_URL, json={
        "question": question,
        "conversation_id": conversation_id,
        "document": database_document.model_dump() if database_document else None,
        "history": session.history,
    })
    answer = parse_service(ServiceAnswer, response, "Backend 2")
    if not answer.answer.strip():
        raise HTTPException(status_code=502, detail="Backend 2 не вернул ответ")
    result = ApiResponse(**answer.model_dump(), conversation_id=conversation_id, document=database_document)
    
    session.history = (session.history + [
        {"role": "user", "content": question},
        {"role": "assistant", "content": answer.answer},
    ])[-MAX_HISTORY_MESSAGES:]
    session.document = database_document
    session.updated_at = time.monotonic()
    sessions[conversation_id] = session
    return result

# Эндпоинты чата и анализа
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
    rotation: int = Form(0, ge=0, le=270, multiple_of=90),
):
    try:
        question = validate_question(question)
        with use_session(conversation_id) as (conversation_id, session):
            content, mime = await validate_file(file)
            ocr_options = {"files": {
                "file": (Path(file.filename).name, content, mime),
            }}
            if rotation:
                ocr_options["data"] = {"rotation": str(rotation)}
            ocr_payload = await send_request(ML1_URL, **ocr_options)
            ocr = parse_service(OcrResult, ocr_payload, "ML 1")
            extract_payload = {"ocr_result": ocr_payload}
            if document_type:
                extract_payload["document_type"] = document_type
            extracted = parse_service(ExtractedDocument,
                                      await send_request(ML2_URL, json=extract_payload), "ML 2")
            database_document = Document(
                type=extracted.document_type or document_type,
                fields=extracted.fields,
                ocr_text=ocr.text,
                coordinates=extracted.coordinates if extracted.coordinates is not None else ocr.coordinates,
                image=ocr.image,
                visual_features=ocr.visual_features,
            )
            return await get_answer(question, conversation_id, session, database_document)
    finally:
        await file.close()