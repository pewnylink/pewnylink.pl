import os
from uuid import UUID
from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.audit_service import AuditEngine

router = APIRouter(tags=["pages"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


async def get_optional_user(request: Request, db: AsyncSession = Depends(get_db)):
    """Pobiera zalogowanego użytkownika z sesji/ciasteczka, jeśli istnieje."""
    token = request.cookies.get("access_token") or request.headers.get("Authorization")
    if not token:
        return None
    try:
        from app.core.security import decode_access_token
        from app.models.db_models import User as DBUser
        from sqlalchemy import select

        if token.startswith("Bearer "):
            token = token.replace("Bearer ", "")

        payload = decode_access_token(token)
        if not payload:
            return None

        user_id = payload.get("sub") or payload.get("user_id")
        if not user_id:
            return None

        result = await db.execute(select(DBUser).where(DBUser.id == UUID(user_id)))
        return result.scalar_one_or_none()
    except Exception:
        return None


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, current_user: object = Depends(get_optional_user)):
    return templates.TemplateResponse(
        request=request, 
        name="index.html",
        context={"user": current_user}
    )


@router.get("/report", response_class=HTMLResponse)
async def report(
    request: Request, 
    url: str = Query(..., description="URL ogłoszenia do audytu"),
    current_user: object = Depends(get_optional_user)
):
    # Wywołujemy silnik analityczny
    report_data = await AuditEngine.analyze_url(url)

    # Weryfikujemy, czy użytkownik ma uprawnienia Administratora
    is_admin = False
    if current_user:
        is_admin = (
            getattr(current_user, "is_admin", False)
            or getattr(current_user, "role", None) in ["ADMIN", "admin"]
            or getattr(getattr(current_user, "role", None), "value", None) == "ADMIN"
        )

    # Jeśli użytkownik to Admin, wymuszamy odblokowanie pełnej treści w kontekście widoku
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