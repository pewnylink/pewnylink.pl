# tests/conftest.py
import sys
from pathlib import Path
import pytest_asyncio

# Dodanie katalogu głównego projektu do ścieżki Pythona
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Dostosuj import poniżej do rzeczywistej ścieżki pliku database.py w Twoim projekcie:
# - Jeśli plik to app/database.py -> from app.database import engine
# - Jeśli plik to app/core/database.py -> from app.core.database import engine
from app.database import engine


@pytest_asyncio.fixture(autouse=True)
async def cleanup_db_engine():
    """
    Automatycznie zwalnia pulę połączeń asyncpg po każdym teście.
    Dzięki temu każdy kolejny test nawiązuje czyste połączenie w swojej pętli asyncio.
    """
    yield
    await engine.dispose()