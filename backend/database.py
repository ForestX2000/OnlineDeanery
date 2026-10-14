import logging
import os
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)

# Без DATABASE_URL движок не создаём: API работает в режиме без БД
# (история/аккаунты недоступны), а не с захардкоженным паролем.
DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL:
    logger.warning("DATABASE_URL не задан — работа без персистентности (без БД)")

engine = create_async_engine(DATABASE_URL, echo=False) if DATABASE_URL else None
AsyncSessionLocal = (
    async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    if engine is not None else None
)


class Base(DeclarativeBase):
    pass


async def get_db():
    if AsyncSessionLocal is None:
        yield None
        return
    async with AsyncSessionLocal() as session:
        yield session


SessionLocal = AsyncSessionLocal
