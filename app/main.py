import os
from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routers import admin, pages

# 1. Tworzymy instancję aplikacji FastAPI
app = FastAPI(title="pewnylink.pl API", version="1.0.0")

# 2. Podłączamy routery (po utworzeniu obiektu app)
app.include_router(pages.router)
app.include_router(admin.router)

# Ścieżka do katalogu z szablonami
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

# GŁÓWNA STRONA (LANDING PAGE)
@app.get("/", response_class=HTMLResponse)
async def get_landing_page(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

# STRONA RAPORTU AUDYTOWEGO
@app.get("/report", response_class=HTMLResponse)
async def get_report(
    request: Request, 
    url: str = Query(..., description="Adres URL oferty"), 
    admin: bool = Query(False, description="Flaga dostępu administratora")
):
    target_url = url.strip()
    if not target_url.startswith(("http://", "https://")):
        target_url = f"https://{target_url}"
    
    # Tutaj wywołujesz swoją istniejącą logikę z services/report_generator.py
    # Przestawiamy renderowanie na szablon report_view.html
    return templates.TemplateResponse(
        request=request, 
        name="report_view.html", 
        context={"target_url": target_url, "is_admin": admin}
    )