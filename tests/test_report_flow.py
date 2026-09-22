import sys
from pathlib import Path
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.checklist_service import load_checklist_by_industry
from app.core.affiliates import get_affiliate_widgets

CHECKLISTS_DIR = BASE_DIR / "config" / "checklists"


def get_all_industry_ids():
    """Pobiera listę nazw branż na podstawie plików JSON w katalogu checklists."""
    if not CHECKLISTS_DIR.exists():
        return []
    return [f.stem for f in CHECKLISTS_DIR.glob("*.json")]


# Pobieramy listę branż do parametryzacji testu
INDUSTRY_IDS = get_all_industry_ids()


@pytest.mark.parametrize("industry_id", INDUSTRY_IDS if INDUSTRY_IDS else ["default"])
def test_single_industry(industry_id: str):
    print(f"\n==================================================")
    print(f"🔍 Rozpoczynam diagnostykę dla branży: '{industry_id}'...")
    print(f"==================================================")

    # 1. Wczytanie pliku JSON
    checklist = load_checklist_by_industry(industry_id)
    assert checklist is not None, f"Nie udało się wczytać checklisty dla branży {industry_id}"
    print("✅ [1/4] Plik JSON wczytany z sukcesem.")
    print(f"   • Dostępne klucze główne: {list(checklist.keys())}")

    # 2. Nazwa branży
    industry_name = (
        checklist.get("name") 
        or checklist.get("title") 
        or checklist.get("industry_name") 
        or checklist.get("industry")
    )
    print(f"\n🏷️ [2/4] Nazwa branży: {industry_name}")

    # 3. Zliczanie punktów
    free_checkpoints = checklist.get("freemium_checkpoints")
    if free_checkpoints is not None and isinstance(free_checkpoints, list):
        free_points = len(free_checkpoints)
    else:
        free_summary = checklist.get("public_free_summary", {})
        free_points = len(free_summary.get("points", [])) if isinstance(free_summary, dict) else 0

    categories = checklist.get("categories")
    if categories is None:
        paid_analysis = checklist.get("paid_detailed_analysis", {})
        categories = paid_analysis.get("categories", []) if isinstance(paid_analysis, dict) else []

    paid_points = 0
    for cat in categories:
        if isinstance(cat, dict):
            checkpoints = cat.get("checkpoints") or cat.get("points") or []
            paid_points += len(checkpoints)

    print("\n📊 [3/4] Podsumowanie punktów:")
    print(f"   • Punkty darmowe (Freemium): {free_points}")
    print(f"   • Liczba kategorii: {len(categories)}")
    print(f"   • Punkty płatne (Checkpoints): {paid_points}")

    # 4. Weryfikacja modułów planu działań AI
    action_plan = checklist.get("paid_post_analysis_modules") or checklist.get("ai_generated_action_plan", {})
    
    if isinstance(action_plan, dict):
        if "modules" in action_plan and isinstance(action_plan["modules"], list):
            modules_list = action_plan["modules"]
        else:
            modules_list = list(action_plan.values())
        
        section_title = action_plan.get("section_title", "Plan działań AI / Moduły płatne")
    else:
        modules_list = []
        section_title = "None"

    print("\n💡 [3/4] Weryfikacja planu działań AI:")
    print(f"   • Sekcja: {section_title}")
    print(f"   • Liczba modułów: {len(modules_list)}/3 {'✅' if len(modules_list) >= 3 else '⚠️'}")

    # 5. Test pobierania afiliacji
    print("\n🔗 [4/4] Test pobierania afiliacji:")
    try:
        affiliates = get_affiliate_widgets(industry_id, placement="report")
        print(f"   • Znalezione oferty dla placement='report': {len(affiliates)}")
    except TypeError:
        try:
            affiliates = get_affiliate_widgets(placement="report", industry_id=industry_id)
            print(f"   • Znalezione oferty (odwrotna kolejność): {len(affiliates)}")
        except Exception as err:
            print(f"   ⚠️ Błąd wywołania afiliacji: {err}")
    except Exception as e:
        print(f"   ⚠️ Błąd podczas pobierania afiliacji: {e}")


if __name__ == "__main__":
    for ind_id in INDUSTRY_IDS:
        test_single_industry(ind_id)