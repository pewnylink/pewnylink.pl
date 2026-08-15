# app/api/v1/endpoints/reports.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.report_schema import ReportCreate, ReportResponse
from app.services.report_generator import generate_audit_report, format_report_response
from app.services.report_repository import ReportRepository

router = APIRouter(prefix="/reports", tags=["Reports API"])


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
    """
    KROK 1: Pobiera raport po report_id.
    Jeśli is_unlocked == False, sekcja deep_analysis jest maskowana (zwraca null).
    """
    db_report = await ReportRepository.get_by_report_id(db, report_id)
    if not db_report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Raport '{report_id}' nie istnieje.",
        )
    return format_report_response(db_report)


@router.post("/{report_id}/mock-checkout", response_model=ReportResponse)
async def mock_checkout_api(report_id: str, db: AsyncSession = Depends(get_db)):
    """
    KROK 2: Bezkosztowa symulacja opłacenia raportu.
    Zmienia is_unlocked = True w bazie danych i zwraca pełny, odsłonięty raport.
    """
    db_report = await ReportRepository.get_by_report_id(db, report_id)
    if not db_report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Raport '{report_id}' nie istnieje.",
        )

    # Odblokowujemy raport
    db_report.is_unlocked = True
    await db.commit()
    await db.refresh(db_report)

    return format_report_response(db_report)