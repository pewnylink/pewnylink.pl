# app/models/db_models.py
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import String, Boolean, DateTime, Integer, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ReportModel(Base):
    """Tabela 'reports' w bazie PostgreSQL reprezentująca trwałe dane raportów SaaS."""
    __tablename__ = "reports"

    # Unikalny klucz główny UUID4
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    
    # Czytelny Identyfikator raportu np. REP-8A1F3C90
    report_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    
    # Dane podstawowe ogłoszenia
    target_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    title_raw: Mapped[str] = mapped_column(String(512), nullable=False, default="Ogłoszenie bez tytułu")
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="general")
    industry_name: Mapped[str] = mapped_column(String(128), nullable=False, default="Analiza Ogólna")
    
    # Statusy płatności i dostępu
    is_paid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_unlocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Wyniki analizy ryzyka
    risk_score: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), default="NISKIE", nullable=False)
    
    # Złożone struktury z Pydantic przechowywane natywnie jako PostgreSQL JSONB
    freemium_preview: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    digital_footprint: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    financial_analysis: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    expert_checkpoints: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    negotiation_assistant: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    
    # Znaczniki czasu z obsługą stref czasowych
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False,
        index=True
    )

    __table_args__ = (
        Index("idx_reports_created_category", "created_at", "category"),
    )