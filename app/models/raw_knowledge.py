# app/models/raw_knowledge.py
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class RawExpertKnowledge(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    category: str = Field(..., description="Np. machinery, medical, ebikes, us_cars")
    brand: str
    model: str
    source_url: str
    raw_defect_description: str
    extracted_keywords: List[str] = []
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(default="pending_approval", description="pending_approval | rejected")

    class Config:
        populate_by_name = True