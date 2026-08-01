import os
import json
import re
from datetime import datetime, timezone
from app.database import reports_collection
from app.services.audit_service import AuditEngine

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "config", "checklists.json")

def load_checklist_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"universal_free_points": [], "industries": {}}

def anonymize_text(text: str) -> str:
    text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[UKRYTO E-MAIL]', text)
    text = re.sub(r'(\+?48)?\s*(\d{3}[\s-]?\d{3}[\s-]?\d{3})', '[UKRYTO TELEFON]', text)
    return text

async def generate_audit_report(listing_text: str, target_url: str, industry: str = "general", is_unlocked: bool = False) -> dict:
    config = load_checklist_config()
    clean_text = anonymize_text(listing_text)
    
    # 1. Pobranie danych branżowych z konfiguracji
    industry_info = config.get("industries", {}).get(industry, config.get("industries", {}).get("general", {}))
    industry_name = industry_info.get("name", "Pozostałe / Ogólne")
    premium_items = industry_info.get("premium_points", [])

    # 2. Uruchomienie Silnika Audytowego (AuditEngine)
    audit_results = await AuditEngine.analyze_url(url=target_url, is_unlocked=is_unlocked)

    # 3. Przygotowanie dokumentu raportu z pełnym zestawem danych dla MongoDB oraz szablonu HTML
    report_document = {
        "created_at": datetime.now(timezone.utc),
        "created_at_formatted": datetime.now(timezone.utc).strftime("%d.%m.%Y"),
        "industry": industry_name,
        "industry_key": industry,
        "target_url": target_url,
        "listing_text": clean_text,
        "is_paid": is_unlocked,
        "is_unlocked": is_unlocked,
        
        # Metryki wyliczone przez AuditEngine
        "risk_score": audit_results.get("risk_score", 30),
        "risk_level": audit_results.get("risk_level", "NISKIE"),
        "legal_flags": audit_results.get("legal_flags", []),
        "tco_items": audit_results.get("tco_items", []),
        "total_tco_extra": audit_results.get("total_tco_extra", 0.0),
        "completeness_score": audit_results.get("completeness_score", "100%"),
        "missing_fields_count": audit_results.get("missing_fields_count", 0),
        
        # Dane widokowe dla szablonu report_view.html
        "free_points": audit_results.get("free_points", []),
        "questions": audit_results.get("questions", []),
        "suggested_discount": audit_results.get("suggested_discount", "0 PLN"),
        "negotiation_script": audit_results.get("negotiation_script", ""),
        "premium_items": premium_items,
        
        # Informacje o sprzedawcy / transakcji
        "seller_type": audit_results.get("seller_type", "Osoba Prywatna"),
        "rekojmia_status": audit_results.get("rekojmia_status", "Obowiązuje"),
        "history_status": "Czysty profil"
    }

    # 4. Zapis dokumentu w MongoDB
    result = reports_collection.insert_one(report_document)
    
    # 5. Przypisanie bezpiecznych identyfikatorów tekstowych (konwersja ObjectId)
    generated_id = str(result.inserted_id)
    report_document["id"] = generated_id
    report_document["_id"] = generated_id  # Nadpisujemy surowy ObjectId ciągiem znaków dla bezpieczeństwa Jinja2
    report_document["report_id"] = audit_results.get("report_id", f"REP-{generated_id[-6:].upper()}")

    return report_document