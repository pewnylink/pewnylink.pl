# app/database.py
import json
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# Pobranie spójnego URL bazy z modułu konfiguracji
DATABASE_URL = settings.get_database_url()

is_sqlite = DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

# Konfiguracja silnika dopasowana do silnika bazy
engine_kwargs = {
    "echo": False,
    "json_serializer": lambda obj: json.dumps(obj, default=str, ensure_ascii=False),
}

if not is_sqlite:
    engine_kwargs.update({
        "pool_size": 5,
        "max_overflow": 10,
        "pool_recycle": 300,
    })

engine = create_async_engine(
    DATABASE_URL,
    connect_args=connect_args,
    **engine_kwargs
)

# Fabryka asynchronicznych sesji SQLAlchemy 2.0
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Główna klasa bazowa dla wszystkich modeli tabel ORM."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency Injection dla FastAPI dostarczający asynchroniczną sesję bazy danych."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()