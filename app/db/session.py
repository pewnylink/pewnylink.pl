# app/db/session.py
import json
from typing import AsyncGenerator
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


def sanitize_asyncpg_url(url: str) -> str:
    """Usuwa parametry nieobsługiwane przez asyncpg (np. channel_binding, sslmode)."""
    if not url.startswith("postgresql+asyncpg"):
        return url

    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)

    # Bezpieczne usunięcie niekompatybilnych parametrów cloudowych
    query_params.pop("channel_binding", None)

    if "sslmode" in query_params:
        ssl_val = query_params.pop("sslmode")
        query_params["ssl"] = ssl_val

    new_query = urlencode(query_params, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


# Pobranie URL bazy danych
if hasattr(settings, "get_database_url"):
    RAW_DATABASE_URL = settings.get_database_url()
else:
    RAW_DATABASE_URL = getattr(settings, "DATABASE_URL", "")

DATABASE_URL = sanitize_asyncpg_url(RAW_DATABASE_URL)

is_sqlite = DATABASE_URL.startswith("sqlite")

# Konfiguracja connect_args w zależności od silnika bazy danych
connect_args = {}
if is_sqlite:
    connect_args["check_same_thread"] = False
else:
    # Wyłączenie cache przygotowanych zapytań (rozwiązuje InvalidCachedStatementError w testach oraz PgBouncerze)
    connect_args["prepared_statement_cache_size"] = 0

# Konfiguracja silnika pod produkcyjne wymogi SaaS
engine_kwargs = {
    "echo": False,
    "pool_pre_ping": True,  # Odporność na zerwane połączenia z PostgreSQL
}

if is_sqlite:
    engine_kwargs["json_serializer"] = lambda obj: json.dumps(obj, default=str, ensure_ascii=False)
else:
    engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_recycle": 1800,
        "pool_timeout": 30,
    })

engine = create_async_engine(
    DATABASE_URL,
    connect_args=connect_args,
    **engine_kwargs
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Alias zapewniający kompatybilność ze wszystkimi modułami i testami
async_session_maker = AsyncSessionLocal


class Base(DeclarativeBase):
    """Główna klasa bazowa dla wszystkich modeli tabel ORM."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency Injection dla FastAPI dostarczający asynchroniczną sesję bazy danych."""
    async with AsyncSessionLocal() as session:
        yield session