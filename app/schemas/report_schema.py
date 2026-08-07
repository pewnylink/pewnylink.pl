# app/schemas/report_schema.py
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ReportSummary(BaseModel):
    score: float = Field(..., description="Ocena atrakcyjności 1.0 - 10.0")
    risk_level: str = Field(..., description="Poziom ryzyka: LOW, MEDIUM, HIGH")
    market_price_diff_percent: Optional[float] = Field(
        None, description="Różnica względem ceny rynkowej (%)"
    )
    verdict_summary: str = Field(
        ..., description="Ogólna ocena i najważniejszy wniosek"
    )


class ReportDeepAnalysis(BaseModel):
    red_flags: List[str] = Field(
        default_factory=list, description="Wykryte spójności i haczyki"
    )
    checklist: List[str] = Field(
        default_factory=list, description="Checklista pytań do sprzedawcy"
    )
    negotiation_tips: List[str] = Field(
        default_factory=list, description="Skrypt negocjacyjny i cena docelowa"
    )


class ReportCreate(BaseModel):
    url: str = Field(..., description="Link do oferty do przeanalizowania")


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    report_id: str
    target_url: str
    is_unlocked: bool
    created_at: datetime

    summary: ReportSummary
    deep_analysis: Optional[ReportDeepAnalysis] = None