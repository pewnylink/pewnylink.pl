from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os

from app.services.audit_service import AuditEngine

router = APIRouter(tags=["pages"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@router.get("/report", response_class=HTMLResponse)
async def report(request: Request, url: str = Query(..., description="URL ogłoszenia do audytu")):
    # Wywołujemy nasz silnik analityczny
    report_data = await AuditEngine.analyze_url(url)
    
    return templates.TemplateResponse(
        request=request, 
        name="report_view.html", 
        context={"report": report_data}
    )