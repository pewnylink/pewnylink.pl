# app/models/report.py
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from pydantic import BaseModel, HttpUrl
from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# Warunkowy import tylko dla analizy statycznej Pylance
if TYPE_CHECKING:
    from app.models.user import User


class ReportCategory(str, Enum):
    AUTOMOTIVE = "automotive"
    REAL_ESTATE = "real_estate"
    ELECTRONICS = "electronics"
    OTHER = "other"


# --- MODEL ORM BAZY DANYCH (SQLAlchemy 2.0 / PostgreSQL) ---
class Report(Base):
    """
    Tabela przechowywania wygenerowanych i zanonimizowanych raportów audytowych.
    Zgodna z RODO i TDM (nie przetrzymuje multimediów ani PII sprzedawców).
    """
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    images_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    seller_type: Mapped[str] = mapped_column(String(64), nullable=False, default="Prywatny")
    
    total_price_with_tco: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_tco_extra: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    suggested_discount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    
    # Pełna zanonimizowana struktura audytu (listy ryzyk, wyliczenia TCO) w formacie JSON
    report_data: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    
    is_unlocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False
    )

    user: Mapped[Optional[User]] = relationship("User", back_populates="reports")


# --- SCHEMATY PYDANTIC DLA API ---

class ReportCreateRequest(BaseModel):
    url: HttpUrl


class LegalFlag(BaseModel):
    code: str
    title: str
    description: str
    severity: str


class ReportResponse(BaseModel):
    id: int
    url: str
    title: str
    price: float
    risk_level: str
    risk_score: int
    images_count: int
    seller_type: str
    total_price_with_tco: float
    total_tco_extra: float
    suggested_discount: float
    legal_flags: List[LegalFlag]
    negotiation_script: Optional[str] = None
    is_unlocked: bool
    created_at: datetime