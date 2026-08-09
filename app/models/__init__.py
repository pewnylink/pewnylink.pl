# app/models/__init__.py
from app.models.user import (
    User, 
    UserRole, 
    UserRegister, 
    UserLogin, 
    UserResponse, 
    TokenResponse, 
    VoucherCreate, 
    VoucherRedeem
)
from app.models.voucher import Voucher
from app.models.report import (
    Report, 
    ReportCategory, 
    ReportResponse, 
    LegalFlag, 
    ReportCreateRequest
)

__all__ = [
    "User",
    "UserRole",
    "UserRegister",
    "UserLogin",
    "UserResponse",
    "TokenResponse",
    "VoucherCreate",
    "VoucherRedeem",
    "Voucher",
    "Report",
    "ReportCategory",
    "ReportResponse",
    "LegalFlag",
    "ReportCreateRequest",
]