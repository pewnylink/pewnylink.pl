from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.report_schema import ReportResponse
from app.services.report_generator import build_report_response
from app.services.report_repository import ReportRepository

router = APIRouter(prefix="/api/v1/reports", tags=["Reports"])


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(report_id: UUID, db: AsyncSession = Depends(get_db)):
    repo = ReportRepository(db)
    report = await repo.get_by_id(report_id)

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Raport nie istnieje"
        )

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