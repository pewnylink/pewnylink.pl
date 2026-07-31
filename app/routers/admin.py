from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import os

router = APIRouter(prefix="/admin", tags=["admin"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# ATRAPA BAZY DANYCH / LOGIKI - Docelowo połączone z MongoDB / SQLite
def get_admin_stats():
    return {
        "total_revenue": 14250.00,
        "revenue_breakdown": {
            "start": 1200.00,     # 9,99 zł
            "standard": 5050.00,  # 79,99 zł
            "pro": 8000.00        # 229,99 zł
        },
        "total_users": 342,
        "active_users_30d": 189,
        "total_reports": 1420,
        "top_categories": [
            {"name": "Motoryzacja (Otomoto/OLX)", "count": 620, "percentage": 43.6},
            {"name": "Elektronika (Allegro/OLX)", "count": 410, "percentage": 28.8},
            {"name": "Nieruchomości", "count": 250, "percentage": 17.6},
            {"name": "Inne / E-sklepy", "count": 140, "percentage": 10.0},
        ],
        "top_domains": ["olx.pl", "otomoto.pl", "allegro.pl", "vinted.pl"]
    }

@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    # TODO: Weryfikacja sesji/uprawnień is_admin
    stats = get_admin_stats()
    return templates.TemplateResponse(
        request=request, 
        name="admin/dashboard.html", 
        context={"stats": stats}
    )

@router.post("/grant-package")
async def grant_package(
    user_email: str = Form(...),
    package_type: str = Form(...),
    reports_count: int = Form(...),
    validity_days: int = Form(...),
    reason: str = Form(...)
):
    # TODO: Logika przypisywania pakietu w bazie danych
    print(f"[ADMIN GRANT] Przydzielono dla {user_email}: {package_type} ({reports_count} raportów, {validity_days} dni). Powód: {reason}")
    return RedirectResponse(url="/admin/dashboard?success=granted", status_code=status.HTTP_303_SEE_OTHER)