# app/api/v1/endpoints/reports.py
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.report_generator import generate_audit_report
from app.services.report_repository import ReportRepository

router = APIRouter(prefix="/reports", tags=["Reports"])


class ReportCreateRequest(BaseModel):
    target_url: str
    listing_text: Optional[str] = None
    industry: str = "general"


def _format_and_mask_report(report_obj: Any) -> Dict[str, Any]:
    """
    Konwertuje obiekt modelu SQLAlchemy do słownika i maskuje sekcje premium,
    jeśli raport nie został opłacony (is_unlocked == False).
    """
    is_unlocked = getattr(report_obj, "is_unlocked", False)

    report_dict = {
        "id": str(getattr(report_obj, "id")),
        "report_id": getattr(report_obj, "report_id"),
        "target_url": getattr(report_obj, "target_url"),
        "source_url": getattr(report_obj, "source_url", None),
        "title_raw": getattr(report_obj, "title_raw", None),
        "category": getattr(report_obj, "category", None),
        "industry_name": getattr(report_obj, "industry_name", None),
        "risk_score": getattr(report_obj, "risk_score", None),
        "risk_level": getattr(report_obj, "risk_level", None),
        "is_paid": getattr(report_obj, "is_paid", False),
        "is_unlocked": is_unlocked,
        "freemium_preview": getattr(report_obj, "freemium_preview", {}),
        "created_at": getattr(report_obj, "created_at", None),
    }

    if is_unlocked:
        # Raport odblokowany -> pełne dane
        report_dict.update({
            "digital_footprint": getattr(report_obj, "digital_footprint", {}),
            "financial_analysis": getattr(report_obj, "financial_analysis", {}),
            "expert_checkpoints": getattr(report_obj, "expert_checkpoints", {}),
            "negotiation_assistant": getattr(report_obj, "negotiation_assistant", {}),
        })
    else:
        # Raport darmowy/zablokowany -> sekcje płatne ustawione na None
        report_dict.update({
            "digital_footprint": None,
            "financial_analysis": None,
            "expert_checkpoints": None,
            "negotiation_assistant": None,
        })

    return report_dict


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_report(
    payload: ReportCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Tworzy nowy raport na podstawie adresu URL i opcjonalnego tekstu ogłoszenia,
    zapisuje go w bazie PostgreSQL (Neon.tech) i zwraca podgląd Freemium.
    """
    try:
        report_doc = await generate_audit_report(
            listing_text=payload.listing_text or "Analiza z poziomu API PewnyLink",
            target_url=payload.target_url,
            industry=payload.industry,
            is_unlocked=False,
        )

        saved_report = await ReportRepository.create_report(db, report_doc)
        return _format_and_mask_report(saved_report)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Błąd podczas generowania raportu: {str(e)}",
        )


@router.get("/{report_id}")
async def get_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Pobiera raport z bazy danych na podstawie identyfikatora report_id.
    Automatycznie maskuje zawartość płatną, jeśli is_unlocked == False.
    """
    report = await ReportRepository.get_by_report_id(db, report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Raport o identyfikatorze '{report_id}' nie istnieje.",
        )

    return _format_and_mask_report(report)