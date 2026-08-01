import os
from fastapi import FastAPI, Request, Query, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from bson import ObjectId

from app.routers import admin, pages
from app.services.report_generator import generate_audit_report
from app.database import reports_collection

# 1. Tworzymy instancję aplikacji FastAPI
app = FastAPI(title="pewnylink.pl API", version="1.0.0")

# 2. Podłączamy routery (po utworzeniu obiektu app)
app.include_router(pages.router)
app.include_router(admin.router)

# Ścieżka do katalogu z szablonami i plikami statycznymi
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

templates = Jinja2Templates(directory=TEMPLATES_DIR)


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
    
    # Wywołanie logiki generowania raportu (AuditEngine + MongoDB)
    report_doc = await generate_audit_report(
        listing_text="",
        target_url=target_url,
        industry=industry,
        is_unlocked=admin
    )
    
    return templates.TemplateResponse(
        request=request, 
        name="report_view.html", 
        context={
            "report": report_doc,
            "target_url": target_url, 
            "is_admin": admin
        }
    )


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


# PODGLĄD ZAPISANEGO RAPORTU PO ZAPISANYM ID Z MONGODB
@app.get("/report/{report_id}", response_class=HTMLResponse)
async def get_report_by_id(
    request: Request, 
    report_id: str, 
    unlocked: bool = Query(False)
):
    try:
        doc = reports_collection.find_one({"_id": ObjectId(report_id)})
    except Exception:
        doc = None

    if not doc:
        raise HTTPException(status_code=404, detail="Raport nie został odnaleziony")

    doc["id"] = str(doc["_id"])
    if unlocked:
        doc["is_unlocked"] = True
        doc["is_paid"] = True

    return templates.TemplateResponse(
        request=request, 
        name="report_view.html", 
        context={
            "report": doc,
            "target_url": doc.get("target_url", ""),
            "is_admin": unlocked
        }
    )