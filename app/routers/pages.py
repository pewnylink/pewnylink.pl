import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user_optional
from app.models.db_models import ReportModel as DBReport, User as DBUser
from app.services.audit_service import AuditEngine
from app.services.checklist_service import load_checklist_by_industry
from app.services.report_generator import generate_audit_report
from app.services.report_repository import ReportRepository

logger = logging.getLogger(__name__)

router = APIRouter(tags=["pages"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

CATEGORY_DISPLAY_NAMES = {
    "automotive": "Motoryzacja",
    "motoryzacja": "Motoryzacja",
    "real_estate": "Nieruchomości",
    "nieruchomosci": "Nieruchomości",
    "heavy_machinery": "Maszyny rolnicze i budowlane",
    "sprzet_i_maszyny_rolnicze_oraz_budowlane": "Maszyny rolnicze i budowlane",
    "bicycles": "Rowery",
    "rowery": "Rowery",
    "medical_devices": "Sprzęt medyczny",
    "sprzet_i_urzadzenia_medyczne": "Sprzęt medyczny",
    "consumer electronics & IT": "Elektronika użytkowa i sprzęt IT",
    "elektronika_uzytkowa_i_sprzet_IT": "Elektronika użytkowa i sprzęt IT",
}


def check_is_admin(user: Optional[DBUser]) -> bool:
    """Sprawdzenie uprawnień administratora u użytkownika."""
    if not user:
        return False
    
    role_attr = getattr(user, "role", None)
    role_str = str(getattr(role_attr, "value", role_attr)).upper()
    
    return (
        getattr(user, "is_admin", False)
        or role_str in ["ADMIN", "SUPER_ADMIN"]
    )


def render_safe_template(request: Request, template_name: str, context: dict) -> HTMLResponse:
    """Bezpieczne renderowanie szablonów zapobiegające błędowi TemplateNotFound."""
    target_path = os.path.join(TEMPLATES_DIR, template_name)
    context["request"] = request
    
    if not os.path.exists(target_path):
        logger.warning(
            f"Szablon '{template_name}' nie istnieje w {TEMPLATES_DIR}. Renderowanie zastępcze 'index.html'."
        )
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context=context
        )
    return templates.TemplateResponse(
        request=request,
        name=template_name,
        context=context
    )


# --- STRONA GŁÓWNA I UŻYTKOWA ---

@router.get("/", response_class=HTMLResponse)
@router.get("/index.html", response_class=HTMLResponse)
async def home(
    request: Request, 
    current_user: Optional[DBUser] = Depends(get_current_user_optional)
):
    return render_safe_template(request, "index.html", {"user": current_user})


@router.get("/pricing", response_class=HTMLResponse)
@router.get("/pricing.html", response_class=HTMLResponse)
@router.get("/pricing/", response_class=HTMLResponse)
async def get_pricing_page(
    request: Request,
    current_user: Optional[DBUser] = Depends(get_current_user_optional)
):
    return render_safe_template(request, "pricing.html", {"user": current_user})


@router.get("/checkout", response_class=HTMLResponse)
@router.get("/checkout.html", response_class=HTMLResponse)
@router.get("/checkout/", response_class=HTMLResponse)
async def get_checkout_page(
    request: Request,
    type: Optional[str] = Query("single"),
    report: Optional[str] = Query(None),
    current_user: Optional[DBUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    report_data = None
    if report:
        report_data = await ReportRepository.get_by_report_id(db, report)

    return render_safe_template(
        request,
        "checkout.html",
        {
            "user": current_user,
            "checkout_type": type,
            "report_id": report,
            "report": report_data
        }
    )


# --- AUTORYZACJA I LOGOWANIE / WYLOGOWANIE ---

@router.get("/login", response_class=HTMLResponse)
@router.get("/login.html", response_class=HTMLResponse)
@router.get("/login/", response_class=HTMLResponse)
async def login_page(
    request: Request, 
    current_user: Optional[DBUser] = Depends(get_current_user_optional)
):
    if current_user:
        return RedirectResponse(url="/my-reports", status_code=status.HTTP_303_SEE_OTHER)

    return render_safe_template(request, "login.html", {"user": current_user})


@router.get("/register", response_class=HTMLResponse)
@router.get("/register.html", response_class=HTMLResponse)
@router.get("/register/", response_class=HTMLResponse)
async def register_page(
    request: Request, 
    current_user: Optional[DBUser] = Depends(get_current_user_optional)
):
    if current_user:
        return RedirectResponse(url="/my-reports", status_code=status.HTTP_303_SEE_OTHER)

    return render_safe_template(request, "register.html", {"user": current_user})


@router.get("/logout")
@router.get("/logout.html")
@router.get("/logout/")
@router.get("/api/v1/auth/logout")
@router.get("/auth/logout")
@router.post("/logout")
@router.post("/api/v1/auth/logout")
@router.post("/auth/logout")
async def logout():
    """Czyszczenie ciasteczek sesyjnych i przekierowanie do logowania."""
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    cookie_keys = ["access_token", "token", "session", "jwt", "authorization", "session_id"]
    for key in cookie_keys:
        response.delete_cookie(key=key, path="/")
        response.delete_cookie(key=key, path="/", httponly=True)
        response.delete_cookie(key=key, path="")
    return response


# --- RAPORTY ---

@router.get("/report", response_class=HTMLResponse)
async def get_report(
    request: Request, 
    url: str = Query(..., description="Adres URL oferty"), 
    admin: bool = Query(False, description="Flaga dostępu administratora"),
    industry: str = Query("elektronika_uzytkowa_i_sprzet_IT", description="Kategoria / Branża oferty"),
    current_user: Optional[DBUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    target_url = url.strip()
    if not target_url.startswith(("http://", "https://")):
        target_url = f"https://{target_url}"
    
    is_admin = check_is_admin(current_user) or admin
    
    report_doc = await generate_audit_report(
        listing_text="",
        target_url=target_url,
        industry=industry,
        is_unlocked=is_admin
    )
    
    report_doc["industry_name"] = CATEGORY_DISPLAY_NAMES.get(industry, "Inne / Ogólne")
    
    if current_user:
        report_doc["user_id"] = current_user.id
    
    saved_report = await ReportRepository.create_report(db, report_doc)
    unlocked_param = "?unlocked=true" if is_admin else ""
    return RedirectResponse(
        url=f"/report/{saved_report.report_id}{unlocked_param}", 
        status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/report", response_class=HTMLResponse)
async def create_report_post(
    request: Request,
    url: str = Form(...),
    industry: str = Form("elektronika_uzytkowa_i_sprzet_IT"),
    current_user: Optional[DBUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    target_url = url.strip()
    if not target_url.startswith(("http://", "https://")):
        target_url = f"https://{target_url}"

    is_admin = check_is_admin(current_user)

    report_doc = await generate_audit_report(
        listing_text="",
        target_url=target_url,
        industry=industry,
        is_unlocked=is_admin
    )

    report_doc["industry_name"] = CATEGORY_DISPLAY_NAMES.get(industry, "Inne / Ogólne")
    
    if current_user:
        report_doc["user_id"] = current_user.id

    saved_report = await ReportRepository.create_report(db, report_doc)
    unlocked_param = "?unlocked=true" if is_admin else ""
    return RedirectResponse(
        url=f"/report/{saved_report.report_id}{unlocked_param}", 
        status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("/report/{report_id}", response_class=HTMLResponse)
async def get_report_by_id(
    request: Request, 
    report_id: str, 
    unlocked: bool = Query(False),
    current_user: Optional[DBUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    doc = None
    is_admin = check_is_admin(current_user) or unlocked
    
    if report_id.startswith("REP-DEMO") or report_id == "demo":
        doc = await AuditEngine.analyze_url(
            url="https://www.olx.pl/d/oferta/priorytetowy-audyt-testowy-ID999.html",
            is_unlocked=is_admin,
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
            "is_unlocked": db_report.is_unlocked or is_admin,
            "risk_score": db_report.risk_score,
            "risk_level": db_report.risk_level,
            "freemium_preview": db_report.freemium_preview or {},
            "digital_footprint": db_report.digital_footprint or {},
            "financial_analysis": db_report.financial_analysis or {},
            "expert_checkpoints": db_report.expert_checkpoints or {},
            "negotiation_assistant": db_report.negotiation_assistant or {},
            "created_at_formatted": db_report.created_at.strftime("%d.%m.%Y") if db_report.created_at else ""
        }

    if is_admin:
        doc["is_unlocked"] = True
        doc["is_paid"] = True

    # --- POWIĄZANIE CHECKLISTY JSON DLA XTEMPLATU ---
    industry_key = doc.get("category") or "elektronika_uzytkowa_i_sprzet_IT"
    checklist_data = load_checklist_by_industry(industry_key)
    
    categories = checklist_data.get("categories") or checklist_data.get("paid_detailed_analysis", {}).get("categories", [])
    paid_modules = checklist_data.get("paid_post_analysis_modules") or checklist_data.get("ai_generated_action_plan", [])
    freemium_checkpoints = checklist_data.get("freemium_checkpoints") or checklist_data.get("public_free_summary", [])

    if not doc.get("expert_checkpoints") or not doc["expert_checkpoints"].get("categories"):
        doc["expert_checkpoints"] = {"categories": categories}
    
    if not doc.get("freemium_preview"):
        doc["freemium_preview"] = freemium_checkpoints

    doc["categories"] = categories
    doc["paid_modules"] = paid_modules

    return render_safe_template(
        request, 
        "report_view.html", 
        {
            "report": doc,
            "user": current_user,
            "target_url": doc.get("target_url", ""),
            "is_admin": is_admin,
            "categories": categories,
            "paid_modules": paid_modules
        }
    )


@router.get("/my-reports", response_class=HTMLResponse)
@router.get("/moje-raporty", response_class=HTMLResponse)
@router.get("/my-reports.html", response_class=HTMLResponse)
@router.get("/moje-raporty.html", response_class=HTMLResponse)
async def my_reports(
    request: Request,
    current_user: Optional[DBUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    result = await db.execute(
        select(DBReport)
        .where(DBReport.user_id == current_user.id)
        .order_by(desc(DBReport.created_at))
    )
    user_reports = result.scalars().all()

    return render_safe_template(
        request,
        "my_reports.html",
        {
            "user": current_user,
            "reports": user_reports
        }
    )


# --- DOKUMENTY PRAWNE I KONTAKT ---

@router.get("/regulamin", response_class=HTMLResponse)
@router.get("/regulamin.html", response_class=HTMLResponse, include_in_schema=False)
@router.get("/regulamin/", response_class=HTMLResponse, include_in_schema=False)
async def regulamin_page(
    request: Request,
    current_user: Optional[DBUser] = Depends(get_current_user_optional)
):
    return render_safe_template(request, "regulamin.html", {"user": current_user})


@router.get("/polityka-prywatnosci", response_class=HTMLResponse)
@router.get("/polityka-prywatnosci.html", response_class=HTMLResponse, include_in_schema=False)
@router.get("/polityka-prywatnosci/", response_class=HTMLResponse, include_in_schema=False)
@router.get("/polityka_prywatnosci", response_class=HTMLResponse, include_in_schema=False)
async def polityka_prywatnosci_page(
    request: Request,
    current_user: Optional[DBUser] = Depends(get_current_user_optional)
):
    return render_safe_template(request, "polityka_prywatnosci.html", {"user": current_user})


@router.get("/polityka-cookies", response_class=HTMLResponse)
@router.get("/polityka-cookies.html", response_class=HTMLResponse, include_in_schema=False)
@router.get("/polityka-cookies/", response_class=HTMLResponse, include_in_schema=False)
@router.get("/polityka_cookies", response_class=HTMLResponse, include_in_schema=False)
async def polityka_cookies_page(
    request: Request,
    current_user: Optional[DBUser] = Depends(get_current_user_optional)
):
    return render_safe_template(request, "polityka_cookies.html", {"user": current_user})


@router.get("/prawa-konsumenta", response_class=HTMLResponse)
@router.get("/prawa-konsumenta.html", response_class=HTMLResponse, include_in_schema=False)
@router.get("/prawa-konsumenta/", response_class=HTMLResponse, include_in_schema=False)
@router.get("/prawa_konsumenta", response_class=HTMLResponse, include_in_schema=False)
async def prawa_konsumenta_page(
    request: Request,
    current_user: Optional[DBUser] = Depends(get_current_user_optional)
):
    return render_safe_template(request, "prawa_konsumenta.html", {"user": current_user})


@router.get("/kontakt", response_class=HTMLResponse)
@router.get("/kontakt.html", response_class=HTMLResponse)
@router.get("/kontakt/", response_class=HTMLResponse)
async def kontakt_page(
    request: Request,
    current_user: Optional[DBUser] = Depends(get_current_user_optional)
):
    return render_safe_template(request, "kontakt.html", {"user": current_user})