# app/routers/pages.py
import os
from typing import Optional
from fastapi import APIRouter, Depends, Request, Query, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user_optional
from app.services.audit_service import AuditEngine
from app.models.db_models import User as DBUser, ReportModel as DBReport

router = APIRouter(tags=["pages"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, current_user: Optional[DBUser] = Depends(get_current_user_optional)):
    return templates.TemplateResponse(
        request=request, 
        name="index.html",
        context={"user": current_user}
    )


@router.get("/report", response_class=HTMLResponse)
async def report(
    request: Request, 
    url: str = Query(..., description="URL ogłoszenia do audytu"),
    current_user: Optional[DBUser] = Depends(get_current_user_optional)
):
    report_data = await AuditEngine.analyze_url(url)

    is_admin = False
    if current_user:
        is_admin = (
            getattr(current_user, "is_admin", False)
            or getattr(current_user, "role", None) in ["ADMIN", "admin"]
            or getattr(getattr(current_user, "role", None), "value", None) == "ADMIN"
        )

    if is_admin:
        if isinstance(report_data, dict):
            report_data["is_unlocked"] = True
            report_data["is_paid"] = True
        elif hasattr(report_data, "is_unlocked"):
            report_data.is_unlocked = True

    return templates.TemplateResponse(
        request=request, 
        name="report_view.html", 
        context={"report": report_data, "user": current_user}
    )


@router.get("/my-reports", response_class=HTMLResponse)
@router.get("/moje-raporty", response_class=HTMLResponse)
async def my_reports(
    request: Request,
    current_user: Optional[DBUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Wyświetla listę raportów wygenerowanych przez zalogowanego użytkownika."""
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    result = await db.execute(
        select(DBReport)
        .where(DBReport.user_id == current_user.id)
        .order_by(desc(DBReport.created_at))
    )
    user_reports = result.scalars().all()

    return templates.TemplateResponse(
        request=request,
        name="my_reports.html",
        context={
            "request": request,
            "user": current_user,
            "reports": user_reports
        }
    )


@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request, 
    current_user: Optional[DBUser] = Depends(get_current_user_optional)
):
    if current_user:
        return RedirectResponse(url="/my-reports", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"request": request, "user": current_user}
    )


@router.get("/register", response_class=HTMLResponse)
async def register_page(
    request: Request, 
    current_user: Optional[DBUser] = Depends(get_current_user_optional)
):
    if current_user:
        return RedirectResponse(url="/my-reports", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={"request": request, "user": current_user}
    )