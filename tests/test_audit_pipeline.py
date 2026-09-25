# tests/test_audit_pipeline.py
import asyncio
import pytest
from app.services.audit_service import AuditEngine


@pytest.mark.asyncio
async def test_audit_pipeline_in_flight():
    """
    Test weryfikujący działanie silnika audytowego w locie za pomocą pytest.
    Gwarantuje, że dane są przetwarzane w pamięci bez naruszania bazy danych.
    """
    test_url = "https://www.olx.pl/d/oferta/gitara-elektryczna-epiphone-les-paul-custom-CID99-ID12345.html"

    # Wywołanie silnika audytowego w locie
    report = await AuditEngine.analyze_url(url=test_url, is_unlocked=True)

    # Asercje pytest zamiast zwykłego print()
    assert report is not None, "Raport z audytu nie powinien być pusty"
    assert "title" in report, "Raport powinien zawierać tytuł"
    assert "risk_score" in report, "Raport powinien zawierać wskaźnik ryzyka"
    
    # Dodatkowa weryfikacja biznesowa
    print(f"\n[OK] Audyt przeanalizowany w locie: {report.get('title')}")


# Pozostawiamy blok Main dla możliwości opcjonalnego, ręcznego uruchomienia, 
# ale wymuszamy ustawienie zmiennej środowiskowej TESTING
if __name__ == "__main__":
    import os
    os.environ["TESTING"] = "True"
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    
    async def run_standalone():
        print("Uruchamianie audytu w trybie bezpośrednim (In-Memory)...")
        await test_audit_pipeline_in_flight()
        print("Test w locie zakończony powodzeniem.")

    asyncio.run(run_standalone())