import os
from fastapi import FastAPI, Request, Query, Form, HTTPException, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.routers import admin, pages
from app.services.report_generator import generate_audit_report
from app.services.audit_service import AuditEngine
from app.database import get_db  # Pobiera asynchroniczną sesję z PostgreSQL

# 1. Tworzymy instancję aplikacji FastAPI
app = FastAPI(title="pewnylink.pl API", version="1.0.0")

# 2. Podłączamy routery
app.include_router(pages.router)
app.include_router(admin.router)

# Ścieżka do katalogu z szablonami i plikami statycznymi
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

templates = Jinja2Templates(directory=TEMPLATES_DIR)


# 3. ENDPOINT DLA CRON-JOB.ORG (PODTRZYMANIE BAZY I SERWERA)
@app.get("/health", tags=["Monitoring"])
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        # Wykonuje szybkie zapytanie SELECT 1 do PostgreSQL na Neon.tech
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
    industry: str = Query("general", description="Kategoria / Branża oferty")
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
    
    report_id = report_doc["id"]
    unlocked_param = "?unlocked=true" if admin else ""
    
    return RedirectResponse(url=f"/report/{report_id}{unlocked_param}", status_code=303)


# STRONA GENEROWANIA RAPORTU (POST z formularza głównego)
@app.post("/report", response_class=HTMLResponse)
async def create_report_post(
    request: Request,
    url: str = Form(...),
    industry: str = Form("general")
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

    return RedirectResponse(url=f"/report/{report_doc['id']}", status_code=303)


# PODGLĄD ZAPISANEGO RAPORTU PO ID LUB WIDOK DEMO
@app.get("/report/{report_id}", response_class=HTMLResponse)
async def get_report_by_id(
    request: Request, 
    report_id: str, 
    unlocked: bool = Query(False)
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
        # Miejsce na zapytanie SQLAlchemy do bazy PostgreSQL
        raise HTTPException(
            status_code=404, 
            detail="Raporty z bazy danych będą dostępne po zdefiniowaniu modeli PostgreSQL."
        )

    return templates.TemplateResponse(
        request=request, 
        name="report_view.html", 
        context={
            "report": doc,
            "target_url": doc.get("target_url", ""),
            "is_admin": doc.get("is_unlocked", False)
        }
    )