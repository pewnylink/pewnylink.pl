# app/models/verified_knowledge.py
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class SerialDefect(BaseModel):
    component: str
    description: str
    severity: str = Field(..., description="LOW | MEDIUM | HIGH | CRITICAL")
    estimated_repair_cost_pln: float

class VerifiedExpertKnowledge(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    category: str
    brand: str
    model: str
    production_years: List[int]
    known_serial_defects: List[SerialDefect] = []
    market_mth_median_per_year: Optional[float] = None
    service_requirements: List[str] = []
    approved_by: str = "SevArt Admin"
    approved_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True