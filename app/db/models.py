import enum
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Integer, Boolean, DateTime, Float, ForeignKey, Text, Enum as SQLEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

# --- ENUMY SYSTEMOWE ---

class UserRole(str, enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"

class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"

# --- MODELE BAZODANOWE ---

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacje
    subscriptions: Mapped[List["UserSubscription"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    reports: Mapped[List["Report"]] = relationship(back_populates="user")
    audit_logs: Mapped[List["AuditLog"]] = relationship(back_populates="user")


class SubscriptionPackage(Base):
    __tablename__ = "subscription_packages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # np. "Pojedynczy", "Standard", "PRO"
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # np. "single", "standard", "pro"
    price_pln: Mapped[float] = mapped_column(Float, nullable=False)
    searches_included: Mapped[int] = mapped_column(Integer, default=1)  # Liczba audytów w pakiecie
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    subscriptions: Mapped[List["UserSubscription"]] = relationship(back_populates="package")


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    package_id: Mapped[int] = mapped_column(ForeignKey("subscription_packages.id"), nullable=False)

    status: Mapped[SubscriptionStatus] = mapped_column(SQLEnum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE)
    searches_left: Mapped[int] = mapped_column(Integer, default=0)
    valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="subscriptions")
    package: Mapped["SubscriptionPackage"] = relationship(back_populates="package")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)  # Unikalne ID, np. REF-2026-X89
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    target_url: Mapped[str] = mapped_column(Text, nullable=False)
    title_raw: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    risk_level: Mapped[str] = mapped_column(String(20), default="NISKIE")
    is_unlocked: Mapped[bool] = mapped_column(Boolean, default=False)

    # Cała struktura wygenerowanego raportu (json z Pydantic)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[Optional["User"]] = relationship(back_populates="reports")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    action: Mapped[str] = mapped_column(String(100), nullable=False)  # np. "GRANT_PACKAGE", "GENERATE_REPORT"
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[Optional["User"]] = relationship(back_populates="audit_logs")