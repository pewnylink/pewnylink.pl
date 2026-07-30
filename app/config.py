# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Bezpiecznik.pl API"
    SCRAPERAPI_KEY: str = ""
    MONGODB_URL: str = "mongodb://localhost:27017/bezpiecznik_db"
    DATABASE_NAME: str = "bezpiecznik_db"
    
    # Bezpieczeństwo JWT
    JWT_SECRET_KEY: str = "sevart_bezpiecznik_super_secret_key_2026_change_me_in_prod"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # Token ważny przez 30 dni

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()