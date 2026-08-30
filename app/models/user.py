# app/models/user.py
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, EmailStr


class UserRole(str, Enum):
    """Uprawnienia użytkowników w systemie pewnylink.pl"""
    USER = "USER"                 # Zwykły zarejestrowany użytkownik
    VIP_GUEST = "VIP_GUEST"       # Użytkownik z aktywnym kodem/subskrypcją
    ADMIN = "ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"   # Administrator pełny


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