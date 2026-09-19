from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, HttpUrl

# Importujemy funkcję wczytującą z osobnego serwisu
from app.services.checklist_service import load_checklist_by_industry

# Instancja routera podłączana w main.py
router = APIRouter(prefix="/reports", tags=["Raporty i Analiza"])


class AnalyzeLinkRequest(BaseModel):
    url: str
    industry_id: Optional[str] = None  # Opcjonalne manualne nadpisanie branży


@router.get("/checklists/{industry_id}", summary="Pobierz checklistę dla branży")
async def get_checklist(industry_id: str):
    """
    Zwraca surowy plik JSON z punktami analizy dla podanego `industry_id`.
    """
    return load_checklist_by_industry(industry_id)


@router.post("/analyze", summary="Przeanalizuj link ogłoszenia")
async def analyze_report(payload: AnalyzeLinkRequest):
    """
    Główny endpoint do generowania raportu na podstawie linku.
    Odbiera URL, wykrywa branżę i wczytuje właściwą checklistę JSON.
    """
    # 1. Określenie identyfikatora branży (docelowo z automatycznej detekcji URL)
    detected_industry = payload.industry_id or "maszyny_rolnicze_i_budowlane"

    # 2. Wczytanie checklisty z pliku JSON za pomocą serwisu
    checklist_data = load_checklist_by_industry(detected_industry)

    # 3. Przygotowanie odpowiedzi z danymi z checklisty
    return {
        "status": "success",
        "url": payload.url,
        "industry_id": detected_industry,
        "industry_name": checklist_data.get("industry_name"),
        "public_summary": checklist_data.get("public_free_summary"),
        "paid_analysis": checklist_data.get("paid_detailed_analysis"),
        "action_plan_modules": checklist_data.get("ai_generated_action_plan"),
    }