import asyncio
from backend.database import engine
from backend.models import Base
from backend.models import UserDB, DocumentDB, ExtractedFieldDB, RuleDB, RequestDB, AuditLogDB, AuthTokenDB
from backend.migrations import apply_migrations

async def init_tables():
    print("Инициализация таблиц базы данных...")
    if engine is None:
        print("DATABASE_URL не задан — инициализация пропущена.")
        return
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(apply_migrations)
    print("Таблицы успешно созданы!")

if __name__ == "__main__":
    asyncio.run(init_tables())
