# app/models/report.py
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, HttpUrl


class ReportCategory(str, Enum):
    AUTOMOTIVE = "automotive"
    REAL_ESTATE = "real_estate"
    ELECTRONICS = "electronics"
    OTHER = "other"


# --- SCHEMATY PYDANTIC DLA API ---

class ReportCreateRequest(BaseModel):
    url: HttpUrl


class LegalFlag(BaseModel):
    code: str
    title: str
    description: str
    severity: str


class ReportResponse(BaseModel):
    id: str
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