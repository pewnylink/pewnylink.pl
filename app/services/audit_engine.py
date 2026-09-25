from typing import Optional, List, Dict, Any
from app.services.checklist_service import (
    load_checklist_by_industry,
    get_all_available_industries
)
from app.services.audit_service import AuditEngine


async def detect_industry_from_url(url: str, available_industries: List[Dict[str, str]]) -> str:
    """Wykrywa branżę na podstawie słów kluczowych w adresie URL."""
    url_lower = url.lower()
    
    if any(k in url_lower for k in ["maszyny", "rolnicze", "budowlane", "traktor", "koparka", "kombajn"]):
        return "sprzet_i_maszyny_rolnicze_oraz_budowlane"
    if any(k in url_lower for k in ["rower", "rowery", "bike"]):
        return "rowery"
    if any(k in url_lower for k in ["mieszkanie", "dom", "dzialka", "nieruchomosci", "otodom"]):
        return "nieruchomosci"
    if any(k in url_lower for k in ["auto", "samochod", "otomoto", "motoryzacja", "pojazd"]):
        return "motoryzacja"
    if any(k in url_lower for k in ["laptop", "telefon", "elektronika", "komputer", "it", "allegro", "olx", "vinted"]):
        return "elektronika_uzytkowa_i_sprzet_IT"
    if any(k in url_lower for k in ["medyczny", "uszg", "rentgen", "stomatologiczny"]):
        return "sprzet_i_urzadzenia_medyczne"

    # Fallback do pierwszej dostępnej branży
    if available_industries and isinstance(available_industries[0], dict) and "id" in available_industries[0]:
        return available_industries[0]["id"]
    
    return "sprzet_i_maszyny_rolnicze_oraz_budowlane"


async def process_url_audit(url: str, industry_id: Optional[str] = None) -> Dict[str, Any]:
    """Główna funkcja wyliczająca audyt dla podanego linku."""
    available_industries = get_all_available_industries()

    if industry_id:
        detected_industry = industry_id
    else:
        detected_industry = await detect_industry_from_url(url, available_industries)

    checklist_data = load_checklist_by_industry(detected_industry) or {}
    dynamic_audit = await AuditEngine.analyze_url(url=url)

    industry_name = (
        checklist_data.get("name") 
        or checklist_data.get("title") 
        or checklist_data.get("industry_name")
        or detected_industry.replace("_", " ").title()
    )

    return {
        "status": "success",
        "url": url,
        "industry_id": detected_industry,
        "industry_name": industry_name,
        "audit_analysis": dynamic_audit,
        "total_checkpoints_count": len(dynamic_audit.get("free_points", [])) + len(dynamic_audit.get("extended_points", [])),
        "available_industries": available_industries
    }