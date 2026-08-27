# app/api/v1/endpoints/reports.py
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.db_models import Voucher
from app.schemas.report_schema import ReportCreate, ReportResponse
from app.services.report_generator import generate_audit_report, format_report_response
from app.services.report_repository import ReportRepository

router = APIRouter(prefix="/reports", tags=["Reports API"])


class VoucherRequest(BaseModel):
    voucher_code: str


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report_api(payload: ReportCreate, db: AsyncSession = Depends(get_db)):
    """Tworzy nowy darmowy raport w bazie danych."""
    target_url = payload.url.strip()
    if not target_url.startswith(("http://", "https://")):
        target_url = f"https://{target_url}"

    report_doc = await generate_audit_report(
        listing_text="",
        target_url=target_url,
        industry="general",
        is_unlocked=False,
    )
    saved_report = await ReportRepository.create_report(db, report_doc)
    return format_report_response(saved_report)


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report_api(report_id: str, db: AsyncSession = Depends(get_db)):
    """Pobiera raport po report_id. Maskuje deep_analysis jeśli is_unlocked == False."""
    clean_report_id = report_id.strip()
    db_report = await ReportRepository.get_by_report_id(db, clean_report_id)
    if not db_report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Raport '{clean_report_id}' nie istnieje.",
        )
    return format_report_response(db_report)


@router.post("/{report_id}/mock-checkout", response_model=ReportResponse)
async def mock_checkout_api(report_id: str, db: AsyncSession = Depends(get_db)):
    """Symulacja opłacenia raportu – zmienia is_unlocked = True w bazie."""
    clean_report_id = report_id.strip()
    db_report = await ReportRepository.get_by_report_id(db, clean_report_id)
    if not db_report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Raport '{clean_report_id}' nie istnieje.",
        )

    db_report.is_unlocked = True
    await db.commit()
    await db.refresh(db_report)

    return format_report_response(db_report)


@router.post("/{report_id}/voucher", response_model=ReportResponse)
async def unlock_with_voucher_api(
    report_id: str, payload: VoucherRequest, db: AsyncSession = Depends(get_db)
):
    """Odblokowuje raport przy użyciu aktywnego kodu vouchera z bazy danych."""
    clean_report_id = report_id.strip()
    clean_voucher_code = payload.voucher_code.strip()

    db_report = await ReportRepository.get_by_report_id(db, clean_report_id)
    if not db_report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Raport '{clean_report_id}' nie istnieje.",
        )

    stmt = select(Voucher).where(
        Voucher.code == clean_voucher_code,
        Voucher.is_active.is_(True),
    )
    result = await db.execute(stmt)
    voucher = result.scalar_one_or_none()

    if not voucher:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nieprawidłowy lub nieaktywny kod vouchera.",
        )

    db_report.is_unlocked = True
    voucher.is_active = False
    await db.commit()
    await db.refresh(db_report)

    return format_report_response(db_report)