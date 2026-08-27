# tests/conftest.py
import sys
from pathlib import Path
import pytest_asyncio

# Dodanie katalogu głównego projektu do ścieżki Pythona
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import engine, Base


@pytest_asyncio.fixture(autouse=True)
async def setup_and_cleanup_db():
    """
    Automatycznie tworzy strukturę tabel przed każdym testem
    oraz zwalnia pętlę połączeń po jego zakończeniu.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    await engine.dispose()