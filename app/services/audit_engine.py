from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.services.checklist_service import (
    load_checklist_by_industry,
    get_all_available_industries
)
from app.services.audit_service import AuditEngine

router = APIRouter(prefix="/reports", tags=["Raporty i Analiza"])


class AnalyzeLinkRequest(BaseModel):
    url: str
    industry_id: Optional[str] = None


async def detect_industry_from_url(url: str, available_industries: List[Dict[str, str]]) -> str:
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

    if available_industries and isinstance(available_industries[0], dict) and "id" in available_industries[0]:
        return available_industries[0]["id"]
    
    return "sprzet_i_maszyny_rolnicze_oraz_budowlane"


@router.get("/industries", summary="Pobierz listę dostępnych branż")
async def list_industries():
    return {
        "status": "success",
        "industries": get_all_available_industries()
    }


@router.get("/checklists/{industry_id}", summary="Pobierz checklistę dla branży")
async def get_checklist(industry_id: str):
    checklist_data = load_checklist_by_industry(industry_id)
    if not checklist_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Nie odnaleziono checklisty dla branży: {industry_id}"
        )
    return checklist_data


@router.post("/analyze", summary="Przeanalizuj link ogłoszenia (5 darmowych + 40 płatnych punktów)")
async def analyze_report(payload: AnalyzeLinkRequest):
    available_industries = get_all_available_industries()

    if payload.industry_id:
        detected_industry = payload.industry_id
    else:
        detected_industry = await detect_industry_from_url(payload.url, available_industries)

    checklist_data = load_checklist_by_industry(detected_industry) or {}
    dynamic_audit = await AuditEngine.analyze_url(url=payload.url)

    industry_name = (
        checklist_data.get("name") 
        or checklist_data.get("title") 
        or checklist_data.get("industry_name")
        or detected_industry.replace("_", " ").title()
    )

    return {
        "status": "success",
        "url": payload.url,
        "industry_id": detected_industry,
        "industry_name": industry_name,
        "audit_analysis": dynamic_audit,
        "total_checkpoints_count": len(dynamic_audit.get("free_points", [])) + len(dynamic_audit.get("extended_points", [])),
        "available_industries": available_industries
    }