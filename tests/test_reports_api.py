# tests/test_reports_api.py
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_report_freemium_and_mock_checkout_flow():
    """
    Testuje kompletny cykl Freemium:
    1. Utworzenie raportu -> domyślnie is_unlocked == False
    2. GET /api/v1/reports/{id} -> sprawdzamy, że deep_analysis == None
    3. POST /api/v1/reports/{id}/mock-checkout -> symulacja odblokowania
    4. GET /api/v1/reports/{id} -> sprawdzamy, że deep_analysis zawiera pełne dane
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        test_url = "https://www.olx.pl/d/oferta/testowa-oferta-ID123.html"

        # KROK 1: Utworzenie raportu
        create_response = await ac.post("/api/v1/reports", json={"url": test_url})
        assert create_response.status_code == 201
        
        created_data = create_response.json()
        report_id = created_data["report_id"]
        
        assert created_data["target_url"] == test_url
        assert created_data["is_unlocked"] is False
        assert created_data["summary"] is not None
        assert created_data["deep_analysis"] is None

        # KROK 2: Pobranie raportu (wersja zablokowana)
        get_locked_res = await ac.get(f"/api/v1/reports/{report_id}")
        assert get_locked_res.status_code == 200
        
        locked_data = get_locked_res.json()
        assert locked_data["is_unlocked"] is False
        assert locked_data["deep_analysis"] is None

        # KROK 3: Symulacja zakupu przez endpoint /mock-checkout
        checkout_res = await ac.post(f"/api/v1/reports/{report_id}/mock-checkout")
        assert checkout_res.status_code == 200
        
        checkout_data = checkout_res.json()
        assert checkout_data["is_unlocked"] is True
        assert checkout_data["deep_analysis"] is not None
        assert isinstance(checkout_data["deep_analysis"]["red_flags"], list)

        # KROK 4: Weryfikacja ponownym GET (trwałość zmiany w bazie danych)
        get_unlocked_res = await ac.get(f"/api/v1/reports/{report_id}")
        assert get_unlocked_res.status_code == 200
        
        unlocked_data = get_unlocked_res.json()
        assert unlocked_data["is_unlocked"] is True
        assert unlocked_data["deep_analysis"] is not None
        assert "checklist" in unlocked_data["deep_analysis"]
        assert "negotiation_tips" in unlocked_data["deep_analysis"]


@pytest.mark.asyncio
async def test_get_non_existent_report():
    """Weryfikacja obsługi błędu 404 dla nieistniejącego raportu."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/reports/REP-NIE-ISTNIEJE-999")
        assert response.status_code == 404
        assert "nie istnieje" in response.json()["detail"]