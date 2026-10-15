import os
import time
import uuid
import logging
import json
import hashlib
import warnings
import secrets
import threading
from collections import deque
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Literal

import httpx
from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile, Depends, status
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, EmailStr, Field, JsonValue, ValidationError
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from sqlalchemy import delete, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from backend.models import ApiModel, ApiResponse, Document, DocumentImage, ServiceAnswer
from backend.database import engine, Base, SessionLocal
from backend.migrations import apply_migrations
from backend.security import hash_password, verify_password, token_ttl_days
from backend.models import (
    UserDB,
    UserRole,
    DocumentDB,
    ExtractedFieldDB,
    RuleDB,
    RequestDB,
    AuditLogDB,
    AuthTokenDB,
)

DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(32))

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
DOCUMENT_TYPES_URL = os.getenv(
    "DOCUMENT_TYPES_URL",
    f"{BACKEND2_URL.rsplit('/', 1)[0]}/document-types",
)
logger = logging.getLogger(__name__)
# Даём OCR-сервису завершить распознавание и оставляем время на ответ.
INTERNAL_TIMEOUT = float(os.getenv("INTERNAL_TIMEOUT", "300"))

LOGIN_ATTEMPT_LIMIT = 10
LOGIN_WINDOW_SECONDS = 15 * 60
MAX_LOGIN_CLIENTS = 4096
_login_attempts: dict[str, deque[float]] = {}
_login_attempts_lock = threading.Lock()
database_startup_error: str | None = None


async def migrate_legacy_password_hashes() -> int:
    """Hash legacy plaintext values before any login request can use them."""
    if SessionLocal is None:
        return 0
    async with SessionLocal() as db:
        result = await db.execute(select(UserDB).with_for_update())
        users = result.scalars().all()
        legacy_users = [
            user for user in users
            if isinstance(user.password_hash, str)
            and user.password_hash
            and not user.password_hash.startswith("pbkdf2$")
        ]
        if not legacy_users:
            return 0
        values = [user.password_hash for user in legacy_users]
        hashes = await run_in_threadpool(lambda: [hash_password(value) for value in values])
        for user, password_hash in zip(legacy_users, hashes):
            user.password_hash = password_hash
        await db.commit()
        return len(legacy_users)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # БД опциональна: без DATABASE_URL/недоступного Postgres API работает на памяти сессий.
    global database_startup_error
    if engine is None:
        database_startup_error = None
        logger.warning("БД не настроена (DATABASE_URL пуст), работа без персистентности")
    else:
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                await conn.run_sync(apply_migrations)
            migrated_passwords = await migrate_legacy_password_hashes()
            if migrated_passwords:
                logger.info("Migrated %s legacy password hashes", migrated_passwords)
            database_startup_error = None
            logger.info("Таблицы БД готовы: %s", list(Base.metadata.tables.keys()))
        except Exception as exc:
            database_startup_error = type(exc).__name__
            logger.warning("БД недоступна или миграция не прошла (%s)", type(exc).__name__)
    async with httpx.AsyncClient(timeout=INTERNAL_TIMEOUT) as client:
        app.state.http_client = client
        yield
    sessions.clear()
    active_sessions.clear()
    try:
        if engine is not None:
            await engine.dispose()
    except Exception:
        pass


app = FastAPI(title="Онлайн-деканат API", lifespan=lifespan)


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(request: Request, exc: SQLAlchemyError):
    logger.warning("Database request failed (%s)", type(exc).__name__)
    return JSONResponse(
        status_code=503,
        content={"detail": "База данных временно недоступна. Попробуйте позже."},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",") if origin.strip()],
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.get("/health")
async def health():
    if SessionLocal is None:
        return {"status": "ok", "database": "disabled", "sessions": len(sessions)}
    if database_startup_error is not None:
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "database": "startup_failed",
                "sessions": len(sessions),
            },
        )
    try:
        async with SessionLocal() as health_db:
            await health_db.execute(text("SELECT 1"))
    except Exception as exc:
        logger.warning("DB readiness check failed (%s)", type(exc).__name__)
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "database": "unavailable", "sessions": len(sessions)},
        )
    return {"status": "ok", "database": "ok", "sessions": len(sessions)}


# Асинхронная зависимость для получения сессии БД
async def get_db():
    if SessionLocal is None:
        yield None
        return
    async with SessionLocal() as session:
        yield session


async def resolve_user(authorization: str | None, db):
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Сессия входа истекла. Войдите в аккаунт заново.")
    if db is None:
        raise HTTPException(status_code=503, detail="База данных недоступна. Войдите позже.")
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    result = await db.execute(
        select(UserDB).join(AuthTokenDB, AuthTokenDB.user_id == UserDB.user_id)
        .where(AuthTokenDB.token_hash == token_hash)
    )
    user = result.scalars().first()
    if user is None:
        raise HTTPException(status_code=401, detail="Пользователь не найден. Войдите в аккаунт заново.")
    return user


async def resolve_token(authorization: str | None, db):
    """Тот же разбор Bearer, но возвращает и запись токена (для проверки TTL)."""
    user = await resolve_user(authorization, db)
    if user is None:
        return None, None
    _, _, token = (authorization or "").partition(" ")
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    record = await db.get(AuthTokenDB, token_hash)
    if record is None:
        raise HTTPException(status_code=401, detail="Сессия входа истекла. Войдите в аккаунт заново.")
    return user, record


def token_expired(record) -> bool:
    created = getattr(record, "created_at", None)
    if created is None:
        return False
    now = datetime.now(timezone.utc)
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return now - created >= timedelta(days=token_ttl_days())


async def get_optional_user(
    authorization: str | None = Header(default=None), db=Depends(get_db)
):
    if not authorization:
        return None
    user, record = await resolve_token(authorization, db)
    if user is None:
        return None
    if token_expired(record):
        await db.execute(delete(AuthTokenDB).where(AuthTokenDB.token_hash == record.token_hash))
        await db.commit()
        raise HTTPException(status_code=401, detail="Сессия входа истекла. Войдите в аккаунт заново.")
    return user


async def get_required_user(
    authorization: str | None = Header(default=None), db=Depends(get_db)
):
    user, record = await resolve_token(authorization, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Войдите в аккаунт, чтобы открыть историю запросов.")
    if token_expired(record):
        await db.execute(delete(AuthTokenDB).where(AuthTokenDB.token_hash == record.token_hash))
        await db.commit()
        raise HTTPException(status_code=401, detail="Сессия входа истекла. Войдите в аккаунт заново.")
    return user


async def require_admin(current_user: UserDB = Depends(get_required_user)) -> UserDB:
    role = getattr(current_user.role, "value", current_user.role)
    if role != UserRole.ADMIN.value:
        raise HTTPException(status_code=403, detail="Требуются права администратора.")
    return current_user


# Схемы аутентификации и управления пользователями
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)

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
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)
    username: str = Field(min_length=1, max_length=100)
    role: Literal["student", "admin"] = "student"


class UpdateUserRequest(BaseModel):
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=256)
    username: str | None = Field(default=None, min_length=1, max_length=100)
    role: Literal["student", "admin"] | None = None


class UserListItem(BaseModel):
    user_id: int
    username: str
    email: str
    role: str
    created_at: datetime

class MessageResponse(BaseModel):
    success: bool
    message: str


class CreatedUserResponse(UserListItem):
    success: bool
    message: str


# Схема чата и документов
class ChatMessage(ApiModel):
    message: str = Field(max_length=MAX_QUESTION_LENGTH)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=100)


class RequestHistoryItem(ApiModel):
    request_id: int
    question: str
    answer: str | None
    status: str
    document_type: str | None = None
    created_at: datetime
    user_email: str
    user_name: str


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
    # Владелец диалога: "user:<id>" или "anon". Чужой conversation_id
    # не открывает чужой документ/историю (см. use_session).
    owner: str = "anon"


sessions: dict[str, Session] = {}
active_sessions: set[str] = set()


def check_login_rate_limit(client_host: str, now: float | None = None) -> None:
    """Allow at most ten login attempts per peer IP in a rolling 15-minute window."""
    current_time = time.monotonic() if now is None else now
    with _login_attempts_lock:
        for host, attempts in list(_login_attempts.items()):
            while attempts and current_time - attempts[0] >= LOGIN_WINDOW_SECONDS:
                attempts.popleft()
            if not attempts:
                del _login_attempts[host]

        attempts = _login_attempts.setdefault(client_host, deque())
        if len(attempts) >= LOGIN_ATTEMPT_LIMIT:
            retry_after = max(1, int(LOGIN_WINDOW_SECONDS - (current_time - attempts[0])))
            raise HTTPException(
                status_code=429,
                detail="Слишком много попыток входа. Попробуйте позже.",
                headers={"Retry-After": str(retry_after)},
            )
        attempts.append(current_time)

        if len(_login_attempts) > MAX_LOGIN_CLIENTS:
            oldest_host = min(_login_attempts, key=lambda host: _login_attempts[host][0])
            _login_attempts.pop(oldest_host, None)


def record_user_admin_action(
    db,
    admin: UserDB,
    action_type: str,
    target_user_id: int,
    comment: str,
) -> None:
    db.add(AuditLogDB(
        admin_id=admin.user_id,
        admin_email=admin.email,
        target_user_id=target_user_id,
        action_type=action_type,
        comment=comment,
    ))


# Эндпоинты входа и управления пользователями
@app.post("/api/auth/login", response_model=LoginResponse)
async def login(data: LoginRequest, request: Request, db = Depends(get_db)):
    if db is None:
        raise HTTPException(status_code=503, detail="База данных недоступна. Войдите позже.")
    peer = request.client.host if request.client is not None else "unknown"
    check_login_rate_limit(peer)
    normalized_email = data.email.lower().strip()
    result = await db.execute(select(UserDB).where(UserDB.email == normalized_email))
    user = result.scalars().first()

    stored_hash = user.password_hash if user is not None else DUMMY_PASSWORD_HASH
    check = await run_in_threadpool(verify_password, data.password, stored_hash)
    if user is None or check != "ok":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль."
        )
    name_parts = user.username.split(" ", 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    role_str = user.role.value if hasattr(user.role, "value") else str(user.role)

    token = secrets.token_urlsafe(32)
    db.add(AuthTokenDB(
        token_hash=hashlib.sha256(token.encode("utf-8")).hexdigest(),
        user_id=user.user_id,
    ))
    await db.commit()
    return {
        "success": True,
        "token": token,
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


@app.get("/api/requests", response_model=list[RequestHistoryItem])
async def request_history(
    current_user: UserDB = Depends(get_required_user), db=Depends(get_db)
):
    query = select(RequestDB, UserDB).join(UserDB, RequestDB.user_id == UserDB.user_id)
    if current_user.role != "admin":
        query = query.where(RequestDB.user_id == current_user.user_id)
    result = await db.execute(query.order_by(RequestDB.created_at.desc(), RequestDB.request_id.desc()))
    return [
        RequestHistoryItem(
            request_id=request.request_id,
            question=request.question_text,
            answer=request.answer_text,
            status=request.status,
            document_type=request.document_type,
            created_at=request.created_at,
            user_email=user.email,
            user_name=user.username,
        )
        for request, user in result.all()
    ]


@app.post("/api/auth/logout", response_model=MessageResponse)
async def logout(
    authorization: str | None = Header(default=None),
    current_user: UserDB = Depends(get_required_user),
    db=Depends(get_db),
):
    _, _, token = (authorization or "").partition(" ")
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    await db.execute(delete(AuthTokenDB).where(AuthTokenDB.token_hash == token_hash))
    await db.commit()
    return {"success": True, "message": "Вы вышли из аккаунта."}


@app.post("/api/admin/users", response_model=CreatedUserResponse)
async def admin_create_user(
    data: CreateUserRequest,
    current_admin: UserDB = Depends(require_admin),
    db=Depends(get_db),
):
    if db is None:
        raise HTTPException(status_code=503, detail="База данных недоступна. Попробуйте позже.")
    normalized_email = data.email.lower().strip()
    normalized_username = data.username.strip()
    if not normalized_username:
        raise HTTPException(status_code=422, detail="Имя пользователя не должно быть пустым.")

    existing = await db.execute(select(UserDB).where(UserDB.email == normalized_email))
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует в базе деканата."
        )

    existing = await db.execute(select(UserDB).where(UserDB.username == normalized_username))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Имя пользователя уже занято.")

    new_user = UserDB(
        email=normalized_email,
        password_hash=await run_in_threadpool(hash_password, data.password),
        username=normalized_username,
        role=UserRole(data.role).value,
    )
    db.add(new_user)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Email или имя пользователя уже заняты.") from exc
    record_user_admin_action(
        db, current_admin, "user.create", new_user.user_id,
        f"Создан пользователь {normalized_email}.",
    )
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Email или имя пользователя уже заняты.") from exc

    return {
        **_user_list_item(new_user).model_dump(),
        "success": True,
        "message": f"Пользователь {normalized_email} успешно создан деканатом."
    }


def _user_list_item(user: UserDB) -> UserListItem:
    return UserListItem(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        role=getattr(user.role, "value", user.role),
        created_at=user.created_at,
    )


async def _lock_admin_count(db) -> int:
    """Lock current admin rows in stable order before enforcing the last-admin rule."""
    result = await db.execute(
        select(UserDB)
        .where(UserDB.role == UserRole.ADMIN.value)
        .order_by(UserDB.user_id)
        .with_for_update()
    )
    return len(result.scalars().all())


@app.get("/api/admin/users", response_model=list[UserListItem])
async def admin_list_users(
    _: UserDB = Depends(require_admin),
    db=Depends(get_db),
):
    if db is None:
        raise HTTPException(status_code=503, detail="База данных недоступна. Попробуйте позже.")
    result = await db.execute(select(UserDB).order_by(UserDB.user_id))
    return [_user_list_item(user) for user in result.scalars().all()]


@app.get("/api/admin/users/{user_id}", response_model=UserListItem)
async def admin_get_user(
    user_id: int,
    _: UserDB = Depends(require_admin),
    db=Depends(get_db),
):
    if db is None:
        raise HTTPException(status_code=503, detail="База данных недоступна. Попробуйте позже.")
    user = await db.get(UserDB, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден.")
    return _user_list_item(user)


@app.patch("/api/admin/users/{user_id}", response_model=UserListItem)
async def admin_update_user(
    user_id: int,
    data: UpdateUserRequest,
    current_admin: UserDB = Depends(require_admin),
    db=Depends(get_db),
):
    if db is None:
        raise HTTPException(status_code=503, detail="База данных недоступна. Попробуйте позже.")
    changes = data.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="Укажите хотя бы одно поле для изменения.")
    if any(value is None for value in changes.values()):
        raise HTTPException(status_code=422, detail="Изменяемые поля не должны быть пустыми.")

    locked_admin_count = await _lock_admin_count(db) if "role" in changes else None
    user = await db.get(UserDB, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден.")

    if "email" in changes:
        new_email = str(data.email).strip().lower()
        duplicate = await db.execute(
            select(UserDB).where(UserDB.email == new_email, UserDB.user_id != user_id)
        )
        if duplicate.scalars().first():
            raise HTTPException(status_code=400, detail="Email уже занят.")
        user.email = new_email

    if "username" in changes:
        new_username = data.username.strip()
        if not new_username:
            raise HTTPException(status_code=422, detail="Имя пользователя не должно быть пустым.")
        duplicate = await db.execute(
            select(UserDB).where(UserDB.username == new_username, UserDB.user_id != user_id)
        )
        if duplicate.scalars().first():
            raise HTTPException(status_code=400, detail="Имя пользователя уже занято.")
        user.username = new_username

    if "password" in changes:
        user.password_hash = await run_in_threadpool(hash_password, data.password)
        await db.execute(delete(AuthTokenDB).where(AuthTokenDB.user_id == user_id))

    if data.role == UserRole.STUDENT.value and getattr(user.role, "value", user.role) == UserRole.ADMIN.value:
        if locked_admin_count is not None and locked_admin_count <= 1:
            raise HTTPException(status_code=400, detail="Нельзя снять роль у последнего администратора.")
    if "role" in changes:
        user.role = data.role

    changed_fields = ", ".join(sorted(changes))
    action = "user.password_change" if set(changes) == {"password"} else "user.update"
    record_user_admin_action(
        db, current_admin, action, user.user_id,
        f"Изменены поля: {changed_fields}.",
    )
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Email или имя пользователя уже заняты.") from exc
    await db.refresh(user)
    return _user_list_item(user)


@app.delete("/api/admin/users/{user_id}", response_model=MessageResponse)
async def admin_delete_user(
    user_id: int,
    current_admin: UserDB = Depends(require_admin),
    db=Depends(get_db),
):
    if db is None:
        raise HTTPException(status_code=503, detail="База данных недоступна. Попробуйте позже.")
    if user_id == current_admin.user_id:
        raise HTTPException(status_code=400, detail="Нельзя удалить текущую учетную запись.")

    admin_count = await _lock_admin_count(db)
    user = await db.get(UserDB, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден.")
    if getattr(user.role, "value", user.role) == UserRole.ADMIN.value and admin_count <= 1:
        raise HTTPException(status_code=400, detail="Нельзя удалить последнего администратора.")

    email = user.email
    record_user_admin_action(
        db, current_admin, "user.delete", user.user_id,
        f"Удалена учетная запись {email}.",
    )
    await db.delete(user)
    await db.commit()
    return {"success": True, "message": f"Пользователь {email} удалён."}


# Вспомогательные функции логики документов
def validate_question(question: str) -> str:
    question = question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Вопрос не должен быть пустым")
    if len(question) > MAX_QUESTION_LENGTH:
        raise HTTPException(status_code=400, detail="Максимальная длина вопроса — 5000 символов")
    return question


@contextmanager
def use_session(conversation_id: str | None, owner: str = "anon"):
    now = time.monotonic()
    for key, session in list(sessions.items()):
        if key not in active_sessions and now - session.updated_at > SESSION_TTL_SECONDS:
            del sessions[key]
    if conversation_id is not None:
        if conversation_id not in sessions:
            raise HTTPException(status_code=404, detail="Диалог не найден или срок его хранения истёк")
        session = sessions[conversation_id]
        if session.owner != owner:
            # Чужой диалог: отвечаем как об истёкшем, не раскрывая факта.
            raise HTTPException(status_code=404, detail="Диалог не найден или срок его хранения истёк")
    else:
        if len(set(sessions) | active_sessions) >= MAX_SESSIONS:
            raise HTTPException(status_code=503, detail="Слишком много активных диалогов. Попробуйте позже")
        conversation_id, session = str(uuid.uuid4()), Session(owner=owner)
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
            if len(reader.pages) > 30:
                raise HTTPException(status_code=400, detail="Слишком много страниц в PDF: максимум 30")
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


async def send_request(url: str, *, method: str = "POST", **kwargs) -> dict:
    service = {ML1_URL: "OCR (ML 1)", ML2_URL: "Extract (ML 2)",
               BACKEND2_URL: "Backend 2", DOCUMENT_TYPES_URL: "конфигурация типов документов"}.get(url, "внутренний сервис")
    try:
        response = await app.state.http_client.request(method, url, **kwargs)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if response.status_code == 504:
                raise HTTPException(status_code=504, detail=f"Превышено время ожидания сервиса {service}") from exc
            # Тело upstream не пробрасываем клиенту (внутренности сервисов),
            # только код; детали остаются в серверном логе.
            try:
                detail = response.text[:500]
            except Exception:
                detail = ""
            logger.warning("Сервис %s вернул %s: %s", service, response.status_code, detail)
            raise HTTPException(
                status_code=502,
                detail=f"{service} вернул ошибку {response.status_code}",
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


@app.get("/document-types")
async def configured_document_types():
    return await send_request(DOCUMENT_TYPES_URL, method="GET")


async def get_document_type_definition(document_type: str | None) -> dict[str, Any] | None:
    if not document_type:
        return None
    catalog = await send_request(DOCUMENT_TYPES_URL, method="GET")
    items = catalog.get("items")
    if not isinstance(items, list):
        raise HTTPException(status_code=502, detail="Конфигурация типов документов имеет неверный формат")
    for item in items:
        if isinstance(item, dict) and item.get("id") == document_type:
            return item
    raise HTTPException(status_code=422, detail="Выбранный тип документа отсутствует в конфигурации")


def request_status_for_result(result: ApiResponse) -> str:
    if result.document is None or result.verification is None:
        return "failed"
    if (result.verification.status != "complete" or result.verification.missing_fields
            or result.verification.issues):
        return "failed"
    return "resolved"


def request_status_for_exception(exc: Exception) -> str:
    return "timeout" if isinstance(exc, HTTPException) and exc.status_code == 504 else "failed"


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


async def begin_request_record(
    db, user: UserDB | None, question: str, document_type: str | None = None
) -> int | None:
    if user is None or db is None:
        return None
    record = RequestDB(user_id=user.user_id, question_text=question,
                       document_type=document_type, status="processing")
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record.request_id


async def finish_request_record(
    db, request_id: int | None, status_value: str, answer: str | None = None,
    document_type: str | None = None,
) -> None:
    if request_id is None or db is None:
        return
    record = await db.get(RequestDB, request_id)
    if record is None:
        return
    record.status = status_value
    record.answer_text = answer
    if document_type is not None:
        record.document_type = document_type
    await db.commit()


async def finish_request_record_in_new_session(
    request_id: int | None, status_value: str, answer: str | None = None,
    document_type: str | None = None,
) -> None:
    if request_id is None or SessionLocal is None:
        return
    async with SessionLocal() as history_db:
        await finish_request_record(history_db, request_id, status_value, answer, document_type)

# Эндпоинты чата и анализа
def session_owner(user: UserDB | None) -> str:
    return f"user:{user.user_id}" if user is not None else "anon"


@app.post("/chat", response_model=ApiResponse)
async def chat(
    data: ChatMessage,
    current_user: UserDB | None = Depends(get_optional_user),
    db=Depends(get_db),
):
    question = validate_question(data.message)
    request_id = await begin_request_record(db, current_user, question)
    try:
        with use_session(data.conversation_id, session_owner(current_user)) as (conversation_id, session):
            result = await get_answer(question, conversation_id, session, session.document)
        await finish_request_record(db, request_id, "resolved", result.answer)
        return result
    except Exception as exc:
        await finish_request_record(db, request_id, request_status_for_exception(exc))
        raise


@app.post("/analyze", response_model=ApiResponse)
async def analyze(
    file: UploadFile = File(...),
    question: str = Form(..., max_length=MAX_QUESTION_LENGTH),
    conversation_id: str | None = Form(None, min_length=1, max_length=100),
    document_type: str | None = Form(None, max_length=100),
    rotation: int = Form(0, ge=0, le=270, multiple_of=90),
    current_user: UserDB | None = Depends(get_optional_user),
    db=Depends(get_db),
):
    try:
        question = validate_question(question)
        type_definition = await get_document_type_definition(document_type)
        request_id = await begin_request_record(db, current_user, question, document_type)
        try:
            with use_session(conversation_id, session_owner(current_user)) as (conversation_id, session):
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
                    extract_payload["field_definitions"] = type_definition.get("required_fields", [])
                extracted = parse_service(ExtractedDocument,
                                          await send_request(ML2_URL, json=extract_payload), "ML 2")
                database_document = Document(
                    type=extracted.document_type or document_type,
                    fields=extracted.fields,
                    ocr_text=ocr.text,
                    coordinates=extracted.coordinates or ocr.coordinates,
                    image=ocr.image,
                    visual_features=ocr.visual_features,
                )
                result = await get_answer(question, conversation_id, session, database_document)
            await finish_request_record(db, request_id, request_status_for_result(result),
                                        result.answer, result.document.type if result.document else None)
            return result
        except Exception as exc:
            await finish_request_record(db, request_id, request_status_for_exception(exc),
                                        document_type=document_type)
            raise
    finally:
        await file.close()


@app.post("/analyze/stream")
async def analyze_stream(
    file: UploadFile = File(...),
    question: str = Form(..., max_length=MAX_QUESTION_LENGTH),
    conversation_id: str | None = Form(None, min_length=1, max_length=100),
    document_type: str | None = Form(None, max_length=100),
    rotation: int = Form(0, ge=0, le=270, multiple_of=90),
    current_user: UserDB | None = Depends(get_optional_user),
    db=Depends(get_db),
):
    question = validate_question(question)
    type_definition = await get_document_type_definition(document_type)
    request_id = await begin_request_record(db, current_user, question, document_type)

    def encode_event(event: dict) -> str:
        return json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n"

    async def event_stream():
        try:
            with use_session(conversation_id, session_owner(current_user)) as (active_conversation_id, session):
                yield encode_event({"type": "progress", "stage": "ocr"})
                content, mime = await validate_file(file)
                ocr_options = {"files": {
                    "file": (Path(file.filename).name, content, mime),
                }}
                if rotation:
                    ocr_options["data"] = {"rotation": str(rotation)}
                ocr_payload = await send_request(ML1_URL, **ocr_options)
                ocr = parse_service(OcrResult, ocr_payload, "ML 1")

                yield encode_event({"type": "progress", "stage": "extract"})
                extract_payload = {"ocr_result": ocr_payload}
                if document_type:
                    extract_payload["document_type"] = document_type
                    extract_payload["field_definitions"] = type_definition.get("required_fields", [])
                extracted = parse_service(ExtractedDocument,
                                          await send_request(ML2_URL, json=extract_payload), "ML 2")
                database_document = Document(
                    type=extracted.document_type or document_type,
                    fields=extracted.fields,
                    ocr_text=ocr.text,
                    coordinates=extracted.coordinates or ocr.coordinates,
                    image=ocr.image,
                    visual_features=ocr.visual_features,
                )
                yield encode_event({
                    "type": "fields",
                    "document": database_document.model_dump(mode="json"),
                })
                yield encode_event({"type": "progress", "stage": "answer"})
                result = await get_answer(question, active_conversation_id, session, database_document)
            await finish_request_record_in_new_session(
                request_id, request_status_for_result(result), result.answer,
                result.document.type if result.document else None,
            )
            yield encode_event({"type": "result", "result": result.model_dump(mode="json")})
        except HTTPException as exc:
            await finish_request_record_in_new_session(request_id, request_status_for_exception(exc),
                                                       document_type=document_type)
            yield encode_event({"type": "error", "detail": exc.detail, "status": exc.status_code})
        except Exception:
            logger.exception("Не удалось завершить потоковый анализ документа")
            await finish_request_record_in_new_session(request_id, "failed", document_type=document_type)
            yield encode_event({"type": "error", "detail": "Не удалось завершить обработку документа.", "status": 500})
        finally:
            await file.close()

    return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
