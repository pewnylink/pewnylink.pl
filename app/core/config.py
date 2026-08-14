from typing import List
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

    # Nagłówki CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:8000", "http://127.0.0.1:8000"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    # Lista e-maili administratorów (wpisz Wasze adresy e-mail):
    ADMIN_EMAILS: list[str] = [
        "sebo3010@gmail.com",
        "Adrian.u9277@gmail.com"
    ]


settings = Settings()