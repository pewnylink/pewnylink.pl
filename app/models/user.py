# app/models/user.py
from enum import Enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field

class UserRole(str, Enum):
    SUPER_ADMIN = "SUPER_ADMIN"  # Seba & Wspólnik (unlimited)
    VIP_GUEST = "VIP_GUEST"      # Rodzina / Rekompensata (darmowy dostęp czasowy)
    USER = "USER"                # Standardowy klient

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: Optional[str] = "Użytkownik"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: UserRole
    access_until: Optional[datetime] = None
    created_at: datetime

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class VoucherCreate(BaseModel):
    code: str  # np. "KONKURS2026" lub "REKOMPENSATA14"
    days_validity: int = 14  # Na ile dni przyznaje dostęp
    max_uses: int = 1        # Ile osób może użyć kodu

class VoucherRedeem(BaseModel):
    code: str