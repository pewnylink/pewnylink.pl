# app/services/report_repository.py
import uuid
from typing import Optional, Dict, Any, Tuple
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import ReportModel, Voucher


class ReportRepository:
    """Produkcyjna warstwa I/O dla PostgreSQL (Neon.tech)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_report(
        self, report_data: Dict[str, Any], db: Optional[AsyncSession] = None
    ) -> ReportModel:
        """Bezpieczny zapis raportu z wykorzystaniem domyślnych wartości .get()."""
        session = db or self.db
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
        session.add(db_report)
        await session.commit()
        await session.refresh(db_report)
        return db_report

    async def get_by_id(self, report_identifier: Any) -> Optional[ReportModel]:
        """
        Bezpiecznie pobiera raport z bazy:
        - Dla liczby int: szuka po kluczu głównym `id` (INTEGER).
        - Dla stringa / UUID: szuka po biznesowym `report_id` (VARCHAR/TEXT).
        """
        if not report_identifier:
            return None

        # 1. Jeśli przekazano bezpośrednio liczbę (np. id = 12)
        if isinstance(report_identifier, int):
            stmt = select(ReportModel).where(ReportModel.id == report_identifier)
        
        # 2. Jeśli przekazano ciąg cyfr w stringu (np. "12")
        elif isinstance(report_identifier, str) and report_identifier.isdigit():
            stmt = select(ReportModel).where(
                or_(
                    ReportModel.id == int(report_identifier),
                    ReportModel.report_id == report_identifier
                )
            )

        # 3. Jeśli przekazano kod tekstowy (np. "REP-TEST-123") lub obiekt UUID
        else:
            identifier_str = str(report_identifier)
            stmt = select(ReportModel).where(ReportModel.report_id == identifier_str)

        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_report_id(self, report_identifier: Any) -> Optional[ReportModel]:
        """Alias zapewniający wsteczną kompatybilność ze starszymi wywołaniami."""
        return await self.get_by_id(report_identifier)

    async def unlock_report(self, report_identifier: Any) -> Optional[ReportModel]:
        """
        Symuluje potwierdzenie płatności (mock unlock).
        Ustawia is_unlocked = True i zapisuje zmiany w bazie.
        """
        report = await self.get_by_id(report_identifier)
        if not report:
            return None

        report.is_unlocked = True
        await self.db.commit()
        await session.refresh(report) if (session := self.db) else None
        return report

    async def unlock_with_voucher(
        self, report_identifier: Any, voucher_code: str
    ) -> Tuple[Optional[ReportModel], Optional[str]]:
        """
        Odblokowuje raport kodem vouchera.
        Zwraca krotkę: (report, error_message).
        """
        report = await self.get_by_id(report_identifier)
        if not report:
            return None, "Raport nie istnieje"

        if report.is_unlocked or getattr(report, "is_paid", False):
            return report, None

        # Weryfikacja vouchera w bazie
        stmt = select(Voucher).where(
            Voucher.code == voucher_code, Voucher.is_active == True
        )
        result = await self.db.execute(stmt)
        voucher = result.scalars().first()

        if not voucher:
            return None, "Nieprawidłowy lub już wykorzystany kod vouchera"

        # Odblokowanie raportu i dezaktywacja jednorazowego vouchera
        report.is_unlocked = True
        if hasattr(report, "is_paid"):
            report.is_paid = True

        voucher.is_active = False

        await self.db.commit()
        await self.db.refresh(report)
        return report, None