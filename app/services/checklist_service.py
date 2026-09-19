import json
from pathlib import Path
from fastapi import HTTPException

# Ścieżka do katalogu z checklistami
CHECKLISTS_DIR = Path("config/checklists")

def load_checklist_by_industry(industry_id: str) -> dict:
    """
    Wczytuje odpowiedni plik JSON z folderu config/checklists/
    na podstawie industry_id.
    """
    file_path = CHECKLISTS_DIR / f"{industry_id}.json"
    
    if not file_path.is_file():
        raise HTTPException(
            status_code=404, 
            detail=f"Nie znaleziono konfiguracji dla branży: {industry_id}"
        )
            
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)