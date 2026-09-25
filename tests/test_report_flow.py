# tests/test_report_flow.py
from pathlib import Path
import pytest

from app.services.checklist_service import load_checklist_by_industry
from app.core.affiliates import get_affiliate_widgets

BASE_DIR = Path(__file__).resolve().parent.parent
CHECKLISTS_DIR = BASE_DIR / "config" / "checklists"


def get_all_industry_ids() -> list[str]:
    """Pobiera listę nazw branż na podstawie plików JSON w katalogu checklists."""
    if not CHECKLISTS_DIR.exists():
        return []
    return [f.stem for f in CHECKLISTS_DIR.glob("*.json")]


INDUSTRY_IDS = get_all_industry_ids()


@pytest.mark.parametrize("industry_id", INDUSTRY_IDS if INDUSTRY_IDS else ["default"])
def test_single_industry_checklist_and_affiliates(industry_id: str):
    """
    Weryfikuje poprawność struktury checklisty JSON oraz ładowania widgetów afiliacyjnych dla danej branży.
    """
    # 1. Wczytanie pliku JSON
    checklist = load_checklist_by_industry(industry_id)
    assert checklist is not None, f"Nie udało się wczytać checklisty dla branży '{industry_id}'"

    # 2. Nazwa branży
    industry_name = (
        checklist.get("name") 
        or checklist.get("title") 
        or checklist.get("industry_name") 
        or checklist.get("industry")
    )
    assert industry_name is not None, f"Checklista '{industry_id}' nie posiada zdefiniowanej nazwy/tytułu"

    # 3. Zliczanie punktów
    free_checkpoints = checklist.get("freemium_checkpoints")
    if free_checkpoints is not None and isinstance(free_checkpoints, list):
        free_points = len(free_checkpoints)
    else:
        free_summary = checklist.get("public_free_summary", {})
        free_points = len(free_summary.get("points", [])) if isinstance(free_summary, dict) else 0

    assert free_points >= 0, "Liczba punktów darmowych nie może być ujemna"

    categories = checklist.get("categories")
    if categories is None:
        paid_analysis = checklist.get("paid_detailed_analysis", {})
        categories = paid_analysis.get("categories", []) if isinstance(paid_analysis, dict) else []

    paid_points = sum(
        len(cat.get("checkpoints") or cat.get("points") or [])
        for cat in categories
        if isinstance(cat, dict)
    )

    # 4. Weryfikacja modułów planu działań AI
    action_plan = checklist.get("paid_post_analysis_modules") or checklist.get("ai_generated_action_plan", {})
    
    if isinstance(action_plan, dict):
        if "modules" in action_plan and isinstance(action_plan["modules"], list):
            modules_list = action_plan["modules"]
        else:
            modules_list = list(action_plan.values())
    else:
        modules_list = []

    # Asercja biznesowa: Każda branża powinna mieć min. 3 moduły w planie działań
    assert len(modules_list) >= 3, (
        f"Branża '{industry_id}' posiada tylko {len(modules_list)} modułów w planie działań (wymagane min. 3)."
    )

    # 5. Test pobierania afiliacji (bez połykania błędów)
    affiliates = get_affiliate_widgets(industry_id=industry_id, placement="report")
    assert isinstance(affiliates, list), f"Pobieranie afiliacji dla '{industry_id}' powinno zwracać listę"