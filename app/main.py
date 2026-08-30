# app/main.py
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

import app.models.db_models  # Rejestracja modeli w SQLAlchemy przed migracją
from app.api.v1.endpoints.payments import router as payments_api_router
from app.api.v1.endpoints.reports import router as reports_api_router
from app.db.session import Base, engine, get_db
from app.routers import admin, auth, pages


# 1. Zarządzanie cyklem życia aplikacji (Lifespan)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Automatyczne tworzenie tabel w PostgreSQL przy starcie serwera
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


# 2. Tworzenie instancji aplikacji FastAPI
app = FastAPI(
    title="pewnylink.pl API",
    version="1.0.0",
    lifespan=lifespan
)

# 2a. Konfiguracja CORS (Cross-Origin Resource Sharing)
raw_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:8000,https://pewnylink.pl,https://www.pewnylink.pl"
)
allowed_origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# 2b. Podłączenie plików statycznych
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# 3. Podłączanie routerów
app.include_router(pages.router)
app.include_router(admin.router)
app.include_router(auth.router)  # Usunięto prefix="/auth" – router ma już prefiks w auth.py
app.include_router(reports_api_router, prefix="/api/v1")
app.include_router(payments_api_router, prefix="/api/v1")

# 4. ENDPOINT MONITORINGU DLA CRON-JOB.ORG / HEALTH CHECK
@app.get("/health", tags=["Monitoring"])
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Baza danych nie odpowiada: {str(e)}"
        )