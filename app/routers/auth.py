# app/routers/auth.py
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.database import get_db
from app.models.user import (
    UserRegister, 
    UserLogin, 
    TokenResponse, 
    UserResponse, 
    UserRole, 
    VoucherCreate, 
    VoucherRedeem,
    User,
    Voucher
)
from app.core.security import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["Auth & Access"])


@router.post("/register", response_model=TokenResponse)
async def register(payload: UserRegister, db: AsyncSession = Depends(get_db)):
    email_clean = payload.email.lower().strip()

    # 1. Sprawdzenie unikalności adresu e-mail
    stmt = select(User).where(User.email == email_clean)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Konto z tym adresem e-mail już istnieje."
        )

    # 2. Tworzenie obiektu użytkownika w PostgreSQL
    role = UserRole.USER
    now_utc = datetime.now(timezone.utc)

    new_user = User(
        email=email_clean,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=role,
        access_until=None,
        created_at=now_utc
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    user_id_str = str(new_user.id)
    token = create_access_token(user_id=user_id_str, role=role)

    user_resp = UserResponse(
        id=user_id_str,
        email=new_user.email,
        full_name=new_user.full_name,
        role=new_user.role,
        access_until=None,
        created_at=new_user.created_at
    )

    return TokenResponse(access_token=token, user=user_resp)


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    email_clean = payload.email.lower().strip()
    
    stmt = select(User).where(User.email == email_clean)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Błędny e-mail lub hasło."
        )

    user_id_str = str(user.id)
    token = create_access_token(user_id=user_id_str, role=user.role)

    user_resp = UserResponse(
        id=user_id_str,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        access_until=user.access_until,
        created_at=user.created_at
    )

    return TokenResponse(access_token=token, user=user_resp)


@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        id=str(current_user["id"]),
        email=current_user["email"],
        full_name=current_user["full_name"],
        role=current_user["role"],
        access_until=current_user.get("access_until"),
        created_at=current_user["created_at"]
    )


# --- ZARZĄDZANIE VOUCHERAMI ---

@router.post("/vouchers/create", tags=["Admin Vouchers"])
async def create_voucher(
    payload: VoucherCreate, 
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Tworzenie kodów promocyjnych (Dostępne tylko dla ról SUPER_ADMIN)."""
    if current_user["role"] != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Brak uprawnień administratora."
        )

    code_clean = payload.code.upper().strip()
    
    # Sprawdzamy czy voucher istnieje w bazie
    stmt = select(Voucher).where(Voucher.code == code_clean)
    result = await db.execute(stmt)
    voucher = result.scalar_one_or_none()

    if voucher:
        voucher.days_validity = payload.days_validity
        voucher.max_uses = payload.max_uses
    else:
        voucher = Voucher(
            code=code_clean,
            days_validity=payload.days_validity,
            max_uses=payload.max_uses,
            uses_count=0,
            created_at=datetime.now(timezone.utc)
        )
        db.add(voucher)

    await db.commit()
    return {"status": "ok", "message": f"Voucher '{code_clean}' na {payload.days_validity} dni został stworzony."}


@router.post("/vouchers/redeem")
async def redeem_voucher(
    payload: VoucherRedeem, 
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Realizacja vouchera przez użytkownika."""
    code_clean = payload.code.upper().strip()
    
    # 1. Pobranie vouchera
    stmt_v = select(Voucher).where(Voucher.code == code_clean)
    res_v = await db.execute(stmt_v)
    voucher = res_v.scalar_one_or_none()

    if not voucher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Podany kod jest nieprawidłowy."
        )

    if voucher.uses_count >= voucher.max_uses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Ten kod został już wykorzystany limit razy."
        )

    # 2. Wyliczanie nowej daty ważności konta
    now = datetime.now(timezone.utc)
    current_access = current_user.get("access_until")
    
    # Obsługa stref czasowych / naiwnych obiektów datetime
    if current_access and current_access.tzinfo is None:
        current_access = current_access.replace(tzinfo=timezone.utc)

    base_date = current_access if (current_access and current_access > now) else now
    new_access_until = base_date + timedelta(days=voucher.days_validity)

    # 3. Pobranie i aktualizacja użytkownika (wypchnięcie ObjectId na rzecz id PostgreSQL)
    user_id = int(current_user["id"]) if str(current_user["id"]).isdigit() else current_user["id"]
    stmt_u = select(User).where(User.id == user_id)
    res_u = await db.execute(stmt_u)
    user = res_u.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Użytkownik nie został znaleziony."
        )

    user.access_until = new_access_until
    user.role = UserRole.VIP_GUEST
    voucher.uses_count += 1

    await db.commit()

    return {
        "status": "ok",
        "message": f"Kod aktywowany! Dostęp do raportów został przyznany do: {new_access_until.strftime('%Y-%m-%d %H:%M')}",
        "access_until": new_access_until
    }