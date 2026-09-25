# app/services/classifier_service.py
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Przykładowa funkcja klasyfikująca (AI lub na podstawie słów kluczowych/kategorii)
async def detect_industry(title: str, description: str, category_hint: Optional[str] = None) -> str:
    """
    Wykrywa branżę na podstawie tytułu, opisu i opcjonalnej podpowiedzi z kategorii.
    Zwraca klucz branży dopasowany do list kontrolnych (checklists).
    """
    # 1. Sprawdzenie reguł słów kluczowych / kategorii źródłowej (szybka ścieżka)
    text = f"{title} {category_hint or ''}".lower()
    
    if any(k in text for k in ["ciągnik", "koparka", "traktor", "kombajn", "siewnik"]):
        return "maszyny_i_urzadzenia_rolnicze_oraz_budowlane"
    if any(k in text for k in ["usg", "rentgen", "fotel stomatologiczny", "kardiomonitor"]):
        return "sprzet_i_urzadzenia_medyczne"
    if any(k in text for k in ["laptop", "iphone", "macbook", "rtx", "komputer"]):
        return "elektronika_uzytkowa_i_sprzet_IT"
    if any(k in text for k in ["rower", "mtb", "gravel", "shimano", "e-bike"]):
        return "rowery"
    if any(k in text for k in ["mieszkanie", "działka", "lokal", "dom", "hale"]):
        return "nieruchomosci"
    if any(k in text for k in ["samochód", "auto", "audi", "bmw", "motocykl", "felgi"]):
        return "motoryzacja"

    # 2. Jeśli reguły nie wykryły jednoznacznie -> wywołanie AI (np. OpenAI/Gemini)
    # Tu wstawiasz zapytanie do modelu AI z dokładnym promptem
    return "elektronika_uzytkowa_i_sprzet_IT" # domyślna / uzyskana z AI