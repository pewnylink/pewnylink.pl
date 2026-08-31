# app/models/affiliate.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.session import Base

class AffiliateOffer(Base):
    """Model oferty afiliacyjnej zarządzanej z panelu admina."""
    __tablename__ = "affiliate_offers"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(150), nullable=False)           # np. "Porównywarka OC/AC – Mubi"
    provider = Column(String(50), nullable=False)         # np. "Mubi"
    badge = Column(String(50), nullable=True)             # np. "Oszczędność" lub "Partner Finansowy"
    description = Column(Text, nullable=False)            # Opis oferty
    destination_url = Column(Text, nullable=False)       # Pełny URL partnerski
    category = Column(String(50), nullable=False, index=True) # "auto", "machinery", "real_estate", "general"
    section = Column(String(50), nullable=False, index=True)  # "financial", "checkpoints", "green_light"
    cta_text = Column(String(50), default="Sprawdź")      # Treść przycisku (np. "Oblicz składkę")
    color = Column(String(20), default="indigo")          # Kolor akcentu (indigo, amber, emerald, purple)
    is_active = Column(Boolean, default=True, index=True) # Status aktywności z admina
    click_count = Column(Integer, default=0)              # Ogólny licznik kliknięć

    clicks = relationship("AffiliateClickLog", back_populates="offer", cascade="all, delete-orphan")


class AffiliateClickLog(Base):
    """Rejestr pojedynczych kliknięć do analityki w panelu admina."""
    __tablename__ = "affiliate_clicks"

    id = Column(Integer, primary_key=True, index=True)
    offer_id = Column(Integer, ForeignKey("affiliate_offers.id", ondelete="CASCADE"), nullable=False)
    report_id = Column(String(50), nullable=True, index=True) # ID raportu, z którego kliknięto
    clicked_at = Column(DateTime, default=datetime.utcnow, index=True)
    user_agent = Column(String(255), nullable=True)
    ip_hash = Column(String(64), nullable=True)           # Hash IP (zgodność z RODO)

    offer = relationship("AffiliateOffer", back_populates="clicks")