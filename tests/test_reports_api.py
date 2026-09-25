# tests/test_reports_api.py
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import Voucher


@pytest.mark.asyncio
async def test_report_freemium_and_mock_checkout_flow(async_client: AsyncClient):
    """Weryfikacja pełnego przepływu: tworzenie raportu freemium, pobranie oraz odblokowanie mock-checkout w bazie RAM."""
    test_url = "https://www.olx.pl/d/oferta/test-freemium-flow-ID123.html"
    create_res = await async_client.post("/api/v1/reports", json={"url": test_url})
    assert create_res.status_code == 201

    report_data = create_res.json()
    report_id = report_data["report_id"]
    assert report_data["is_unlocked"] is False

    # Sprawdzenie czy deep_analysis istnieje i ma ustawiony verdict
    if report_data.get("deep_analysis"):
        assert "Zablokowana" in report_data["deep_analysis"].get("verdict", "")

    get_res = await async_client.get(f"/api/v1/reports/{report_id}")
    assert get_res.status_code == 200
    assert get_res.json()["is_unlocked"] is False

    checkout_res = await async_client.post(f"/api/v1/reports/{report_id}/mock-checkout")
    assert checkout_res.status_code == 200
    unlocked_data = checkout_res.json()
    assert unlocked_data["is_unlocked"] is True


@pytest.mark.asyncio
async def test_unlock_report_with_valid_voucher(
    async_client: AsyncClient, 
    db_session: AsyncSession
):
    """Weryfikacja odblokowania raportu za pomocą aktywnego vouchera w bazie RAM."""
    voucher_code = f"TESTV_{uuid.uuid4().hex[:8].upper()}"

    # Zapisujemy voucher w izolowanej sesji testowej (RAM)
    db_session.add(Voucher(code=voucher_code, is_active=True))
    await db_session.commit()

    test_url = "https://www.olx.pl/d/oferta/test-voucher-valid-ID456.html"
    create_res = await async_client.post("/api/v1/reports", json={"url": test_url})
    assert create_res.status_code == 201

    report_id = create_res.json()["report_id"]

    unlock_res = await async_client.post(
        f"/api/v1/reports/{report_id}/voucher",
        json={"voucher_code": voucher_code},
    )
    assert unlock_res.status_code == 200
    assert unlock_res.json()["is_unlocked"] is True


@pytest.mark.asyncio
async def test_unlock_report_with_invalid_voucher(async_client: AsyncClient):
    """Weryfikacja obsługi błędu przy próbie użycia nieistniejącego kodu vouchera."""
    test_url = "https://www.olx.pl/d/oferta/test-voucher-invalid-ID789.html"
    create_res = await async_client.post("/api/v1/reports", json={"url": test_url})
    assert create_res.status_code == 201

    report_id = create_res.json()["report_id"]

    unlock_res = await async_client.post(
        f"/api/v1/reports/{report_id}/voucher",
        json={"voucher_code": "NON_EXISTING_VOUCHER_CODE_999"},
    )
    assert unlock_res.status_code == 400


@pytest.mark.asyncio
async def test_get_non_existent_report(async_client: AsyncClient):
    """Weryfikacja zwrócenia błędu 404 dla nieistniejącego raportu."""
    res = await async_client.get("/api/v1/reports/non-existent-report-id-999")
    assert res.status_code == 404