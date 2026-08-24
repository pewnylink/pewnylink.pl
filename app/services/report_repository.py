# app/services/report_repository.py
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import ReportModel, Voucher


def _sanitize_for_json(obj: Any) -> Any:
    """Rekurencyjnie konwertuje obiekty datetime na string w formacie ISO dla bezpiecznego zapisu w kolumnach JSONB."""
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize_for_json(i) for i in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    return obj


def _to_uuid_or_none(val: Any) -> Any:
    """Konwertuje ciąg tekstowy na uuid.UUID, jeśli jest poprawnym UUID. Konieczne dla SQLite."""
    if isinstance(val, str):
        try:
            return uuid.UUID(val)
        except ValueError:
            return val
    return val


def _resolve_session_and_args(self_or_cls: Any, *args: Any) -> Tuple[Optional[AsyncSession], List[Any]]:
    """Elastycznie wyciąga sesję AsyncSession oraz pozostałe argumenty zapytania."""
    session = None
    remaining = list(args)

    if hasattr(self_or_cls, "db") and isinstance(getattr(self_or_cls, "db"), AsyncSession):
        session = self_or_cls.db
    elif isinstance(self_or_cls, AsyncSession):
        session = self_or_cls

    for i, arg in enumerate(remaining):
        if isinstance(arg, AsyncSession):
            if not session:
                session = arg
            remaining.pop(i)
            break

    return session, remaining


class ReportRepository:
    """Produkcyjna warstwa I/O dla PostgreSQL (Neon.tech) i SQLite."""

    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db

    async def create_report(self_or_cls, *args: Any) -> ReportModel:
        """Bezpieczny zapis raportu z automatyczną sanitaryzacją typów JSONB oraz UUID."""
        session, remaining = _resolve_session_and_args(self_or_cls, *args)

        if not session or not remaining or not isinstance(remaining[0], dict):
            raise ValueError("Nieprawidłowe parametry wywołania create_report.")

        data = remaining[0]

        db_report = ReportModel(
            report_id=str(data["report_id"]),
            target_url=data["target_url"],
            source_url=data["source_url"],
            title_raw=data.get("title_raw", "Ogłoszenie bez tytułu"),
            category=data.get("category", "general"),
            industry_name=data.get("industry_name", "Analiza Ogólna"),
            is_paid=data.get("is_paid", False),
            is_unlocked=data.get("is_unlocked", False),
            risk_score=data.get("risk_score", 30),
            risk_level=data.get("risk_level", "NISKIE"),
            freemium_preview=_sanitize_for_json(data.get("freemium_preview")),
            digital_footprint=_sanitize_for_json(data.get("digital_footprint")),
            financial_analysis=_sanitize_for_json(data.get("financial_analysis")),
            expert_checkpoints=_sanitize_for_json(data.get("expert_checkpoints")),
            negotiation_assistant=_sanitize_for_json(data.get("negotiation_assistant")),
        )

        if data.get("id"):
            db_report.id = _to_uuid_or_none(data["id"])
        if data.get("user_id"):
            db_report.user_id = _to_uuid_or_none(data["user_id"])
        if data.get("created_at"):
            db_report.created_at = data["created_at"]

        session.add(db_report)
        await session.commit()
        await session.refresh(db_report)
        return db_report

    async def get_by_id(self_or_cls, *args: Any) -> Optional[ReportModel]:
        """Pobiera raport z bazy po kluczu id (INTEGER/UUID) lub report_id (VARCHAR/TEXT)."""
        session, remaining = _resolve_session_and_args(self_or_cls, *args)

        if not session:
            raise ValueError("Nie przekazano prawidłowej sesji AsyncSession.")

        if not remaining or remaining[0] is None:
            return None

        identifier = remaining[0]

        if isinstance(identifier, int):
            stmt = select(ReportModel).where(ReportModel.id == identifier)
        elif isinstance(identifier, str) and identifier.isdigit():
            stmt = select(ReportModel).where(
                or_(
                    ReportModel.id == int(identifier),
                    ReportModel.report_id == identifier,
                )
            )
        else:
            identifier_uuid = _to_uuid_or_none(identifier)
            identifier_str = str(identifier)
            
            if isinstance(identifier_uuid, uuid.UUID):
                stmt = select(ReportModel).where(
                    or_(
                        ReportModel.id == identifier_uuid,
                        ReportModel.report_id == identifier_str,
                    )
                )
            else:
                stmt = select(ReportModel).where(ReportModel.report_id == identifier_str)

        result = await session.execute(stmt)
        return result.scalars().first()

    async def get_by_report_id(self_or_cls, *args: Any) -> Optional[ReportModel]:
        """Alias zapewniający wsteczną kompatybilność."""
        session, remaining = _resolve_session_and_args(self_or_cls, *args)
        repo_obj = ReportRepository(session)
        return await repo_obj.get_by_id(*remaining)

    async def unlock_report(self_or_cls, *args: Any) -> Optional[ReportModel]:
        """Symuluje potwierdzenie płatności (mock unlock)."""
        session, remaining = _resolve_session_and_args(self_or_cls, *args)

        if not session:
            raise ValueError("Nie przekazano prawidłowej sesji AsyncSession.")

        if not remaining or remaining[0] is None:
            return None

        identifier = remaining[0]
        if hasattr(identifier, "report_id"):
            identifier = getattr(identifier, "report_id")

        repo_obj = ReportRepository(session)
        report = await repo_obj.get_by_id(identifier)
        if not report:
            return None

        report.is_unlocked = True
        if hasattr(report, "is_paid"):
            report.is_paid = True

        await session.commit()
        await session.refresh(report)
        return report

    async def unlock_with_voucher(
        self_or_cls, *args: Any
    ) -> Tuple[Optional[ReportModel], Optional[str]]:
        """Odblokowuje raport kodem vouchera. Zwraca krotkę: (report, error_message)."""
        session, remaining = _resolve_session_and_args(self_or_cls, *args)

        if not session:
            raise ValueError("Nie przekazano prawidłowej sesji AsyncSession.")

        if len(remaining) < 2:
            return None, "Nieprawidłowe parametry zapytania"

        arg1, arg2 = remaining[0], remaining[1]

        identifier = arg1
        if hasattr(identifier, "report_id"):
            identifier = getattr(identifier, "report_id")

        if isinstance(arg2, dict):
            code = arg2.get("voucher_code") or arg2.get("code") or str(arg2)
        elif hasattr(arg2, "voucher_code"):
            code = getattr(arg2, "voucher_code")
        elif hasattr(arg2, "code"):
            code = getattr(arg2, "code")
        else:
            code = str(arg2)

        repo_obj = ReportRepository(session)
        report = await repo_obj.get_by_id(identifier)
        if not report:
            return None, "Raport nie istnieje"

        if report.is_unlocked or getattr(report, "is_paid", False):
            return report, None

        stmt = select(Voucher).where(
            Voucher.code == code,
            Voucher.is_active.is_(True)
        )
        result = await session.execute(stmt)
        voucher = result.scalars().first()

        if not voucher:
            return report, "Nieprawidłowy lub już wykorzystany kod vouchera"

        report.is_unlocked = True
        if hasattr(report, "is_paid"):
            report.is_paid = True

        voucher.is_active = False

        await session.commit()
        await session.refresh(report)
        return report, None