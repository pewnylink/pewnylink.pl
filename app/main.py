# app/main.py
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, Form, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

import app.models.db_models  # Rejestracja modeli w SQLAlchemy przed migracją
from app.api.v1.endpoints.payments import router as payments_api_router
from app.api.v1.endpoints.reports import router as reports_api_router
from app.db.session import Base, engine, get_db
from app.dependencies import get_current_user_optional
from app.models.db_models import User
from app.routers import admin, auth, pages
from app.services.audit_service import AuditEngine
from app.services.report_generator import generate_audit_report
from app.services.report_repository import ReportRepository

# Słownik etykiet branż dla widoków
CATEGORY_DISPLAY_NAMES = {
    "automotive": "Motoryzacja",
    "real_estate": "Nieruchomości",
    "heavy_machinery": "Maszyny ciężkie",
    "bicycles": "Rowery",
    "medical_devices": "Sprzęt medyczny",
    "general": "Inne / Ogólne",
}


# 1. Zarządzanie cyklem życia aplikacji (Lifespan)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Automatyczne tworzenie tabel w PostgreSQL przy starcie serwera
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


# 2. Tworzenie instancji aplikacji FastAPI
app = FastAPI(title="pewnylink.pl API", version="1.0.0", lifespan=lifespan)

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

# Ścieżka do katalogu z szablonami i plikami statycznymi
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

# 3. Podłączanie routerów (Strony HTML, Panel Admina, Autentykacja oraz REST API)
app.include_router(pages.router)
app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(reports_api_router, prefix="/api/v1")
app.include_router(payments_api_router, prefix="/api/v1")


# 4. ENDPOINT MONITORINGU DLA CRON-JOB.ORG
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


# GŁÓWNA STRONA (LANDING PAGE)
@app.get("/", response_class=HTMLResponse)
async def get_landing_page(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


# STRONA CENNIKA
@app.get("/pricing", response_class=HTMLResponse)
async def get_pricing_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="pricing.html" if os.path.exists(os.path.join(TEMPLATES_DIR, "pricing.html")) else "index.html",
        context={"request": request}
    )


# STRONA ZAMÓWIENIA / CHECKOUT
@app.get("/checkout", response_class=HTMLResponse)
async def get_checkout_page(
    request: Request,
    type: Optional[str] = Query("single"),
    report: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    report_data = None
    if report:
        report_data = await ReportRepository.get_by_report_id(db, report)

    return templates.TemplateResponse(
        request=request,
        name="checkout.html" if os.path.exists(os.path.join(TEMPLATES_DIR, "checkout.html")) else "index.html",
        context={
            "request": request,
            "checkout_type": type,
            "report_id": report,
            "report": report_data
        }
    )


# STRONA GENEROWANIA RAPORTU AUDYTOWEGO (GET ze skanera/linku)
@app.get("/report", response_class=HTMLResponse)
async def get_report(
    request: Request, 
    url: str = Query(..., description="Adres URL oferty"), 
    admin: bool = Query(False, description="Flaga dostępu administratora"),
    industry: str = Query("general", description="Kategoria / Branża oferty"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    target_url = url.strip()
    if not target_url.startswith(("http://", "https://")):
        target_url = f"https://{target_url}"
    
    report_doc = await generate_audit_report(
        listing_text="",
        target_url=target_url,
        industry=industry,
        is_unlocked=admin
    )
    
    report_doc["industry_name"] = CATEGORY_DISPLAY_NAMES.get(industry, "Inne / Ogólne")
    
    if current_user:
        report_doc["user_id"] = current_user.id
    
    saved_report = await ReportRepository.create_report(db, report_doc)
    unlocked_param = "?unlocked=true" if admin else ""
    return RedirectResponse(url=f"/report/{saved_report.report_id}{unlocked_param}", status_code=303)


# STRONA GENEROWANIA RAPORTU (POST z formularza głównego)
@app.post("/report", response_class=HTMLResponse)
async def create_report_post(
    request: Request,
    url: str = Form(...),
    industry: str = Form("general"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    target_url = url.strip()
    if not target_url.startswith(("http://", "https://")):
        target_url = f"https://{target_url}"

    report_doc = await generate_audit_report(
        listing_text="",
        target_url=target_url,
        industry=industry,
        is_unlocked=False
    )

    report_doc["industry_name"] = CATEGORY_DISPLAY_NAMES.get(industry, "Inne / Ogólne")
    
    if current_user:
        report_doc["user_id"] = current_user.id

    saved_report = await ReportRepository.create_report(db, report_doc)
    return RedirectResponse(url=f"/report/{saved_report.report_id}", status_code=303)


# PODGLĄD ZAPISANEGO RAPORTU PO ID LUB WIDOK DEMO
@app.get("/report/{report_id}", response_class=HTMLResponse)
async def get_report_by_id(
    request: Request, 
    report_id: str, 
    unlocked: bool = Query(False),
    db: AsyncSession = Depends(get_db)
):
    doc = None
    
    if report_id.startswith("REP-DEMO") or report_id == "demo":
        doc = await AuditEngine.analyze_url(
            url="https://www.olx.pl/d/oferta/priorytetowy-audyt-testowy-ID999.html",
            is_unlocked=unlocked,
            report_id=report_id
        )
        doc["id"] = report_id
        doc["industry_name"] = CATEGORY_DISPLAY_NAMES.get(doc.get("category", "general"), "Inne / Ogólne")
    else:
        db_report = await ReportRepository.get_by_report_id(db, report_id)
        if not db_report:
            raise HTTPException(
                status_code=404, 
                detail=f"Raport o identyfikatorze '{report_id}' nie został znaleziony."
            )
        
        doc = {
            "id": str(db_report.id),
            "report_id": db_report.report_id,
            "target_url": db_report.target_url,
            "source_url": db_report.source_url,
            "title_raw": db_report.title_raw,
            "category": db_report.category,
            "industry_name": getattr(db_report, "industry_name", CATEGORY_DISPLAY_NAMES.get(db_report.category, "Inne / Ogólne")),
            "is_paid": db_report.is_paid,
            "is_unlocked": db_report.is_unlocked or unlocked,
            "risk_score": db_report.risk_score,
            "risk_level": db_report.risk_level,
            "freemium_preview": db_report.freemium_preview,
            "digital_footprint": db_report.digital_footprint,
            "financial_analysis": db_report.financial_analysis,
            "expert_checkpoints": db_report.expert_checkpoints,
            "negotiation_assistant": db_report.negotiation_assistant,
            "created_at_formatted": db_report.created_at.strftime("%d.%m.%Y") if db_report.created_at else ""
        }

    return templates.TemplateResponse(
        request=request, 
        name="report_view.html", 
        context={
            "report": doc,
            "target_url": doc.get("target_url", ""),
            "is_admin": doc.get("is_unlocked", False)
        }
    )