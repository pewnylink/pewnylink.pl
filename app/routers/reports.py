from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.report_schema import ReportResponse
from app.services.report_generator import build_report_response
from app.services.report_repository import ReportRepository


async def get_optional_user(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Pobiera zalogowanego użytkownika z ciasteczka lub nagłówka Authorization, jeśli istnieje.
    """
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


router = APIRouter(prefix="/api/v1/reports", tags=["Reports"])


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[object] = Depends(get_optional_user),
):
    repo = ReportRepository(db)
    report = await repo.get_by_id(report_id)

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Raport nie istnieje"
        )

    # Jeśli użytkownik jest Administratorem, przyznajemy pełny dostęp do raportu
    if current_user:
        is_admin = (
            getattr(current_user, "is_admin", False)
            or getattr(current_user, "role", None) in ["ADMIN", "admin"]
            or getattr(getattr(current_user, "role", None), "value", None) == "ADMIN"
        )
        if is_admin:
            report.is_unlocked = True

    return build_report_response(report)


@router.post("/{report_id}/mock-unlock", response_model=ReportResponse)
async def mock_unlock_report(report_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Symuluje potwierdzenie płatności bez podłączania zewnętrznych bramek.
    Ustawia is_unlocked = True w bazie danych.
    """
    repo = ReportRepository(db)
    report = await repo.unlock_report(report_id)

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Raport nie istnieje"
        )

    return build_report_response(report)