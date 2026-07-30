# app/models/report.py
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl
from app.legal.legal_shield import MANDATORY_DISCLAIMER

# --- CZĘŚĆ I: Cyfrowy Ślad i Metadane (1-9) ---
class DigitalFootprint(BaseModel):
    listing_id: str
    first_seen_timestamp: datetime
    active_days_on_market: int
    seller_account_age_days: int
    seller_rating_avg: Optional[float] = None
    multi_account_score: float = Field(..., description="0-100% ryzyka duplikatów")
    crime_density_rate: float = Field(..., description="Wskaźnik z art. 286 k.k. na 10k mieszkańców pow. KGP/GUS")
    nlp_manipulation_score: float = Field(..., description="Wskaźnik presji psychologicznej / użycia translatora")
    exif_analysis: Dict[str, Any] = {}
    risk_phrases_detected: List[str] = []
    cross_portal_duplicates: List[HttpUrl] = []
    accessory_bait_warning: bool = False

# --- CZĘŚĆ II: Moduły Branżowe (10-24) ---
class MachineryModule(BaseModel):
    mth_declared: float
    mth_market_median: float
    price_curve_deviation_percent: float
    factory_defects_matrix: List[Dict[str, Any]] = []
    pledge_registry_instructions: str
    emission_stage: str
    dpf_adblue_risk_level: str
    nearest_service_distance_km: float

class MedicalModule(BaseModel):
    passport_validity_status: str
    ce_jurisdiction_valid: bool
    estimated_tco_3year_pln: float
    seller_krs_ceidg_audit: Dict[str, Any] = {}

class EBikeModule(BaseModel):
    stolen_registry_checked: bool
    stolen_status: str
    battery_soh_estimated_percent: float
    frame_material_fatigue_risk: str

class USCarModule(BaseModel):
    title_status: str = Field(..., description="CLEAN | SALVAGE | JUNK | UNKNOWN")
    hidden_vin_alert: bool

# --- CZĘŚĆ III: Analiza Finansowa (25-26) ---
class FinancialAnalysis(BaseModel):
    price_deviation_index_pdi: float = Field(..., description="Wskaźnik anomalii cenowej PDI")
    tax_form: str = Field(..., description="FV 23% | VAT-Marża | Umowa K-S")
    pcc3_tax_risk_pln: float

# --- CZĘŚĆ IV: Asystent Negocjacyjny i Podsumowanie (27-30) ---
class NegotiationAssistant(BaseModel):
    llm_generated_questions: List[str] = Field(..., min_length=3, max_length=3)
    inspection_checklist: List[str] = []
    safety_shield_percentage: float = Field(..., description="0-100% ogólnego wskaźnika zaufania")
    shield_badge_color: str = Field(..., description="GREEN | YELLOW | RED")

class FullBezpiecznikReport(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    source_url: str
    title_raw: str
    deep_link: str
    category: str = Field(..., description="machinery | medical | ebikes | us_cars")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    algorithm_version: str = "Bezpiecznik AI v1.0-SevArt"
    
    # 30 Punktów Standardu
    digital_footprint: DigitalFootprint
    machinery_module: Optional[MachineryModule] = None
    medical_module: Optional[MedicalModule] = None
    ebike_module: Optional[EBikeModule] = None
    us_car_module: Optional[USCarModule] = None
    financial_analysis: FinancialAnalysis
    negotiation_assistant: NegotiationAssistant
    
    # Tarcza Prawna SevArt
    disclaimer: str = MANDATORY_DISCLAIMER

    class Config:
        populate_by_name = True