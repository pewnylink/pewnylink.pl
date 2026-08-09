# app/config.py
from pathlib import Path
from typing import Optional
from pydantic import ConfigDict
from pydantic_settings import BaseSettings

# Ścieżka do katalogu głównego projektu
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    APP_NAME: str = "pewnylink.pl API"

    # Integracje zewnętrzne
    OPENAI_API_KEY: str = ""
    SCRAPER_API_KEY: str = ""

    # Konfiguracja Bazy Danych PostgreSQL
    DB_USER: Optional[str] = None
    DB_PASSWORD: Optional[str] = None
    DB_HOST: Optional[str] = None
    DB_PORT: str = "5432"
    DB_NAME: Optional[str] = None
    DATABASE_URL: Optional[str] = None

    # Ścieżki do zasobów
    CHECKLISTS_PATH: Path = BASE_DIR / "config" / "checklists.json"

    # Bezpieczeństwo JWT
    JWT_SECRET_KEY: str = "pewnylink_super_secret_key_2026_change_me_in_prod"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 dni

    model_config = ConfigDict(env_file=".env", extra="ignore")

    def get_database_url(self) -> str:
        """
        Zwraca zweryfikowany URL połączenia z bazą danych.
        Automatycznie prioryteryzuje dedykowane zmienne PostgreSQL AsyncPG.
        """
        if self.DATABASE_URL and self.DATABASE_URL.startswith("postgresql"):
            return self.DATABASE_URL

        if self.DB_USER and self.DB_PASSWORD and self.DB_HOST and self.DB_NAME:
            return (
                f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?ssl=require"
            )

        # Bezpieczny fallback dla lokalnego środowiska deweloperskiego (SQLite async)
        return f"sqlite+aiosqlite:///{BASE_DIR}/pewnylink.db"


settings = Settings()