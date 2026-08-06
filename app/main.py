# app/main.py
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Query, Form, HTTPException, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.routers import admin, pages
from app.services.report_generator import generate_audit_report
from app.services.audit_service import AuditEngine
from app.services.report_repository import ReportRepository
from app.database import engine, Base, get_db
import app.models.db_models  # Rejestracja modeli w SQLAlchemy przed migracją


# 1. Zarządzanie cyklem życia aplikacji (Lifespan)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Automatyczne tworzenie tabel w PostgreSQL (Neon.tech) przy starcie serwera
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


# 2. Tworzymy instancję aplikacji FastAPI z cyklem życia lifespan
app = FastAPI(title="pewnylink.pl API", version="1.0.0", lifespan=lifespan)

# 3. Podłączamy routery
app.include_router(pages.router)
app.include_router(admin.router)

# Ścieżka do katalogu z szablonami i plikami statycznymi
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

templates = Jinja2Templates(directory=TEMPLATES_DIR)


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


# STRONA GENEROWANIA RAPORTU AUDYTOWEGO (GET ze skanera/linku)
@app.get("/report", response_class=HTMLResponse)
async def get_report(
    request: Request, 
    url: str = Query(..., description="Adres URL oferty"), 
    admin: bool = Query(False, description="Flaga dostępu administratora"),
    industry: str = Query("general", description="Kategoria / Branża oferty"),
    db: AsyncSession = Depends(get_db)
):
    target_url = url.strip()
    if not target_url.startswith(("http://", "https://")):
        target_url = f"https://{target_url}"
    
    # 1. Generowanie struktury raportu w pamięci
    report_doc = await generate_audit_report(
        listing_text="",
        target_url=target_url,
        industry=industry,
        is_unlocked=admin
    )
    
    # 2. Zapis w PostgreSQL przez ReportRepository
    saved_report = await ReportRepository.create_report(db, report_doc)
    
    unlocked_param = "?unlocked=true" if admin else ""
    return RedirectResponse(url=f"/report/{saved_report.report_id}{unlocked_param}", status_code=303)


# STRONA GENEROWANIA RAPORTU (POST z formularza głównego)
@app.post("/report", response_class=HTMLResponse)
async def create_report_post(
    request: Request,
    url: str = Form(...),
    industry: str = Form("general"),
    db: AsyncSession = Depends(get_db)
):
    target_url = url.strip()
    if not target_url.startswith(("http://", "https://")):
        target_url = f"https://{target_url}"

    # 1. Generowanie struktury raportu w pamięci
    report_doc = await generate_audit_report(
        listing_text="",
        target_url=target_url,
        industry=industry,
        is_unlocked=False
    )

    # 2. Zapis w PostgreSQL przez ReportRepository
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
    
    # OBSŁUGA RAPORTU TESTOWEGO / DEMO
    if report_id.startswith("REP-DEMO") or report_id == "demo":
        doc = await AuditEngine.analyze_url(
            url="https://www.olx.pl/d/oferta/priorytetowy-audyt-testowy-ID999.html",
            is_unlocked=unlocked,
            report_id=report_id
        )
        doc["id"] = report_id
    else:
        # Pobranie trwałego raportu z bazy danych PostgreSQL
        db_report = await ReportRepository.get_by_report_id(db, report_id)
        if not db_report:
            raise HTTPException(
                status_code=404, 
                detail=f"Raport o identyfikatorze '{report_id}' nie został znaleziony."
            )
        
        # Przekształcenie rekordu SQL na słownik dla szablonów Jinja2
        doc = {
            "id": str(db_report.id),
            "report_id": db_report.report_id,
            "target_url": db_report.target_url,
            "source_url": db_report.source_url,
            "title_raw": db_report.title_raw,
            "category": db_report.category,
            "industry_name": db_report.industry_name,
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