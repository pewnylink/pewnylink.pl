# app/routers/affiliates.py
import hashlib
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.affiliate import AffiliateOffer, AffiliateClickLog

router = APIRouter(tags=["affiliates"])

@router.get("/r/{offer_id}")
async def track_and_redirect(
    offer_id: int, 
    report_id: str = None, 
    request: Request = None, 
    db: AsyncSession = Depends(get_db)
):
    """
    Rejestruje kliknięcie w bazie SQLite (asynchronicznie) i przekierowuje użytkownika na docelowy URL partnera.
    """
    # 1. Pobierz aktywną ofertę z bazy
    stmt = select(AffiliateOffer).where(
        AffiliateOffer.id == offer_id, 
        AffiliateOffer.is_active == True
    )
    result = await db.execute(stmt)
    offer = result.scalar_one_or_none()

    if not offer:
        raise HTTPException(status_code=404, detail="Oferta nie istnieje lub jest nieaktywna.")

    # 2. Rejestracja zdarzenia w bazie (zgodna z RODO - hash IP)
    ip_raw = request.client.host if request else ""
    ip_hash = hashlib.sha256(ip_raw.encode()).hexdigest()[:16] if ip_raw else None

    click_log = AffiliateClickLog(
        offer_id=offer.id,
        report_id=report_id,
        user_agent=request.headers.get("user-agent") if request else None,
        ip_hash=ip_hash
    )
    
    # Inkrementacja licznika i zapis logu
    offer.click_count += 1
    db.add(click_log)
    await db.commit()

    # 3. Bezpieczne przekierowanie HTTP 307 (Temporary Redirect)
    return RedirectResponse(url=offer.destination_url, status_code=307)