from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# Pobieranie adresu bazy z pliku .env / app/core/config.py
DATABASE_URL = settings.DATABASE_URL

class Base(DeclarativeBase):
    """Główna klasa bazowa dla wszystkich modeli ORM"""
    pass

engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Ustaw True w dev, aby widzieć zapytania SQL w konsoli
    future=True
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency do wstrzykiwania sesji bazy danych w endpointach FastAPI"""
    async with AsyncSessionLocal() as session:
        yield session