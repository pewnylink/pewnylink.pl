# app/routers/reports.py
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.report_schema import ReportCreate, ReportResponse
from app.services.report_generator import generate_audit_report, format_report_response
from app.services.report_repository import ReportRepository

router = APIRouter(prefix="/reports", tags=["Reports API"])


class VoucherRequest(BaseModel):
    voucher_code: str


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(payload: ReportCreate, db: AsyncSession = Depends(get_db)):
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
    repo = ReportRepository(db)
    saved_report = await repo.create_report(report_doc)
    return format_report_response(saved_report)


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(report_id: str, db: AsyncSession = Depends(get_db)):
    """Pobiera raport po report_id. Maskuje deep_analysis jeśli is_unlocked == False."""
    clean_report_id = report_id.strip()
    repo = ReportRepository(db)
    db_report = await repo.get_by_report_id(clean_report_id)
    if not db_report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Raport '{clean_report_id}' nie istnieje.",
        )
    return format_report_response(db_report)


@router.post("/{report_id}/mock-checkout", response_model=ReportResponse)
async def mock_checkout(report_id: str, db: AsyncSession = Depends(get_db)):
    """Symulacja opłacenia raportu – zmienia is_unlocked = True w bazie."""
    clean_report_id = report_id.strip()
    repo = ReportRepository(db)
    db_report = await repo.unlock_report(clean_report_id)
    if not db_report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Raport '{clean_report_id}' nie istnieje.",
        )
    return format_report_response(db_report)


@router.post("/{report_id}/voucher", response_model=ReportResponse)
async def unlock_with_voucher(
    report_id: str, payload: VoucherRequest, db: AsyncSession = Depends(get_db)
):
    """Odblokowuje raport przy użyciu aktywnego kodu vouchera z bazy danych."""
    clean_report_id = report_id.strip()
    clean_voucher_code = payload.voucher_code.strip()

    repo = ReportRepository(db)
    report, error = await repo.unlock_with_voucher(clean_report_id, clean_voucher_code)

    if error:
        if "nie istnieje" in error.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error,
        )

    return format_report_response(report)