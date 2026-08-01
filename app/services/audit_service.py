import re
from typing import Dict, Any

class AuditEngine:
    """
    Silnik analityczny oceny ryzyka transakcyjnego i estymacji TCO dla pewnylink.pl
    """

    @staticmethod
    async def analyze_url(url: str) -> Dict[Any, Any]:
        # 1. Normalizacja i weryfikacja domenowej kategorii
        domain_category = AuditEngine._detect_category(url)
        
        # 2. Symulacja/Pobranie treści (Docelowo integracja ze scraperem)
        # Na potrzeby demonstracji analizujemy pod kątem fraz kluczowych:
        mock_raw_text = "Sprzedam samochód/sprzęt w stanie używanym. Brak możliwości zwrotu, wyłączona rękojmia. Odbiór osobisty lub wysyłka kurierem na koszt kupującego."
        
        # 3. Analiza Ryzyka i Wykrywanie Haczyków
        legal_flags = []
        risk_score = 30 # Baza: 30/100 (Niskie ryzyko)

        if "wyłącz" in mock_raw_text.lower() or "stan" in mock_raw_text.lower():
            legal_flags.append({
                "title": "⚠️ Próba ograniczenia rękojmi konsumenckiej",
                "description": "Ogłoszenie sugeruje brak odpowiedzialności sprzedawcy. W zakupie konsumpcyjnym taki zapis jest bezskuteczny prawnie."
            })
            risk_score += 25

        if "brak możliwości zwrotu" in mock_raw_text.lower():
            legal_flags.append({
                "title": "⚠️ Wyłączenie prawa do odstąpienia od umowy",
                "description": "Przy zakupie na odległość od firmy masz ustawowe 14 dni na zwrot bez podawania przyczyny."
            })
            risk_score += 20

        # 4. Kalkulator TCO (Całkowitego Kosztu Posiadania)
        tco_items = [
            {"category": "Dostawa i Bezpieczne Pakowanie", "details": "Szacowany koszt wysyłki gabarytowej / ubezpieczonej", "amount": 49.00},
            {"category": "Weryfikacja Stanu Technicznego", "details": "Podstawowy przegląd / diagnostyka powdrożeniowa", "amount": 150.00}
        ]
        
        total_tco = sum(item["amount"] for item in tco_items)

        # 5. Wygenerowanie 3 Dedykowanych Pytań do Sprzedawcy
        questions = [
            {
                "id": 1,
                "title": "Pytanie 1: Pełna dokumentacja i rękojmia",
                "text": "Czy na zakupiony przedmiot wystawiają Państwo pełną fakturę VAT 23% / paragon oraz czy obowiązuje 24-miesięczna rękojmia dla konsumenta?"
            },
            {
                "id": 2,
                "title": "Pytanie 2: Stan fizyczny i kompletność zestawu",
                "text": "Czy oferta zawiera wszystkie fabryczne akcesoria niezbędne do uruchomienia, czy występują ukryte opłaty za aktywację/osprzęt?"
            },
            {
                "id": 3,
                "title": "Pytanie 3: Zwrot i warunki dostawy",
                "text": "Jaki jest dokładny adres i procedura zgłoszenia zwrotu w ciągu 14 dni w przypadku zakupu na odległość?"
            }
        ]

        # Określenie etykiety poziomu ryzyka
        risk_level = "NISKIE"
        if risk_score >= 70:
            risk_level = "WYSOKIE"
        elif risk_score >= 40:
            risk_level = "ŚREDNIE"

        return {
            "target_url": url,
            "category": domain_category,
            "risk_score": min(risk_score, 100),
            "risk_level": risk_level,
            "legal_flags": legal_flags,
            "tco_items": tco_items,
            "total_tco_extra": total_tco,
            "questions": questions
        }

    @staticmethod
    def _detect_category(url: str) -> str:
        url_lower = url.lower()
        if "otomoto" in url_lower or "auto" in url_lower:
            return "Motoryzacja"
        elif "olx" in url_lower or "allegro" in url_lower:
            return "Elektronika / Drobne Ogłoszenia"
        elif "otodom" in url_lower or "nieruchomosci" in url_lower:
            return "Nieruchomości"
        return "Sklep Internetowy / Inne"