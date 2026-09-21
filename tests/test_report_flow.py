import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.checklist_service import load_checklist_by_industry
from app.core.affiliates import get_affiliate_widgets

CHECKLISTS_DIR = BASE_DIR / "config" / "checklists"

def test_single_industry(industry_id: str):
    print(f"\n==================================================")
    print(f"🔍 Rozpoczynam diagnostykę dla branży: '{industry_id}'...")
    print(f"==================================================")

    # 1. Wczytanie pliku JSON
    try:
        checklist = load_checklist_by_industry(industry_id)
        print("✅ [1/4] Plik JSON wczytany z sukcesem.")
        print(f"   • Dostępne klucze główne: {list(checklist.keys())}")
    except Exception as e:
        print(f"❌ [1/4] Błąd wczytywania JSON: {e}")
        return False

    # 2. Nazwa branży
    industry_name = (
        checklist.get("name") 
        or checklist.get("title") 
        or checklist.get("industry_name") 
        or checklist.get("industry")
    )
    print(f"\n🏷️ [2/4] Nazwa branży: {industry_name}")

    # 3. Zliczanie punktów (wsparcie dla nowej i legacy struktury)
    # 3a. Punkty darmowe
    free_checkpoints = checklist.get("freemium_checkpoints")
    if free_checkpoints is not None and isinstance(free_checkpoints, list):
        free_points = len(free_checkpoints)
    else:
        free_summary = checklist.get("public_free_summary", {})
        free_points = len(free_summary.get("points", [])) if isinstance(free_summary, dict) else 0

    # 3b. Kategorie i punkty płatne
    categories = checklist.get("categories")
    if categories is None:
        paid_analysis = checklist.get("paid_detailed_analysis", {})
        categories = paid_analysis.get("categories", []) if isinstance(paid_analysis, dict) else []

    paid_points = 0
    for cat in categories:
        if isinstance(cat, dict):
            # Nowa struktura: 'checkpoints', legacy: 'points'
            checkpoints = cat.get("checkpoints") or cat.get("points") or []
            paid_points += len(checkpoints)

    print("\n📊 [3/4] Podsumowanie punktów:")
    print(f"   • Punkty darmowe (Freemium): {free_points}")
    print(f"   • Liczba kategorii: {len(categories)}")
    print(f"   • Punkty płatne (Checkpoints): {paid_points}")

    # 4. Weryfikacja modułów planu działań AI
    action_plan = checklist.get("paid_post_analysis_modules") or checklist.get("ai_generated_action_plan", {})
    
    if isinstance(action_plan, dict):
        # W nowej strukturze moduły są słownikiem (questions_to_seller, estimated_initial_costs, negotiation_strategy)
        # W legacy były listą pod kluczem "modules"
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
    for mod in modules_list:
        if isinstance(mod, dict):
            print(f"     - {mod.get('title') or mod.get('name')}")

    # 5. Test pobierania afiliacji
    print("\n🔗 [4/4] Test pobierania afiliacji:")
    try:
        affiliates = get_affiliate_widgets(industry_id, placement="report")
        print(f"   • Znalezione oferty dla placement='report': {len(affiliates)}")
        for aff in affiliates:
            print(f"     - {aff}")
    except TypeError:
        try:
            affiliates = get_affiliate_widgets(placement="report", industry_id=industry_id)
            print(f"   • Znalezione oferty (odwrotna kolejność): {len(affiliates)}")
        except Exception as err:
            print(f"   ⚠️ Błąd wywołania afiliacji: {err}")
    except Exception as e:
        print(f"   ⚠️ Błąd podczas pobierania afiliacji: {e}")

    return True


def run_test(target_industry_id: str = None):
    if target_industry_id:
        test_single_industry(target_industry_id)
    else:
        # Automatycznie testuje wszystkie pliki .json w katalogu config/checklists/
        json_files = list(CHECKLISTS_DIR.glob("*.json"))
        if not json_files:
            print(f"❌ Nie znaleziono żadnych plików .json w {CHECKLISTS_DIR}")
            return

        print(f"🚀 Wyryto {len(json_files)} checklist branżowych w {CHECKLISTS_DIR}. Rozpoczynam testy masowe...\n")
        
        success_count = 0
        for file_path in json_files:
            industry_id = file_path.stem
            if test_single_industry(industry_id):
                success_count += 1
        
        print(f"\n==================================================")
        print(f"🎉 Zakończono testy! Sukces: {success_count}/{len(json_files)} branż.")
        print(f"==================================================")

if __name__ == "__main__":
    # Możesz podać konkretne ID jako argument, np. run_test("sprzet_i_maszyny_rolnicze_oraz_budowlane")
    # Zostawiając None testujesz wszystkie pliki z katalogu config/checklists/
    run_test()