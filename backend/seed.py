import asyncio
import bcrypt
from backend.database import AsyncSessionLocal, engine, Base
from backend.models import UserDB, UserRole
from sqlalchemy import select


def hash_password(password: str) -> str:
    """Хеширует пароль через bcrypt напрямую."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


async def seed_database():
    print("--- ЗАПУСК СИДИНГА БАЗЫ ДАННЫХ ---")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(select(UserDB))
            existing_user = result.scalars().first()

            if existing_user:
                print("База данных уже содержит пользователей. Пропускаем сидинг.")
                return

            users = [
                UserDB(
                    email="student@university.ru",
                    username="Иван Студентов",
                    password_hash=hash_password("123456"),
                    role=UserRole.STUDENT.value,
                ),
                UserDB(
                    email="admin@university.ru",
                    username="Алексей Админов",
                    password_hash=hash_password("admin123"),
                    role=UserRole.ADMIN.value,
                ),
                UserDB(
                    email="test@university.ru",
                    username="Мария Петрова",
                    password_hash=hash_password("test123"),
                    role=UserRole.STUDENT.value,
                ),
            ]

            session.add_all(users)
            await session.commit()
            print("Успешно добавлены тестовые пользователи в базу данных!")
        except Exception as e:
            await session.rollback()
            print(f"Ошибка при сидинге базы данных: {e}")


if __name__ == "__main__":
    asyncio.run(seed_database())