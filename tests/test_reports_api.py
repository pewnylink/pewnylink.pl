# tests/test_reports_api.py
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_create_and_get_report_flow():
    """
    Test integracyjny:
    1. Wysyła POST /api/v1/reports z prawidłowymi danymi.
    2. Weryfikuje status HTTP 201 oraz maskowanie sekcji płatnych w odpowiedzi.
    3. Wysyła GET /api/v1/reports/{report_id} z pobranym id.
    4. Weryfikuje status HTTP 200 oraz spójność danych z bazą.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. TWORZENIE RAPORTU (POST)
        payload = {
            "target_url": "https://www.olx.pl/d/oferta/auto-testowe-ID12345.html",
            "listing_text": "Sprzedam samochód osobowy, stan idealny, bezwypadkowy, serwis w ASO.",
            "industry": "automotive",
        }

        response = await client.post("/api/v1/reports", json=payload)

        assert response.status_code == 201
        data = response.json()

        assert "id" in data
        assert "report_id" in data
        assert data["report_id"].startswith("REP-")
        assert data["is_unlocked"] is False
        assert data["is_paid"] is False

        # Weryfikacja maskowania danych płatnych (Freemium)
        assert data["freemium_preview"] is not None
        assert data["digital_footprint"] is None
        assert data["financial_analysis"] is None
        assert data["expert_checkpoints"] is None
        assert data["negotiation_assistant"] is None

        report_id = data["report_id"]

        # 2. POBIERANIE RAPORTU PO ID (GET)
        get_response = await client.get(f"/api/v1/reports/{report_id}")

        assert get_response.status_code == 200
        get_data = get_response.json()

        assert get_data["report_id"] == report_id
        assert get_data["target_url"] == payload["target_url"]
        assert get_data["is_unlocked"] is False
        assert get_data["digital_footprint"] is None


@pytest.mark.asyncio
async def test_get_nonexistent_report():
    """
    Test weryfikujący odpowiedź HTTP 404 dla nieistniejącego raportu.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/reports/REP-NONEXISTENT999")

        assert response.status_code == 404
        assert "nie istnieje" in response.json()["detail"]