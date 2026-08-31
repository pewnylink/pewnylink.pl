# app/core/affiliates.py
from typing import Dict, Any, List

AFFILIATE_CONFIG: Dict[str, Dict[str, List[Dict[str, str]]]] = {
    "auto": {
        "financial": [
            {
                "title": "Kredyt samochodowy / Leasing",
                "desc": "Oblicz ratę w 15 bankach i sprawdź zdolność bez wpływu na BIK.",
                "cta": "Sprawdź ratę",
                "url": "https://mylead.pl/link/auto-leasing-id",
                "badge": "Partner Finansowy",
                "color": "indigo"
            }
        ],
        "checkpoints": [
            {
                "title": "Pełna historia pojazdu w CarVertical",
                "desc": "Sprawdź przebieg, zdjęcia z aukcji i wpisy o szkodach całkowitych.",
                "cta": "Pobierz raport VIN",
                "url": "https://carvertical.com/partner_id",
                "badge": "Weryfikacja VIN",
                "color": "amber"
            }
        ],
        "green_light": [
            {
                "title": "Porównywarka OC/AC – Mubi",
                "desc": "Wylicz ubezpieczenie dla tego auta i odbierz 150 zł zwrotu.",
                "cta": "Oblicz składkę",
                "url": "https://mubi.pl/partner_id",
                "badge": "Oszczędność",
                "color": "emerald"
            }
        ]
    },
    "machinery": {
        "financial": [
            {
                "title": "Leasing Maszyn Budowlanych i Rolniczych",
                "desc": "Finansowanie do 100% wartości bez przedstawiania dokumentów finansowych.",
                "cta": "Wypełnij wniosek",
                "url": "https://systempartnerski.pl/leasing-maszyny",
                "badge": "Leasing Biznesowy",
                "color": "amber"
            }
        ]
    },
    "real_estate": {
        "financial": [
            {
                "title": "Porównywarka Kredytów Hipotecznych",
                "desc": "Bezpłatna konsultacja z ekspertem i analiza zdolności w 12 bankach.",
                "cta": "Umów rozmowę",
                "url": "https://e-broker.pl/hipoteka-id",
                "badge": "Hipoteka",
                "color": "purple"
            }
        ]
    }
}

def get_affiliate_widgets(category: str, placement: str) -> List[Dict[str, str]]:
    """Zwraca dedykowane widgety dla danej kategorii i miejsca w raporcie."""
    cat_config = AFFILIATE_CONFIG.get(category, AFFILIATE_CONFIG.get("auto", {}))
    return cat_config.get(placement, [])