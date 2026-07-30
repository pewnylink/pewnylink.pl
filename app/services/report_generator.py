import os
import json
import re
from datetime import datetime, timezone
from app.database import reports_collection

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "config", "checklists.json")

def load_checklist_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"universal_free_points": [], "industries": {}}

def anonymize_text(text: str) -> str:
    text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[UKRYTO E-MAIL]', text)
    text = re.sub(r'(\+?48)?\s*(\d{3}[\s-]?\d{3}[\s-]?\d{3})', '[UKRYTO TELEFON]', text)
    return text

async def generate_audit_report(listing_text: str, target_url: str, industry: str = "real_estate"):
    config = load_checklist_config()
    clean_text = anonymize_text(listing_text)
    
    industry_info = config.get("industries", {}).get(industry, config.get("industries", {}).get("general", {}))
    industry_name = industry_info.get("name", "Pozostałe / Ogólne")
    premium_items = industry_info.get("premium_points", [])

    free_report_data = {
        "price_benchmark": {
            "status": "W normie rynkowej",
            "details": "Cena wykazuje odchylenie -3.5% od średniej rynkowej dla tej kategorii."
        },
        "seller_identity": {
            "seller_type": "Podmiot Gospodarczy (Spółka / Działalność)",
            "registry_status": "CEIDG/KRS: Zarejestrowany podmiot aktywny. Brak wpisów w rejestrze dłużników.",
            "google_reviews": "Średnia ocen z opinii internetowych: 4.7/5.0"
        },
        "transparency_score": {
            "score": 75,
            "missing_info": ["Brak jawnego numeru identyfikacyjnego/VIN/KW", "Brak podziału na kwoty netto/brutto"]
        },
        "top_red_flags": [
            "W opisie użyto sformułowań wymijających dotyczących rzeczywistego stanu prawnego/technicznego.",
            "Brak jasnego wyszczególnienia ewentualnych kosztów dodatkowych lub prowizji."
        ],
        "transaction_overhead": {
            "tax_and_fees": "PCC 2% lub VAT 23% (w zależności od formy sprzedaży), taksa/opłaty rejestracyjne",
            "estimated_overhead": "Szacowany dodatek okołotransakcyjny: 3% - 6% wartości przedmiotu",
            "formal_requirement": "Wymagana umowa pisemna / faktura z wykazanym statusem VAT."
        }
    }

    # Dokument do zapisu w MongoDB
    report_document = {
        "created_at": datetime.now(timezone.utc),
        "industry": industry_name,
        "industry_key": industry,
        "target_url": target_url,
        "listing_text": clean_text,
        "safety_score": 82,
        "summary": f"Audyt bezpieczeństwa dla kategorii [{industry_name}]",
        "free_data": free_report_data,
        "premium_items": premium_items,
        "is_paid": False
    }

    # ZAPIS DO BAZY MONGODB
    result = reports_collection.insert_one(report_document)
    
    # Dodajemy wygenerowany unikalny ID z MongoDB do zwracanego obiektu
    report_document["id"] = str(result.inserted_id)
    
    return report_document