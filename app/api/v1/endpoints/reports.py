from typing import Optional, List, Dict
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.services.checklist_service import (
    load_checklist_by_industry,
    get_all_available_industries
)

router = APIRouter(prefix="/reports", tags=["Raporty i Analiza"])


class AnalyzeLinkRequest(BaseModel):
    url: str
    industry_id: Optional[str] = None  # Opcjonalne manualne nadpisanie branży przez użytkownika


async def detect_industry_from_url(url: str, available_industries: List[Dict[str, str]]) -> str:
    """
    Automatyczna klasyfikacja branży na podstawie adresu URL ogłoszenia.
    Skanuje frazy w adresie URL i dopasowuje je do dostępnych branż z config/checklists/.
    """
    url_lower = url.lower()
    
    # 1. Szybkie dopasowanie po powszechnych słowach kluczowych w linkach
    if any(k in url_lower for k in ["maszyny", "rolnicze", "budowlane", "traktor", "koparka", "kombajn"]):
        return "sprzet_i_maszyny_rolnicze_oraz_budowlane"
    if any(k in url_lower for k in ["rower", "rowery", "bike"]):
        return "rowery"
    if any(k in url_lower for k in ["mieszkanie", "dom", "dzialka", "nieruchomosci", "otodom"]):
        return "nieruchomosci"
    if any(k in url_lower for k in ["auto", "samochod", "otomoto", "motoryzacja", "pojazd"]):
        return "motoryzacja"
    if any(k in url_lower for k in ["laptop", "telefon", "elektronika", "komputer", "it"]):
        return "elektronika_uzytkowa_i_sprzet_IT"
    if any(k in url_lower for k in ["medyczny", "uszg", "rentgen", "stomatologiczny", "aparat"]):
        return "sprzet_i_urzadzenia_medyczne"

    # 2. Domyślny fallback do pierwszej aktywnej branży w systemie
    if available_industries:
        return available_industries[0]["id"]
    
    return "sprzet_i_maszyny_rolnicze_oraz_budowlane"


@router.get("/industries", summary="Pobierz listę dostępnych branż")
async def list_industries():
    """
    Zwraca listę wszystkich branż zarejestrowanych w systemie (skanuje pliki z config/checklists/).
    """
    return {
        "status": "success",
        "industries": get_all_available_industries()
    }


@router.get("/checklists/{industry_id}", summary="Pobierz checklistę dla branży")
async def get_checklist(industry_id: str):
    """
    Zwraca znormalizowany plik JSON z punktami analizy dla podanego `industry_id`.
    """
    return load_checklist_by_industry(industry_id)


@router.post("/analyze", summary="Przeanalizuj link ogłoszenia")
async def analyze_report(payload: AnalyzeLinkRequest):
    """
    Główny endpoint do generowania raportu na podstawie linku.
    Odbiera URL, automatycznie klasyfikuje branżę i ładuje właściwą checklistę JSON.
    """
    available_industries = get_all_available_industries()

    # 1. Użycie branży wybranej przez użytkownika lub automatyczna detekcja z linku
    if payload.industry_id:
        detected_industry = payload.industry_id
    else:
        detected_industry = await detect_industry_from_url(payload.url, available_industries)

    # 2. Wczytanie i normalizacja danych z checklist_service
    checklist_data = load_checklist_by_industry(detected_industry)

    # 3. Ekstrakcja kluczowych sekcji z obsługą nowej i legacy struktury JSON
    industry_name = (
        checklist_data.get("name") 
        or checklist_data.get("title") 
        or checklist_data.get("industry_name")
    )
    
    freemium_checkpoints = (
        checklist_data.get("freemium_checkpoints") 
        or checklist_data.get("public_free_summary")
    )
    
    categories = (
        checklist_data.get("categories") 
        or checklist_data.get("paid_detailed_analysis", {}).get("categories", [])
    )
    
    paid_modules = (
        checklist_data.get("paid_post_analysis_modules") 
        or checklist_data.get("ai_generated_action_plan")
    )

    return {
        "status": "success",
        "url": payload.url,
        "industry_id": detected_industry,
        "industry_name": industry_name,
        "freemium_checkpoints": freemium_checkpoints,
        "categories": categories,
        "paid_modules": paid_modules,
        "available_industries": available_industries
    }