# tests/test_payments_api.py
from unittest.mock import patch, MagicMock
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.db.session import AsyncSessionLocal
from app.services.report_generator import generate_audit_report
from app.services.report_repository import ReportRepository


@pytest.mark.asyncio
async def test_create_checkout_session_success():
    """Weryfikuje tworzenie sesji checkout Stripe dla istniejącego raportu."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Tworzenie raportu testowego w bazie danych
        async with AsyncSessionLocal() as db:
            report_doc = await generate_audit_report(
                listing_text="Oferta testowa stripe",
                target_url="https://olx.pl/oferta-testowa-123",
                industry="general",
                is_unlocked=False,
            )
            report = await ReportRepository.create_report(db, report_doc)
            report_id = report.report_id

        # 2. Mockowanie odpowiedzi biblioteki Stripe
        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/pay/cs_test_123"
        mock_session.id = "cs_test_123"

        with patch("stripe.checkout.Session.create", return_value=mock_session):
            response = await client.post(f"/api/v1/payments/checkout/create-session/{report_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["checkout_url"] == "https://checkout.stripe.com/pay/cs_test_123"
        assert data["session_id"] == "cs_test_123"


@pytest.mark.asyncio
async def test_stripe_webhook_unlocks_report():
    """Weryfikuje, czy zdarzenie płatności z Stripe webhooka odblokowuje raport."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Tworzenie zablokowanego raportu w bazie danych
        async with AsyncSessionLocal() as db:
            report_doc = await generate_audit_report(
                listing_text="Oferta webhook test",
                target_url="https://olx.pl/webhook-test",
                industry="general",
                is_unlocked=False,
            )
            report = await ReportRepository.create_report(db, report_doc)
            report_id = report.report_id

        # 2. Przygotowanie danych zdarzenia checkout.session.completed
        fake_event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "metadata": {
                        "report_id": report_id
                    }
                }
            }
        }

        # 3. Wysłanie żądania do webhooka z zamockowaną weryfikacją podpisu
        with patch("stripe.Webhook.construct_event", return_value=fake_event):
            response = await client.post(
                "/api/v1/payments/stripe/webhook",
                headers={"Stripe-Signature": "t=123,v1=test_signature"},
                json={}
            )

        assert response.status_code == 200
        assert response.json() == {"status": "success"}

        # 4. Sprawdzenie, czy status raportu w bazie zmienił się na odblokowany
        async with AsyncSessionLocal() as db:
            updated_report = await ReportRepository.get_by_report_id(db, report_id)
            assert updated_report.is_paid is True
            assert updated_report.is_unlocked is True