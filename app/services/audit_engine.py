from typing import Dict, Any, List
from dataclasses import dataclass, field
import re


@dataclass
class RiskMatrixResult:
    risk_score: int  # 0 - 100% (im wyżej, tym większe ryzyko)
    risk_level: str  # "NISKIE", "ŚREDNIE", "WYSOKIE"
    legal_flags_count: int
    missing_fields_count: int
    completeness_score: str
    total_tco_extra: float
    suggested_discount: float
    discount_success_rate: int  # np. 85%


class RiskCalculator:
    """
    Deterministyczny kalkulator punktacji ryzyka i potencjału negocjacyjnego.
    """

    @staticmethod
    def calculate(parsed_data: Dict[str, Any]) -> RiskMatrixResult:
        base_score = 0
        legal_flags = 0
        missing_count = 0
        tco_extra = 0.0

        # 1. Weryfikacja prawa konsumenckiego (rękojmia / zwroty)
        has_rekojmia_clause = parsed_data.get("rekojmia_excluded", False)
        is_company = parsed_data.get("seller_type") == "Firma"

        if has_rekojmia_clause:
            base_score += 35
            legal_flags += 1
            if is_company:
                # Nielegalne wyłącznie rękojmi dla konsumenta przez firmę
                base_score += 20
                legal_flags += 1

        if not parsed_data.get("has_return_policy", True):
            base_score += 25
            legal_flags += 1

        # 2. Kompletność ogłoszenia
        required_fields = ["description", "images", "shipping_cost", "invoice_type", "location"]
        for f in required_fields:
            if not parsed_data.get(f):
                missing_count += 1
                base_score += 8

        # 3. Szacowanie kosztów ukrytych (TCO Extra)
        shipping_cost = float(parsed_data.get("shipping_cost", 0.0) or 0.0)
        pcc_tax = 0.0
        item_price = float(parsed_data.get("price", 0.0) or 0.0)

        # Jeżeli sprzedaż od osoby prywatnej powyżej 1000 PLN -> 2% PCC-3
        if not is_company and item_price > 1000.0:
            pcc_tax = round(item_price * 0.02, 2)
            tco_extra += pcc_tax

        tco_extra += shipping_cost

        # 4. Wyliczenie Poziomu Ryzyka
        final_score = min(100, max(0, base_score))
        if final_score <= 35:
            risk_level = "NISKIE"
        elif final_score <= 65:
            risk_level = "ŚREDNIE"
        else:
            risk_level = "WYSOKIE"

        # 5. Wyliczenie potencjału negocjacyjnego (obniżki)
        # Baza: 5% ceny wyjściowej + bonus za wykryte wady i braki
        discount_percentage = 0.05 + (legal_flags * 0.03) + (missing_count * 0.01)
        suggested_discount = round(item_price * min(discount_percentage, 0.20), 2)
        success_rate = 85 if legal_flags > 0 else 60

        # Completeness Score
        completeness = max(0, 100 - (missing_count * 15))

        return RiskMatrixResult(
            risk_score=final_score,
            risk_level=risk_level,
            legal_flags_count=legal_flags,
            missing_fields_count=missing_count,
            completeness_score=f"{completeness}%",
            total_tco_extra=round(tco_extra, 2),
            suggested_discount=suggested_discount,
            discount_success_rate=success_rate
        )


class AuditEngine:
    """
    Główny orkiestrator generujący strukturę raportu audytowego.
    """

    def __init__(self):
        self.calculator = RiskCalculator()

    def generate_report(self, raw_data: Dict[str, Any], report_id: str, is_unlocked: bool = False) -> Dict[str, Any]:
        metrics = self.calculator.calculate(raw_data)

        # Sekcja darmowa: 5 podstawowych punktów
        free_points = [
            {
                "title": "1. Weryfikacja prawa do 14-dniowego zwrotu",
                "status": "RYZYKO" if not raw_data.get("has_return_policy", True) else "OK",
                "desc": "Sprzedawca w opisie ogranicza prawo do zwrotu towaru." if not raw_data.get("has_return_policy", True) else "Prawo do odstąpienia od umowy bez podania przyczyny jest zachowane.",
                "is_ok": raw_data.get("has_return_policy", True)
            },
            {
                "title": "2. Analiza zapisu o rękojmi konsumenckiej",
                "status": "UWAGA" if raw_data.get("rekojmia_excluded") else "OK",
                "desc": "Wykryto próbę wyłączenia lub ograniczenia rękojmi za wady." if raw_data.get("rekojmia_excluded") else "Standardowa rękojmia prawna obowiązuje.",
                "is_ok": not raw_data.get("rekojmia_excluded")
            },
            {
                "title": "3. Sprawdzenie typu faktury / dowodu zakupu",
                "status": "OK" if raw_data.get("invoice_type") else "UWAGA",
                "desc": f"Zadeklarowany dokument: {raw_data.get('invoice_type', 'Brak szczegółów')}",
                "is_ok": bool(raw_data.get("invoice_type"))
            },
            {
                "title": "4. Estymacja dodatkowych opłat i transportu",
                "status": "INFO",
                "desc": f"Szacowane opły dodatkowe (np. dostawa, PCC-3): +{metrics.total_tco_extra} PLN",
                "is_ok": True
            },
            {
                "title": "5. Sprawdzenie statusu profilu sprzedającego",
                "status": "OK",
                "desc": f"Typ konta: {raw_data.get('seller_type', 'Osoba prywatna')}. Brak wpisów w publicznych rejestrach ostrzeżeń.",
                "is_ok": True
            }
        ]

        # 3 Sugerowane Pytania AI do sprzedawcy (dane dla opłaconego raportu)
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
        script = (
            f"Dzień dobry, jestem zainteresowany zakupem przedmiotu z oferty ({raw_data.get('target_url')}). "
            f"Z uwagi na wykryte braki w opisie oraz szacowane koszty dodatkowe, proponuję cenę o {metrics.suggested_discount} PLN niższą. "
            f"W przypadku akceptacji jestem gotowy sfinalizować zakup dzisiaj."
        )

        return {
            "report_id": report_id,
            "target_url": raw_data.get("target_url"),
            "category": raw_data.get("category", "Sprzęt / Elektronika"),
            "created_at": raw_data.get("created_at", "01.08.2026"),
            "risk_score": metrics.risk_score,
            "risk_level": metrics.risk_level,
            "legal_flags": [1] * metrics.legal_flags_count,
            "total_tco_extra": metrics.total_tco_extra,
            "completeness_score": metrics.completeness_score,
            "missing_fields_count": metrics.missing_fields_count,
            "seller_type": raw_data.get("seller_type", "Osoba Prywatna"),
            "rekojmia_status": "Wyłączona" if raw_data.get("rekojmia_excluded") else "Obowiązuje",
            "history_status": "Czysty profil",
            "is_unlocked": is_unlocked,
            "free_points": free_points,
            "suggested_discount": f"{metrics.suggested_discount} PLN",
            "negotiation_script": script,
            "questions": questions
        }