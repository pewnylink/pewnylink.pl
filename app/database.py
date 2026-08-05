import os
from typing import AsyncGenerator
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

# Wczytanie zmiennych z pliku .env
load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")

# Budowa URL z wymuszonym szyfrowaniem SSL (standard m.in. w Neon.tech i Supabase)
DATABASE_URL = (
    f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}?ssl=require"
)

# Tworzenie asynchronicznego silnika bazy danych
engine = create_async_engine(
    DATABASE_URL,
    echo=False,          # Ustaw True, aby widzieć zapytania SQL w konsoli podczas developmentu
    pool_size=5,         # Liczba stałych połączeń w puli
    max_overflow=10,     # Maksymalna liczba dodatkowych połączeń przy obciążeniu
    pool_recycle=300,    # Odświeżanie połączeń co 5 minut (zapobiega zrywaniu przez chmurę)
)

# Fabryka asynchronicznych sesji
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Klasa bazowa dla wszystkich modeli tabel (SQLAlchemy 2.0 style)
class Base(DeclarativeBase):
    pass

# Generator sesji do użycia w aplikacjach (np. FastAPI lub skryptach)
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()