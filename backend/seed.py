import asyncio
from backend.database import AsyncSessionLocal, engine, Base
from backend.models import UserDB, UserRole
from sqlalchemy import select

async def seed_database():
    print("--- ЗАПУСК СИДИНГА БАЗЫ ДАННЫХ ---")
    
    # Создаем таблицы асинхронно
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSessionLocal() as session:
        try:
            # Проверяем, есть ли уже пользователи в базе
            result = await session.execute(select(UserDB))
            existing_user = result.scalars().first()
            
            if existing_user:
                print("База данных уже содержит пользователей. Пропускаем сидинг.")
                return

            # Добавляем тестовых пользователей (студентов и администратора)
            users = [
                UserDB(
                    email="student@university.ru",
                    username="Иван Студентов",
                    password_hash="123456",
                    role=UserRole.STUDENT.value,
                ),
                UserDB(
                    email="admin@university.ru",
                    username="Алексей Админов",
                    password_hash="admin123",
                    role=UserRole.ADMIN.value,
                ),
                UserDB(
                    email="test@university.ru",
                    username="Мария Петрова",
                    password_hash="test123",
                    role=UserRole.STUDENT.value,
                )
            ]
            
            session.add_all(users)
            await session.commit()
            print("Успешно добавлены тестовые пользователи в базу данных!")
        except Exception as e:
            await session.rollback()
            print(f"Ошибка при сидинге базы данных: {e}")

if __name__ == "__main__":
    asyncio.run(seed_database())