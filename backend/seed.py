"""Create the first administrator when bootstrap credentials are configured."""

import asyncio
import os

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select

from backend.database import AsyncSessionLocal, Base, engine
from backend.models import UserDB, UserRole
from backend.migrations import apply_migrations
from backend.security import hash_password


async def seed_database() -> None:
    if engine is None or AsyncSessionLocal is None:
        print("DATABASE_URL не задан — создание администратора пропущено.")
        return

    email = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "").strip()
    password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "")
    username = os.getenv("BOOTSTRAP_ADMIN_NAME", "Администратор").strip()
    if not email and not password:
        print("Начальный администратор не создан: задайте BOOTSTRAP_ADMIN_EMAIL и BOOTSTRAP_ADMIN_PASSWORD.")
        return
    if not email or not password:
        raise ValueError("Для создания администратора нужны BOOTSTRAP_ADMIN_EMAIL и BOOTSTRAP_ADMIN_PASSWORD.")
    if not 8 <= len(password) <= 256:
        raise ValueError("BOOTSTRAP_ADMIN_PASSWORD должен содержать от 8 до 256 символов.")
    if not username or len(username) > 100:
        raise ValueError("BOOTSTRAP_ADMIN_NAME должен содержать от 1 до 100 символов.")
    try:
        email = str(TypeAdapter(EmailStr).validate_python(email)).lower()
    except ValidationError as exc:
        raise ValueError("BOOTSTRAP_ADMIN_EMAIL должен быть корректным email.") from exc

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        await connection.run_sync(apply_migrations)

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(UserDB).where(UserDB.email == email))
        existing = result.scalars().first()
        if existing is not None:
            role = getattr(existing.role, "value", existing.role)
            if role != UserRole.ADMIN.value:
                raise ValueError("BOOTSTRAP_ADMIN_EMAIL уже занят пользователем без роли admin.")
            if not existing.is_bootstrap_admin:
                existing.is_bootstrap_admin = True
                await session.commit()
            print("Начальный администратор уже существует; пароль не изменён.")
            return

        session.add(UserDB(
            email=email,
            username=username,
            password_hash=hash_password(password),
            role=UserRole.ADMIN.value,
            is_bootstrap_admin=True,
        ))
        await session.commit()
        print("Начальный администратор создан.")


if __name__ == "__main__":
    asyncio.run(seed_database())
