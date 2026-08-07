# app/models/user.py
from enum import Enum
from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, EmailStr, Field, ConfigDict

class UserRole(str, Enum):
    SUPER_ADMIN = "SUPER_ADMIN"  # Seba & Adrian (unlimited)
    VIP_GUEST = "VIP_GUEST"      # Rodzina / Rekompensata (darmowy dostęp czasowy)
    USER = "USER"                # Standardowy klient

class AccessScope(str, Enum):
    ALL = "ALL"                        # Pełny dostęp do wszystkich raportów i narzędzi
    REPORTS_ONLY = "REPORTS_ONLY"      # Dostęp wyłącznie do generowania raportów
    SINGLE_REPORT = "SINGLE_REPORT"    # Dostęp do jednego wskazanego raportu

class GrantReason(str, Enum):
    ADMIN_OWNER = "ADMIN_OWNER"        # Właściciel / Admin
    FAMILY = "FAMILY"                  # Rodzina / Znajomi
    COMPENSATION = "COMPENSATION"      # Rekompensata za błąd w serwisie
    CONTEST_WINNER = "CONTEST_WINNER"  # Wygrana w konkursie
    PROMO_VOUCHER = "PROMO_VOUCHER"    # Kod rabatowy / Voucher
    OTHER = "OTHER"                    # Inne ustalenia

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
    is_unlimited: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# --- Ręczne Przydzielanie Dostępu (Dla Admina) ---
class GrantAccessRequest(BaseModel):
    user_email: EmailStr
    scope: AccessScope = AccessScope.ALL
    reason: GrantReason = GrantReason.COMPENSATION
    note: Optional[str] = None  # Opis/notatka, np. "Dostęp w ramach przeprosin za awarię z 07.08"
    days_validity: Optional[int] = 14  # None = dostęp bezterminowy, int = liczba dni
    is_unlimited: bool = False  # True = bezterminowy pełny dostęp

class AccessGrantResponse(BaseModel):
    id: str
    user_email: EmailStr
    scope: AccessScope
    reason: GrantReason
    note: Optional[str] = None
    granted_by: str  # Email admina, który przyznał dostęp
    expires_at: Optional[datetime] = None
    created_at: datetime

# --- Vouchery i Kody Dostępowe ---
class VoucherCreate(BaseModel):
    code: str  # np. "KONKURS2026" lub "REKOMPENSATA14"
    days_validity: int = 14  # Na ile dni przyznaje dostęp
    max_uses: int = 1        # Ile osób może użyć kodu
    reason: GrantReason = GrantReason.PROMO_VOUCHER
    scope: AccessScope = AccessScope.ALL

class VoucherRedeem(BaseModel):
    code: str

class VoucherResponse(BaseModel):
    id: str
    code: str
    days_validity: int
    max_uses: int
    current_uses: int
    reason: GrantReason
    scope: AccessScope
    created_at: datetime
    is_active: bool = True

# --- Statystyki i Analityka dla Panelu Admina ---
class IndustryStats(BaseModel):
    industry_name: str       # np. "Motoryzacja", "Nieruchomości", "Elektronika/RTV", "Inne"
    report_count: int        # Liczba wygenerowanych raportów
    percentage: float        # Udział procentowy w całości (np. 42.5%)

class DashboardStatsResponse(BaseModel):
    total_reports: int                       # Wszystkie wygenerowane raporty
    total_users: int                         # Liczba użytkowników
    active_grants_count: int                 # Liczba aktywnych darmowych dostępów
    total_revenue_pln: float                 # Przychod brutto
    top_industries: List[IndustryStats]      # Statystyki branżowe
    reports_last_30_days: Dict[str, int]     # Aktywność dzienna (YYYY-MM-DD -> liczba)