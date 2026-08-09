# app/models/user.py
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, TYPE_CHECKING
from pydantic import BaseModel, EmailStr
from sqlalchemy import String, DateTime, Enum as SQLEnum, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# Warunkowy import tylko dla analizy statycznej Pylance (zapobiega cyklowi)
if TYPE_CHECKING:
    from app.models.report import Report


class UserRole(str, Enum):
    """Uprawnienia użytkowników w systemie pewnylink.pl"""
    USER = "USER"                 # Zwykły zarejestrowany użytkownik
    VIP_GUEST = "VIP_GUEST"       # Użytkownik z aktywnym kodem/subskrypcją
    SUPER_ADMIN = "SUPER_ADMIN"   # Administrator pełny


# --- MODEL ORM BAZY DANYCH (SQLAlchemy 2.0 / PostgreSQL) ---
class User(Base):
    """
    Tabela użytkowników systemu.
    Przechowuje dane aktywacyjne, dostęp dostępnościowy oraz powiązane raporty.
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="Klucz główny użytkownika"
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False, comment="Unikalny e-mail (login)"
    )
    password_hash: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Zahasłowane hasło (bcrypt)"
    )
    full_name: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, comment="Imię i nazwisko lub nazwa firmy"
    )
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, native_enum=False), 
        default=UserRole.USER, 
        nullable=False,
        comment="Rola w systemie"
    )
    access_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        nullable=True,
        comment="Data wygaśnięcia płatnego dostępu / vouchera (UTC)"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False,
        comment="Data rejestracji konta"
    )

    # Relacja do zanonimizowanych raportów użytkownika (1-do-wielu)
    reports: Mapped[List[Report]] = relationship(
        "Report", back_populates="user", cascade="all, delete-orphan"
    )


# --- SCHEMATY PYDANTIC (WALIDACJA DANYCH WEJŚCIOWYCH I WYJŚCIOWYCH API) ---

class UserRegister(BaseModel):
    """Rejestracja nowego konta"""
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    """Logowanie do systemu"""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Profil użytkownika zwracany w API"""
    id: str
    email: str
    full_name: Optional[str] = None
    role: UserRole
    access_until: Optional[datetime] = None
    created_at: datetime


class TokenResponse(BaseModel):
    """Odpowiedź z tokenem JWT po zalogowaniu / rejestracji"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class VoucherCreate(BaseModel):
    """Tworzenie nowego vouchera (Tylko Super Admin)"""
    code: str
    days_validity: int
    max_uses: int = 1


class VoucherRedeem(BaseModel):
    """Realizacja kodu vouchera przez użytkownika"""
    code: str