# app/core/config.py
from typing import List
from pydantic import ConfigDict, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Podstawowe informacje o projekcie
    PROJECT_NAME: str = "PewnyLink.pl API"
    ENVIRONMENT: str = "development"
    
    # Baza danych SQL
    DATABASE_URL: str = "sqlite+aiosqlite:///./sql_app.db"

    # Bezpieczeństwo i JWT
    SECRET_KEY: str = "DEV_ONLY_INSECURE_SECRET_KEY_CHANGE_THIS_IN_ENV_123456789"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 godziny

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

    def __getattr__(self, item: str):
        """Dynamiczny fallback zapobiegający AttributeError przy zapytaniach o warianty klucza scrapera."""
        item_upper = item.upper()
        if item_upper in ("SCRAPERAPI_KEY", "SCRAPER_API_KEY", "SCRAPER_KEY"):
            return self.SCRAPERAPI_KEY or self.SCRAPER_API_KEY or ""
        raise AttributeError(f"'Settings' object has no attribute '{item}'")


settings = Settings()