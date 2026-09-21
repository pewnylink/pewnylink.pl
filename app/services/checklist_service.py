import json
from pathlib import Path
from typing import Dict, List, Optional
from fastapi import HTTPException

# Bezpieczne wyznaczenie ścieżki głównej projektu (root)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CHECKLISTS_DIR = BASE_DIR / "config" / "checklists"

# Mapowanie skróconych/legacy identyfikatorów na nazwy plików w config/checklists/
INDUSTRY_ALIASES: Dict[str, str] = {
    "maszyny_rolnicze_i_budowlane": "sprzet_i_maszyny_rolnicze_oraz_budowlane",
    "heavy_machinery": "sprzet_i_maszyny_rolnicze_oraz_budowlane",
    "elektronika": "elektronika_uzytkowa_i_sprzet_IT",
    "medycyna": "sprzet_i_urzadzenia_medyczne",
}


def _normalize_checklist_data(industry_id: str, raw_data: dict) -> dict:
    """
    Gwarantuje jednolitą strukturę słownika niezależnie od ewentualnego zagnieżdżenia w pliku JSON.
    """
    # Obsługa przypadku zagnieżdżenia pod kluczem branży
    if industry_id in raw_data and isinstance(raw_data[industry_id], dict):
        content = raw_data[industry_id]
        if "freemium_checkpoints" in raw_data and "freemium_checkpoints" not in content:
            content["freemium_checkpoints"] = raw_data["freemium_checkpoints"]
        data = content
    else:
        data = raw_data

    # Gwarancja spójności pól identyfikacyjnych
    if "id" not in data:
        data["id"] = industry_id
    if "name" not in data:
        data["name"] = data.get("title") or data.get("industry_name") or industry_id

    return data


def load_checklist_by_industry(industry_id: str) -> dict:
    """
    Wczytuje i normalizuje odpowiedni plik JSON z folderu config/checklists/
    na podstawie industry_id (z uwzględnieniem aliasów).
    """
    target_id = INDUSTRY_ALIASES.get(industry_id, industry_id)
    file_path = CHECKLISTS_DIR / f"{target_id}.json"

    if not file_path.is_file():
        available = [item["id"] for item in get_all_available_industries()]
        raise HTTPException(
            status_code=404, 
            detail=(
                f"Nie znaleziono konfiguracji dla branży: '{industry_id}'. "
                f"Dostępne branże w systemie: {available}"
            )
        )

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        return _normalize_checklist_data(target_id, raw_data)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Błąd składniowy w pliku JSON dla branży '{target_id}': {e}"
        )


def get_all_available_industries() -> List[Dict[str, str]]:
    """
    Skanuje katalog config/checklists/ i zwraca listę wszystkich dostępnych branż.
    Używane dynamicznie przez klasyfikator AI (LLM) oraz endpointy API.
    """
    if not CHECKLISTS_DIR.exists():
        return []

    industries = []
    for file_path in CHECKLISTS_DIR.glob("*.json"):
        industry_id = file_path.stem
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            normalized = _normalize_checklist_data(industry_id, raw_data)
            industries.append({
                "id": industry_id,
                "name": normalized.get("name", industry_id)
            })
        except Exception:
            industries.append({
                "id": industry_id,
                "name": industry_id
            })

    return industries