import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

from app.config import settings
from app.services.audit_service import AuditEngine


def load_checklist_config() -> dict:
    """Wczytuje reguły i listy kontrolne z config/checklists.json przy użyciu ścieżki z settings."""
    checklist_path: Path = settings.CHECKLISTS_PATH
    if checklist_path.exists():
        with open(checklist_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"freemium_checkpoints": [], "general": {"name": "Analiza Ogólna", "checkpoints": []}}


def anonymize_text(text: str) -> str:
    """Anonimizacja danych wrażliwych w opisie ogłoszenia przed analizą."""
    if not text:
        return ""
    text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[UKRYTO E-MAIL]', text)
    text = re.sub(r'(\+?48)?\s*(\d{3}[\s-]?\d{3}[\s-]?\d{3})', '[UKRYTO TELEFON]', text)
    return text


def _build_checkpoints_list(raw_points: List[str]) -> List[dict]:
    """Przekształca listę tekstowych punktów kontrolnych na obiekty słownika."""
    checkpoints = []
    for idx, point_title in enumerate(raw_points, start=1):
        checkpoints.append({
            "id": idx,
            "title": point_title,
            "status": "UNKNOWN",  # Statusy: OK | WARNING | CRITICAL | UNKNOWN
            "findings": None,
            "risk_level": "LOW"
        })
    return checkpoints


async def generate_audit_report(
    listing_text: str, 
    target_url: str, 
    industry: str = "general", 
    is_unlocked: bool = False
) -> Dict[str, Any]:
    """Generuje kompletny słownik raportu audytowego gotowy do zapisu w repozytorium SQL lub wyświetlenia w HTML."""
    config = load_checklist_config()
    clean_text = anonymize_text(listing_text)
    
    # 1. Pobranie danych branżowych z config/checklists.json
    industry_info = config.get(industry, config.get("general", {}))
    industry_name = industry_info.get("name", "Analiza Ogólna (Asysta Zakupowa)")
    raw_expert_points = industry_info.get("checkpoints", [])
    
    # Budowanie 30 punktów eksperckich dla danej branży
    expert_checkpoints = _build_checkpoints_list(raw_expert_points)

    # Budowanie 5 punktów darmowych z sekcji freemium_checkpoints
    raw_freemium_points = config.get("freemium_checkpoints", [])[:5]
    freemium_checkpoints = _build_checkpoints_list(raw_freemium_points)

    # 2. Uruchomienie Silnika Audytowego (AuditEngine)
    audit_results = await AuditEngine.analyze_url(url=target_url, is_unlocked=is_unlocked)

    # 3. Wyliczenie kwoty i argumentów dla Asystenta Negocjacji
    suggested_discount_val = audit_results.get("suggested_discount_raw", 0.0)
    original_price = audit_results.get("original_price", 0.0)
    suggested_opening_price = max(0.0, original_price - suggested_discount_val)

    default_questions = [
        "Czy posiada Pan/Pani pełną dokumentację serwisową i paszport/historię z przeglądów?",
        "Czy wyraża Pan/Pani zgodę na weryfikację stanu w niezależnym serwisie przed podpisaniem umowy?",
        "Czy na dokumentach zakupu (faktura/umowa) zostanie wpisana pełna kwota transakcji bez wyłączania rękojmi?"
    ]
    questions_to_seller = audit_results.get("questions", default_questions)
    if len(questions_to_seller) < 3:
        questions_to_seller = default_questions

    # 4. Generowanie unikalnego identyfikatora UUID v4 (PostgreSQL STANDARD)
    report_uuid = str(uuid.uuid4())
    short_code = report_uuid.replace("-", "")[:8].upper()

    # 5. Przygotowanie dokumentu raportu
    report_document = {
        "id": report_uuid,
        "report_id": f"REP-{short_code}",
        "created_at": datetime.now(timezone.utc),
        "created_at_formatted": datetime.now(timezone.utc).strftime("%d.%m.%Y"),
        "source_url": target_url,
        "target_url": target_url,
        "title_raw": audit_results.get("title_raw", "Ogłoszenie bez tytułu"),
        "listing_text": clean_text,
        "category": industry,
        "industry_key": industry,
        "industry_name": industry_name,
        "is_paid": is_unlocked,
        "is_unlocked": is_unlocked,
        
        # Warstwa Freemium (5 Punktów)
        "freemium_preview": {
            "checkpoints": freemium_checkpoints,
            "overall_score": audit_results.get("risk_score", 30),
            "risk_summary": audit_results.get("risk_summary", "Wymaga weryfikacji dokumentacji przed zakupem.")
        },
        
        # Metryki i Dane Finansowe
        "digital_footprint": {
            "listing_id": audit_results.get("listing_id", "N/A"),
            "first_seen_timestamp": datetime.now(timezone.utc),
            "active_days_on_market": audit_results.get("active_days_on_market", 1),
            "risk_phrases_detected": audit_results.get("legal_flags", [])
        },
        "financial_analysis": {
            "price_deviation_index_pdi": audit_results.get("price_deviation_index", 0.0),
            "market_average_price": audit_results.get("market_average_price", 0.0),
            "tax_form": audit_results.get("seller_type", "NIEZNANY"),
            "estimated_additional_costs": audit_results.get("total_tco_extra", 0.0)
        },
        
        # Warstwa Płatna (30 Punktów Eksperckich)
        "expert_checkpoints": expert_checkpoints,
        
        # Warstwa Płatna (Asystent Negocjacji)
        "negotiation_assistant": {
            "suggested_opening_price": suggested_opening_price,
            "original_price": original_price,
            "justification_arguments": audit_results.get("tco_items", []),
            "questions_to_seller": questions_to_seller[:3]
        },
        
        # Statusy pomocnicze
        "risk_score": audit_results.get("risk_score", 30),
        "risk_level": audit_results.get("risk_level", "NISKIE"),
        "rekojmia_status": audit_results.get("rekojmia_status", "Obowiązuje")
    }

    return report_document
# Dopisz na końcu app/services/report_generator.py
# app/services/report_generator.py
from typing import Any, List
from app.schemas.report_schema import ReportDeepAnalysis, ReportResponse, ReportSummary


def _to_list(data: Any, key: str = "questions") -> List[str]:
    """Pomocnicza funkcja do bezpiecznego wyciągania listy ciągów tekstowych."""
    if isinstance(data, list):
        return [str(item) for item in data]
    if isinstance(data, dict):
        val = data.get(key, [])
        if isinstance(val, list):
            return [str(item) for item in val]
        if isinstance(val, str):
            return [val]
    return []


def format_report_response(db_report) -> ReportResponse:
    """
    Formatuj rekord z bazy danych do schematu Pydantic.
    Bezpiecznie przetwarza dane niezależnie od tego, czy są słownikiem, czy listą.
    """
    preview = db_report.freemium_preview if isinstance(db_report.freemium_preview, dict) else {}
    checkpoints = db_report.expert_checkpoints
    negotiation = db_report.negotiation_assistant

    summary = ReportSummary(
        score=float(db_report.risk_score) if db_report.risk_score is not None else 5.0,
        risk_level=str(db_report.risk_level) if db_report.risk_level else "MEDIUM",
        market_price_diff_percent=preview.get("market_price_diff_percent"),
        verdict_summary=preview.get(
            "verdict_summary", "Wstępna analiza została ukończona."
        ),
    )

    deep_analysis = None
    if db_report.is_unlocked:
        deep_analysis = ReportDeepAnalysis(
            red_flags=_to_list(preview.get("red_flags", []) if isinstance(preview, dict) else []),
            checklist=_to_list(checkpoints, key="questions"),
            negotiation_tips=_to_list(negotiation, key="arguments"),
        )

    return ReportResponse(
        report_id=db_report.report_id,
        target_url=db_report.target_url,
        is_unlocked=bool(db_report.is_unlocked),
        created_at=db_report.created_at,
        summary=summary,
        deep_analysis=deep_analysis,
    )