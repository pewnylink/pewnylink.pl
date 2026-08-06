# app/config.py
from pathlib import Path
from pydantic import ConfigDict
from pydantic_settings import BaseSettings

# Ścieżka do katalogu głównego projektu (C:\Users\Seba\pewnylink.pl)
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    APP_NAME: str = "pewnylink.pl API"
    SCRAPERAPI_KEY: str = ""

    # Baza danych
    DATABASE_URL: str = "sqlite:///./pewnylink.db"

    # Ścieżki do zasobów
    CHECKLISTS_PATH: Path = BASE_DIR / "config" / "checklists.json"

    # Bezpieczeństwo JWT
    JWT_SECRET_KEY: str = "pewnylink_super_secret_key_2026_change_me_in_prod"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # Token ważny przez 30 dni

    model_config = ConfigDict(env_file=".env", extra="ignore")


settings = Settings()