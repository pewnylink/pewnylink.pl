# app/core/config.py
from pathlib import Path
from typing import List, Optional
from pydantic import ConfigDict, model_validator
from pydantic_settings import BaseSettings

# Ścieżka do katalogu głównego projektu pewnylink.pl
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # Podstawowe informacje o projekcie
    PROJECT_NAME: str = "PewnyLink.pl API"
    ENVIRONMENT: str = "development"
    FRONTEND_URL: str = "http://localhost:8000"

    # Ścieżki do zasobów
    CHECKLISTS_PATH: Path = BASE_DIR / "config" / "checklists.json"

    # Baza danych SQL (Domyślnie lokalny SQLite z roota, z możliwością nadpisania przez PostgreSQL w .env)
    DATABASE_URL: Optional[str] = "sqlite+aiosqlite:///./sql_app.db"
    DB_USER: Optional[str] = None
    DB_PASSWORD: Optional[str] = None
    DB_HOST: Optional[str] = None
    DB_PORT: str = "5432"
    DB_NAME: Optional[str] = None

    # Bezpieczeństwo i JWT
    SECRET_KEY: str = "DEV_ONLY_INSECURE_SECRET_KEY_CHANGE_THIS_IN_ENV_123456789"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 godziny

    # Integracja ze Stripe (Płatności Online)
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # Zewnętrzne API (LLM + Scraper)
    OPENAI_API_KEY: str = ""
    SCRAPERAPI_KEY: str = ""
    SCRAPER_API_KEY: str = ""  # Alias wymagany przez ScraperEngine

    # Nagłówki CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:8000", "http://127.0.0.1:8000"]

    # Lista e-maili administratorów
    ADMIN_EMAILS: List[str] = [
        "sebo3010@gmail.com",
        "Adrian.u9277@gmail.com"
    ]

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @model_validator(mode="after")
    def sync_scraper_keys(self) -> "Settings":
        """Synchronizuje wartości między SCRAPERAPI_KEY i SCRAPER_API_KEY."""
        key = self.SCRAPERAPI_KEY or self.SCRAPER_API_KEY
        if key:
            self.SCRAPERAPI_KEY = key
            self.SCRAPER_API_KEY = key
        return self

    def get_database_url(self) -> str:
        """
        Zwraca właściwy URL połączenia z bazą danych.
        Automatycznie prioryteryzuje PostgreSQL z .env, a w razie braku – SQLite.
        """
        if self.DATABASE_URL and self.DATABASE_URL.startswith("postgresql"):
            return self.DATABASE_URL

        if self.DB_USER and self.DB_PASSWORD and self.DB_HOST and self.DB_NAME:
            return (
                f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?ssl=require"
            )

        return self.DATABASE_URL or f"sqlite+aiosqlite:///{BASE_DIR}/sql_app.db"

    def __getattr__(self, item: str):
        """Dynamiczny fallback zapobiegający AttributeError przy zapytaniach o warianty klucza scrapera."""
        item_upper = item.upper()
        if item_upper in ("SCRAPERAPI_KEY", "SCRAPER_API_KEY", "SCRAPER_KEY"):
            return self.SCRAPERAPI_KEY or self.SCRAPER_API_KEY or ""
        raise AttributeError(f"'Settings' object has no attribute '{item}'")


settings = Settings()