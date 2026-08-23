from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.report_schema import ReportResponse
from app.services.report_generator import build_report_response, generate_audit_report
from app.services.report_repository import ReportRepository


class CreateReportRequest(BaseModel):
    url: str
    industry: str = "general"


class VoucherUnlockRequest(BaseModel):
    voucher_code: str


async def get_optional_user(
    request: Request, 
    db: AsyncSession = Depends(get_db)
):
    """Pobiera użytkownika z ciasteczka lub nagłówka Authorization."""
    token = request.cookies.get("access_token") or request.headers.get("Authorization")
    if not token:
        return None
    try:
        if token.startswith("Bearer "):
            token = token.replace("Bearer ", "", 1)

        from app.core.security import decode_access_token
        from app.models.db_models import User as DBUser
        from sqlalchemy import select
        from uuid import UUID

        payload = decode_access_token(token)
        if not payload:
            return None

        user_id_raw = payload.get("sub") or payload.get("user_id")
        if not user_id_raw:
            return None

        result = await db.execute(select(DBUser).where(DBUser.id == UUID(str(user_id_raw))))
        return result.scalar_one_or_none()
    except Exception:
        return None


# Ustawiamy prefix na /reports (main.py doda /api/v1 -> powstanie /api/v1/reports)
router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    payload: CreateReportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[object] = Depends(get_optional_user),
):
    """Tworzy nowy raport przez REST API."""
    target_url = payload.url.strip()
    if not target_url.startswith(("http://", "https://")):
        target_url = f"https://{target_url}"

    report_doc = await generate_audit_report(
        listing_text="",
        target_url=target_url,
        industry=payload.industry,
        is_unlocked=False
    )

    if current_user and hasattr(current_user, "id"):
        report_doc["user_id"] = current_user.id

    # Tworzymy instancję repozytorium z przekazaną sesją bazy danych
    repo = ReportRepository(db)
    saved_report = await repo.create_report(report_doc)
    
    return build_report_response(saved_report)

@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[object] = Depends(get_optional_user),
):
    """Pobiera raport na podstawie jego identyfikatora (np. REP-12345678)."""
    repo = ReportRepository(db)
    report = await repo.get_by_report_id(report_id)

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Raport '{report_id}' nie istnieje"
        )

    is_admin = False
    if current_user:
        role_val = getattr(current_user, "role", None)
        role_str = getattr(role_val, "value", role_val)
        is_admin = (
            getattr(current_user, "is_admin", False) 
            or str(role_str).upper() == "ADMIN"
        )

    return build_report_response(report, force_unlocked=is_admin)


@router.post("/{report_id}/mock-checkout", response_model=ReportResponse)
@router.post("/{report_id}/mock-unlock", response_model=ReportResponse)
async def mock_unlock_report(
    report_id: str, 
    db: AsyncSession = Depends(get_db)
):
    """Symuluje potwierdzenie płatności dla raportu."""
    repo = ReportRepository(db)
    report = await repo.unlock_report(report_id)

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Raport '{report_id}' nie istnieje"
        )

    return build_report_response(report)


@router.post("/{report_id}/unlock-voucher", response_model=ReportResponse)
async def unlock_report_with_voucher(
    report_id: str,
    payload: VoucherUnlockRequest,
    db: AsyncSession = Depends(get_db),
):
    """Odblokowuje raport przy użyciu kodu vouchera."""
    repo = ReportRepository(db)
    report, error_message = await repo.unlock_with_voucher(report_id, payload.voucher_code)

    if error_message:
        status_code = (
            status.HTTP_404_NOT_FOUND
            if "nie istnieje" in error_message.lower()
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=error_message)

    return build_report_response(report)