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
                    password="123456",
                    first_name="Иван",
                    last_name="Студентов",
                    role=UserRole.STUDENT
                ),
                UserDB(
                    email="admin@university.ru",
                    password="admin123",
                    first_name="Алексей",
                    last_name="Админов",
                    role=UserRole.ADMIN
                ),
                UserDB(
                    email="test@university.ru",
                    password="test123",
                    first_name="Мария",
                    last_name="Петрова",
                    role=UserRole.STUDENT
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