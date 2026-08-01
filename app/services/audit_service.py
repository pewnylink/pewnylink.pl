import re
from typing import Dict, Any, List

class AuditEngine:
    """
    Silnik analityczny oceny ryzyka transakcyjnego i estymacji TCO dla bezpiecznik.pl
    """

    @staticmethod
    async def analyze_url(url: str, is_unlocked: bool = False, report_id: str = "REP-DEMO-01") -> Dict[str, Any]:
        # 1. Normalizacja i weryfikacja domenowej kategorii
        domain_category = AuditEngine._detect_category(url)
        
        # 2. Symulacja/Pobranie treści (Docelowo integracja ze scraperem)
        # Przykładowe zeskrobane dane z ogłoszenia:
        mock_raw_data = {
            "target_url": url,
            "category": domain_category,
            "price": 2400.0,
            "shipping_cost": 49.0,
            "seller_type": "Osoba Prywatna",
            "rekojmia_excluded": True,
            "has_return_policy": False,
            "invoice_type": None,
            "description": "Sprzedam sprzęt w stanie używanym. Brak możliwości zwrotu, wyłączona rękojmia. Odbiór osobisty lub wysyłka.",
            "images": ["img1.jpg"],
            "location": "Leszno"
        }

        # 3. Analiza Ryzyka i Wykrywanie Haczyków
        legal_flags = []
        risk_score = 30  # Baza: 30/100
        missing_count = 0
        tco_extra = 0.0

        desc_lower = mock_raw_data["description"].lower()

        # Weryfikacja rękojmi
        if mock_raw_data.get("rekojmia_excluded") or "wyłącz" in desc_lower:
            legal_flags.append({
                "title": "⚠️ Próba ograniczenia rękojmi konsumenckiej",
                "description": "Ogłoszenie sugeruje brak odpowiedzialności sprzedawcy za wady ukryte."
            })
            risk_score += 25

        # Weryfikacja prawa do zwrotu
        if not mock_raw_data.get("has_return_policy", True) or "brak możliwości zwrotu" in desc_lower:
            legal_flags.append({
                "title": "⚠️ Wyłączenie prawa do odstąpienia od umowy",
                "description": "Brak jasnej informacji o możliwości zwrotu towaru w ciągu 14 dni."
            })
            risk_score += 20

        # Sprawdzanie kompletności ogłoszenia
        required_fields = ["description", "images", "shipping_cost", "invoice_type", "location"]
        for f in required_fields:
            if not mock_raw_data.get(f):
                missing_count += 1
                risk_score += 8

        # 4. Kalkulator TCO (Całkowitego Kosztu Posiadania)
        shipping_cost = float(mock_raw_data.get("shipping_cost", 0.0) or 0.0)
        item_price = float(mock_raw_data.get("price", 0.0) or 0.0)
        is_company = mock_raw_data.get("seller_type") == "Firma"

        tco_items = [
            {"category": "Dostawa i Bezpieczne Pakowanie", "details": "Szacowany koszt wysyłki gabarytowej / ubezpieczonej", "amount": shipping_cost}
        ]

        # Podatek PCC-3 (2%) przy zakupie od osoby prywatnej powyżej 1000 PLN
        if not is_company and item_price > 1000.0:
            pcc_tax = round(item_price * 0.02, 2)
            tco_items.append({
                "category": "Podatek PCC-3 (2%)",
                "details": "Obowiązek podatkowy kupującego przy transakcji z osobą prywatną > 1000 PLN",
                "amount": pcc_tax
            })

        total_tco = sum(item["amount"] for item in tco_items)

        # 5. Określenie etykiety poziomu ryzyka
        final_risk_score = min(100, max(0, risk_score))
        if final_risk_score >= 70:
            risk_level = "WYSOKIE"
        elif final_risk_score >= 40:
            risk_level = "ŚREDNIE"
        else:
            risk_level = "NISKIE"

        # Wyliczenie sugerowanej obniżki (potencjał negocjacyjny)
        discount_percentage = 0.05 + (len(legal_flags) * 0.03) + (missing_count * 0.01)
        suggested_discount = round(item_price * min(discount_percentage, 0.20), 2)
        completeness = max(0, 100 - (missing_count * 15))

        # 6. Darmowa sekcja kafelków diagnostycznych
        free_points = [
            {
                "title": "1. Weryfikacja prawa do 14-dniowego zwrotu",
                "status": "RYZYKO" if not mock_raw_data.get("has_return_policy", True) else "OK",
                "desc": "Sprzedawca w opisie ogranicza prawo do zwrotu towaru." if not mock_raw_data.get("has_return_policy", True) else "Prawo do odstąpienia od umowy jest zachowane.",
                "is_ok": mock_raw_data.get("has_return_policy", True)
            },
            {
                "title": "2. Analiza zapisu o rękojmi konsumenckiej",
                "status": "UWAGA" if mock_raw_data.get("rekojmia_excluded") else "OK",
                "desc": "Wykryto próbę wyłączenia lub ograniczenia rękojmi." if not mock_raw_data.get("rekojmia_excluded") else "Standardowa rękojmia prawna obowiązuje.",
                "is_ok": not mock_raw_data.get("rekojmia_excluded")
            },
            {
                "title": "3. Sprawdzenie typu dokumentu zakupu",
                "status": "OK" if mock_raw_data.get("invoice_type") else "UWAGA",
                "desc": f"Zadeklarowany dokument: {mock_raw_data.get('invoice_type', 'Brak szczegółów (moliwy brak FV)')}",
                "is_ok": bool(mock_raw_data.get("invoice_type"))
            },
            {
                "title": "4. Estymacja dodatkowych opłat i transportu",
                "status": "INFO",
                "desc": f"Szacowane opłaty dodatkowe (wysyłka, podatek PCC-3): +{total_tco} PLN",
                "is_ok": True
            },
            {
                "title": "5. Sprawdzenie statusu profilu sprzedającego",
                "status": "OK",
                "desc": f"Typ konta: {mock_raw_data.get('seller_type', 'Osoba prywatna')}. Brak negatywnych wpisów w publicznych rejestrach.",
                "is_ok": True
            }
        ]

        # 7. Wygenerowanie 3 Dedykowanych Pytań do Sprzedawcy
        questions = [
            {
                "id": 1,
                "title": "Pytanie 1: O rękojmię i odpowiedzialność za wady",
                "text": "Dzień dobry, czy w przypadku wykrycia wad ukrytych po zakupie obowiązuje pełna 24-miesięczna rękojmia bez wyłączeń?"
            },
            {
                "id": 2,
                "title": "Pytanie 2: O dokument sprzedaży i podatek",
                "text": "Czy do przedmiotu wystawiają Państwo fakturę VAT 23%, czy sprzedaż odbywa się jako osoba prywatna (umowa K-S)?"
            },
            {
                "id": 3,
                "title": "Pytanie 3: O kompletność zestawu i historię",
                "text": "Czy przedmiot posiada wszystkie oryginalne akcesoria oraz fabryczne opakowanie i dowód zakupu z pierwszej ręki?"
            }
        ]

        # Skrypt negocjacyjny
        negotiation_script = (
            f"Dzień dobry, jestem zainteresowany zakupem oferty z linku ({url}). "
            f"Z uwagi na wykryte braki w opisie oraz wyliczone koszty dodatkowe, proponuję cenę o {suggested_discount} PLN niższą. "
            f"W przypadku akceptacji jestem gotowy sfinalizować zakup od ręki."
        )

        return {
            "report_id": report_id,
            "target_url": url,
            "category": domain_category,
            "created_at": "01.08.2026",
            "risk_score": final_risk_score,
            "risk_level": risk_level,
            "legal_flags": legal_flags,
            "tco_items": tco_items,
            "total_tco_extra": total_tco,
            "completeness_score": f"{completeness}%",
            "missing_fields_count": missing_count,
            "seller_type": mock_raw_data.get("seller_type", "Osoba Prywatna"),
            "rekojmia_status": "Wyłączona" if mock_raw_data.get("rekojmia_excluded") else "Obowiązuje",
            "history_status": "Czysty profil",
            "is_unlocked": is_unlocked,
            "free_points": free_points,
            "suggested_discount": f"{suggested_discount} PLN",
            "negotiation_script": negotiation_script,
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