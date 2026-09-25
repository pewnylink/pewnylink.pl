# tests/conftest.py
import sys
import os
from pathlib import Path
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

# 1. Dodanie katalogu głównego projektu do ścieżki Pythona
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 2. KLUCZOWE: Ustawiamy bazę w pamięci RAM ZANIM zaimportujemy moduły aplikacji!
os.environ["TESTING"] = "True"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from app.main import app
from app.db.session import get_db
from app.models.db_models import Base  # Dopasuj import do właściwego pliku z modelami

# 3. Tworzymy osobny silnik bazy SQLite wyłącznie dla testów (w pamięci RAM)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # Utrzymuje bazę w pamięci przez cały czas trwania testu
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# 4. Nadpisujemy bazę w FastAPI, aby endpointy w testach korzystały z pamięci RAM
async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(autouse=True)
async def setup_and_cleanup_db():
    """
    Tworzy tabele w czystej pamięci RAM przed każdym testem i czyści po nim.
    Baza deweloperska (postgreSQL/SQLite z pliku) nie jest nawet dotykana.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await test_engine.dispose()


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Gotowy klient HTTP do wykonywania testów endpointów FastAPI.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client