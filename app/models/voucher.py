# app/models/voucher.py
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Voucher(Base):
    __tablename__ = "vouchers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    days_validity: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    max_uses: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    uses_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False
    )