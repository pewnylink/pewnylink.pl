# app/api/v1/endpoints/payments.py
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.services.report_repository import ReportRepository

stripe.api_key = settings.STRIPE_SECRET_KEY

router = APIRouter(prefix="/payments", tags=["Payments API"])


@router.post("/checkout/create-session/{report_id}")
async def create_checkout_session(
    report_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Tworzy sesję Stripe Checkout dla wskazanego raportu.
    """
    clean_report_id = report_id.strip()
    db_report = await ReportRepository.get_by_report_id(db, clean_report_id)

    if not db_report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Raport '{clean_report_id}' nie istnieje.",
        )

    if db_report.is_unlocked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Raport jest już odblokowany.",
        )

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card", "blik"],
            line_items=[
                {
                    "price_data": {
                        "currency": "pln",
                        "product_data": {
                            "name": f"Pełny Raport Weryfikacyjny: {db_report.title_raw[:50]}",
                            "description": f"Audyt ryzyka dla ogłoszenia ({db_report.industry_name})",
                        },
                        "unit_amount": 4900,  # Kwota w groszach: 49.00 PLN
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            metadata={
                "report_id": db_report.report_id,
                "consumer_consent_loss_of_withdrawal": "true",  # Flaga zgodności z przepisami SaaS/E-commerce
            },
            success_url=f"{settings.FRONTEND_URL}/report/{db_report.report_id}?status=success",
            cancel_url=f"{settings.FRONTEND_URL}/report/{db_report.report_id}?status=cancelled",
        )
        return {"checkout_url": checkout_session.url, "session_id": checkout_session.id}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Błąd podczas tworzenia sesji płatności: {str(e)}",
        )


@router.post("/stripe/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Webhook odbierający powiadomienia od Stripe.
    Po udanej płatności automatycznie aktualizuje stan raportu (is_paid = True, is_unlocked = True).
    """
    payload = await request.body()

    if not stripe_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Brak nagłówka Stripe-Signature.",
        )

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nieprawidłowy payload.")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nieprawidłowy podpis Stripe-Signature.")

    # Obsługa udanego zakupu
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        metadata = session.get("metadata", {})
        report_id = metadata.get("report_id")

        if report_id:
            db_report = await ReportRepository.get_by_report_id(db, report_id)
            if db_report:
                db_report.is_paid = True
                db_report.is_unlocked = True
                await db.commit()

    return {"status": "success"}