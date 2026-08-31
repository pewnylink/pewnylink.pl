# app/models/__init__.py

# Modele bazodanowe ORM (SQLAlchemy)
from app.models.db_models import ReportModel, Voucher, User
from app.models.affiliate import AffiliateOffer, AffiliateClickLog

# Schematy Pydantic i Enumy z user.py
from app.models.user import (
    UserRole, 
    UserRegister, 
    UserLogin, 
    UserResponse, 
    TokenResponse, 
    VoucherCreate, 
    VoucherRedeem,
)

# Schematy Pydantic i Enumy z report.py
from app.models.report import (
    ReportCategory, 
    ReportResponse, 
    LegalFlag, 
    ReportCreateRequest,
)

# Alias dla wstecznej kompatybilności (zabezpiecza miejsca w kodzie importujące 'Report')
Report = ReportModel

__all__ = [
    # Encje ORM
    "ReportModel",
    "Report",
    "Voucher",
    "User",
    "AffiliateOffer",
    "AffiliateClickLog",
    # Schematy i Enumy Użytkowników
    "UserRole",
    "UserRegister",
    "UserLogin",
    "UserResponse",
    "TokenResponse",
    "VoucherCreate",
    "VoucherRedeem",
    # Schematy i Enumy Raportów
    "ReportCategory",
    "ReportResponse",
    "LegalFlag",
    "ReportCreateRequest",
]