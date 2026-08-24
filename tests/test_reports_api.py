# tests/test_reports_api.py
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.db.session import AsyncSessionLocal, engine
from app.models.db_models import Base, Voucher


@pytest_asyncio.fixture(scope="function", autouse=True)
async def init_test_database():
    """Automatycznie tworzy czysty schemat tabel przed każdym testem i czyści go po zakończeniu."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_report_freemium_and_mock_checkout_flow():
    """Weryfikacja pełnego przepływu: tworzenie raportu freemium, pobranie oraz odblokowanie mock-checkout."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        test_url = "https://www.olx.pl/d/oferta/test-freemium-flow-ID123.html"
        create_res = await ac.post("/api/v1/reports", json={"url": test_url})
        assert create_res.status_code == 201

        report_data = create_res.json()
        report_id = report_data["report_id"]
        assert report_data["is_unlocked"] is False

        # Sprawdzenie czy deep_analysis istnieje i ma ustawiony verdict
        if report_data.get("deep_analysis"):
            assert "Zablokowana" in report_data["deep_analysis"].get("verdict", "")

        get_res = await ac.get(f"/api/v1/reports/{report_id}")
        assert get_res.status_code == 200
        assert get_res.json()["is_unlocked"] is False

        checkout_res = await ac.post(f"/api/v1/reports/{report_id}/mock-checkout")
        assert checkout_res.status_code == 200
        unlocked_data = checkout_res.json()
        assert unlocked_data["is_unlocked"] is True


@pytest.mark.asyncio
async def test_unlock_report_with_valid_voucher():
    """Weryfikacja odblokowania raportu za pomocą aktywnego vouchera."""
    voucher_code = f"TESTV_{uuid.uuid4().hex[:8].upper()}"

    async with AsyncSessionLocal() as session:
        session.add(Voucher(code=voucher_code, is_active=True))
        await session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        test_url = "https://www.olx.pl/d/oferta/test-voucher-valid-ID456.html"
        create_res = await ac.post("/api/v1/reports", json={"url": test_url})
        assert create_res.status_code == 201

        report_id = create_res.json()["report_id"]

        unlock_res = await ac.post(
            f"/api/v1/reports/{report_id}/voucher",
            json={"voucher_code": voucher_code},
        )
        assert unlock_res.status_code == 200
        assert unlock_res.json()["is_unlocked"] is True


@pytest.mark.asyncio
async def test_unlock_report_with_invalid_voucher():
    """Weryfikacja obsługi błędu przy próbie użycia nieistniejącego kodu vouchera."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        test_url = "https://www.olx.pl/d/oferta/test-voucher-invalid-ID789.html"
        create_res = await ac.post("/api/v1/reports", json={"url": test_url})
        assert create_res.status_code == 201

        report_id = create_res.json()["report_id"]

        unlock_res = await ac.post(
            f"/api/v1/reports/{report_id}/voucher",
            json={"voucher_code": "NON_EXISTING_VOUCHER_CODE_999"},
        )
        assert unlock_res.status_code == 400


@pytest.mark.asyncio
async def test_get_non_existent_report():
    """Weryfikacja zwrócenia błędu 404 dla nieistniejącego raportu."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        res = await ac.get("/api/v1/reports/non-existent-report-id-999")
        assert res.status_code == 404