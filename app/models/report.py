# app/models/report.py
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl
from app.legal.legal_shield import MANDATORY_DISCLAIMER


class ChecklistPoint(BaseModel):
    """Pojedynczy punkt z 30 punktów eksperckich w danej branży."""
    id: int = Field(..., description="Numer punktu od 1 do 30")
    title: str = Field(..., description="Tytuł / Treść weryfikowanego kryterium")
    status: str = Field(default="UNKNOWN", description="OK | WARNING | CRITICAL | UNKNOWN")
    findings: Optional[str] = Field(default=None, description="Wniosek/Analityka z opisu lub danych")
    risk_level: str = Field(default="LOW", description="LOW | MEDIUM | HIGH")


class FreemiumPreview(BaseModel):
    """Warstwa darmowa – 5 uniwersalnych punktów próbki dla każdego linku."""
    checkpoints: List[ChecklistPoint] = Field(..., min_length=5, max_length=5)
    overall_score: float = Field(..., description="Ocena bezpieczeństwa 0-100")
    risk_summary: str = Field(..., description="Krótkie podsumowanie wykrytego ryzyka")


# --- CZĘŚĆ I: Cyfrowy Ślad i Metadane ---
class DigitalFootprint(BaseModel):
    listing_id: str
    first_seen_timestamp: datetime
    active_days_on_market: int
    seller_account_age_days: Optional[int] = None
    seller_rating_avg: Optional[float] = None
    multi_account_score: float = Field(default=0.0, description="0-100% ryzyka duplikatów")
    nlp_manipulation_score: float = Field(default=0.0, description="Wskaźnik presji psychologicznej / użycia translatora")
    risk_phrases_detected: List[str] = []
    cross_portal_duplicates: List[str] = []


# --- CZĘŚĆ II: Analiza Finansowa ---
class FinancialAnalysis(BaseModel):
    price_deviation_index_pdi: float = Field(..., description="Wskaźnik odchylenia od średniej rynkowej (np. -15.5%)")
    market_average_price: float = Field(default=0.0, description="Średnia cena rynkowa dla danej klasy/rocznika")
    tax_form: str = Field(default="NIEZNANY", description="FV 23% | VAT-Marża | Umowa K-S")
    estimated_additional_costs: float = Field(default=0.0, description="Szacowane opłaty początkowe/startowe PLN")


# --- CZĘŚĆ III: Asystent Negocjacyjny i Decyzyjny (Płatny) ---
class NegotiationAssistant(BaseModel):
    suggested_opening_price: float = Field(..., description="Sugerowana kwota otwarcia negocjacji PLN")
    original_price: float = Field(..., description="Cena z ogłoszenia PLN")
    justification_arguments: List[str] = Field(..., description="Twarde argumenty do negocjacji ze sprzedawcą")
    questions_to_seller: List[str] = Field(..., min_length=3, max_length=3, description="3 precyzyjne pytania do ogłoszeniodawcy")


# --- GŁÓWNY MODEL RAPORTU SAAS ---
class PewnyLinkReport(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    source_url: str
    title_raw: str
    deep_link: str
    category: str = Field(
        ..., 
        description="heavy_machinery | medical_devices | automotive | real_estate | bicycles | general"
    )
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    algorithm_version: str = "PewnyLink AI v2.0-SevArt"
    
    # Status Płatności i Dostęp
    is_paid: bool = Field(default=False, description="True odblokowuje 30 punktów eksperckich i sekcję negocjacji")
    
    # 1. Warstwa Darmowa (Freemium - 5 Punktów)
    freemium_preview: FreemiumPreview
    
    # 2. Metadane i Analiza Cenowa
    digital_footprint: DigitalFootprint
    financial_analysis: FinancialAnalysis
    
    # 3. Warstwa Płatna – Dedykowany Zestaw 30 Punktów Branżowych
    expert_checkpoints: List[ChecklistPoint] = Field(
        default=[], 
        description="Dedykowane 30 punktów wygenerowanych na podstawie branży z checklists.json"
    )
    
    # 4. Warstwa Płatna – Asystent Negocjacji
    negotiation_assistant: Optional[NegotiationAssistant] = None
    
    # Tarcza Prawna SevArt
    disclaimer: str = MANDATORY_DISCLAIMER

    class Config:
        populate_by_name = True