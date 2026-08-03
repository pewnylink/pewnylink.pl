from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

# Domyślnie SQLite async pod dev, w produkcji podmieniane na postgresql+asyncpg://...
DATABASE_URL = "sqlite+aiosqlite:///./sql_app.db"

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
    """Dependency do wstrzykiwania sesji w endpointach FastAPI"""
    async with AsyncSessionLocal() as session:
        yield session