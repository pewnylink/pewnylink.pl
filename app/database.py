# app/database.py
import json
from typing import AsyncGenerator
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# Pobranie URL bazy
RAW_DATABASE_URL = settings.get_database_url()


def sanitize_asyncpg_url(url: str) -> str:
    """Usuwa parametry nieobsługiwane przez asyncpg (np. channel_binding, sslmode)."""
    if not url.startswith("postgresql+asyncpg"):
        return url

    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)

    # asyncpg nie obsługuje channel_binding
    query_params.pop("channel_binding", None)

    # asyncpg używa 'ssl', a nie 'sslmode'
    if "sslmode" in query_params:
        ssl_val = query_params.pop("sslmode")
        query_params["ssl"] = ssl_val

    new_query = urlencode(query_params, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


DATABASE_URL = sanitize_asyncpg_url(RAW_DATABASE_URL)

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