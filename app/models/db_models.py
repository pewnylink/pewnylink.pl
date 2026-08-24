# app/models/db_models.py
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import String, Boolean, DateTime, Integer, Index, ForeignKey, JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ReportModel(Base):
    """Tabela 'reports' w bazie reprezentująca trwałe dane raportów SaaS."""
    __tablename__ = "reports"

    # Unikalny klucz główny UUID4
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    
    # Czytelny Identyfikator raportu np. REP-8A1F3C90
    report_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    
    # Klucz obcy powiązany z użytkownikiem (opcjonalny - dla raportów niezalogowanych użytkowników może być NULL)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="SET NULL"), 
        nullable=True
    )

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
    
    # Złożone struktury z Pydantic przechowywane jako uniwersalny JSON (JSONB w PostgreSQL, JSON w SQLite)
    freemium_preview: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    digital_footprint: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    financial_analysis: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    expert_checkpoints: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    negotiation_assistant: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    
    # Znaczniki czasu z obsługą stref czasowych
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False,
        index=True
    )

    # Relacja ORM do modelu User
    user: Mapped[Optional["User"]] = relationship(
        "User", 
        back_populates="reports"
    )

    __table_args__ = (
        Index("idx_reports_created_category", "created_at", "category"),
        {"extend_existing": True},
    )


class Voucher(Base):
    """Tabela 'vouchers' reprezentująca jednorazowe kody dostępowe do raportów."""
    __tablename__ = "vouchers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False
    )

    __table_args__ = {"extend_existing": True}


class User(Base):
    """Tabela 'users' reprezentująca użytkowników systemu."""
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="USER", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False
    )

    # Relacja ORM do raportów powiązanych z użytkownikiem
    reports: Mapped[List["ReportModel"]] = relationship(
        "ReportModel", 
        back_populates="user", 
        cascade="all, delete-orphan"
    )

    __table_args__ = {"extend_existing": True}