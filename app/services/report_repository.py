# app/services/report_repository.py
import uuid
from typing import Optional, Dict, Any
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import ReportModel


class ReportRepository:
    """Produkcyjna warstwa I/O dla PostgreSQL (Neon.tech)."""

    @staticmethod
    async def create_report(db: AsyncSession, report_data: Dict[str, Any]) -> ReportModel:
        """Bezpieczny zapis raportu z wykorzystaniem domyślnych wartości .get() zapobiegających błędom KeyError."""
        db_report = ReportModel(
            report_id=report_data["report_id"],
            target_url=report_data["target_url"],
            source_url=report_data["source_url"],
            title_raw=report_data.get("title_raw", "Ogłoszenie bez tytułu"),
            category=report_data.get("category", "general"),
            industry_name=report_data.get("industry_name", "Analiza Ogólna"),
            is_paid=report_data.get("is_paid", False),
            is_unlocked=report_data.get("is_unlocked", False),
            risk_score=report_data.get("risk_score", 30),
            risk_level=report_data.get("risk_level", "NISKIE"),
            freemium_preview=report_data["freemium_preview"],
            digital_footprint=report_data["digital_footprint"],
            financial_analysis=report_data["financial_analysis"],
            expert_checkpoints=report_data["expert_checkpoints"],
            negotiation_assistant=report_data["negotiation_assistant"],
        )
        db.add(db_report)
        await db.commit()
        await db.refresh(db_report)
        return db_report

    @staticmethod
    async def get_by_report_id(db: AsyncSession, report_identifier: str) -> Optional[ReportModel]:
        """Pobiera raport z bazy bez względu na to, czy podano czytelny kod (REP-XXXXX) czy ciąg UUID."""
        try:
            val_uuid = uuid.UUID(report_identifier)
            stmt = select(ReportModel).where(
                or_(ReportModel.report_id == report_identifier, ReportModel.id == val_uuid)
            )
        except ValueError:
            stmt = select(ReportModel).where(ReportModel.report_id == report_identifier)
            
        result = await db.execute(stmt)
        return result.scalars().first()