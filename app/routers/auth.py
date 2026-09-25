# app/routers/auth.py
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
import jwt
from fastapi import APIRouter, HTTPException, status, Depends, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.core.config import settings
from app.models.db_models import User, Voucher
from app.models.user import (
    UserRegister,
    UserLogin,
    UserResponse,
    TokenResponse,
    UserRole,
    VoucherCreate,
    VoucherRedeem
)
from app.core.security import hash_password, verify_password, create_access_token, get_token_from_request
from app.dependencies import get_current_user_required

router = APIRouter(prefix="/api/v1/auth", tags=["Auth & Access"])


async def get_optional_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Pobiera zalogowanego użytkownika z ciasteczka/nagłówka JWT, lub zwraca None gdy niezalogowany."""
    try:
        token = get_token_from_request(request)
        if not token:
            return None
        
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        stmt = select(User).where(User.id == (int(user_id) if str(user_id).isdigit() else user_id))
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    except Exception:
        return None


@router.post("/register", response_model=TokenResponse)
async def register(
    payload: UserRegister, 
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    email_clean = payload.email.lower().strip()

    stmt = select(User).where(User.email == email_clean)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Konto z tym adresem e-mail już istnieje."
        )

    role_val = UserRole.USER.value if hasattr(UserRole.USER, 'value') else str(UserRole.USER)
    now_utc = datetime.now(timezone.utc)

    new_user = User(
        email=email_clean,
        hashed_password=hash_password(payload.password),
        role=role_val,
        is_admin=False,
        created_at=now_utc
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    role_str = new_user.role.value if hasattr(new_user.role, 'value') else str(new_user.role)
    token = create_access_token(user_id=new_user.id, role=role_str)

    response.set_cookie(key="access_token", value=token, httponly=True, path="/", samesite="lax")

    user_resp = UserResponse(
        id=str(new_user.id),
        email=new_user.email,
        full_name=payload.full_name,
        role=new_user.role,
        access_until=None,
        created_at=new_user.created_at
    )

    return TokenResponse(access_token=token, user=user_resp)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: UserLogin, 
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    email_clean = payload.email.lower().strip()
    
    stmt = select(User).where(User.email == email_clean)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Błędny e-mail lub hasło."
        )

    role_str = user.role.value if hasattr(user.role, 'value') else str(user.role)
    token = create_access_token(user_id=user.id, role=role_str)

    response.set_cookie(key="access_token", value=token, httponly=True, path="/", samesite="lax")

    user_resp = UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=getattr(user, "full_name", None),
        role=user.role,
        access_until=getattr(user, "access_until", None),
        created_at=user.created_at
    )

    return TokenResponse(access_token=token, user=user_resp)


@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: User = Depends(get_current_user_required)):
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=getattr(current_user, "full_name", None),
        role=current_user.role,
        access_until=getattr(current_user, "access_until", None),
        created_at=current_user.created_at
    )


# --- ZARZĄDZANIE VOUCHERAMI ---

@router.post("/vouchers/create", tags=["Admin Vouchers"])
async def create_voucher(
    payload: VoucherCreate, 
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """Tworzenie kodów promocyjnych (Dostępne tylko dla administratorów)."""
    role_val = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    is_admin_flag = getattr(current_user, "is_admin", False)

    if not is_admin_flag and role_val != "SUPER_ADMIN" and current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Brak uprawnień administratora."
        )

    code_clean = payload.code.upper().strip()
    
    stmt = select(Voucher).where(Voucher.code == code_clean)
    result = await db.execute(stmt)
    voucher = result.scalar_one_or_none()

    if voucher:
        voucher.days_validity = payload.days_validity
        voucher.max_uses = payload.max_uses
        if hasattr(voucher, "is_active"):
            voucher.is_active = True
    else:
        voucher_kwargs = {
            "code": code_clean,
            "days_validity": payload.days_validity,
            "max_uses": payload.max_uses,
            "uses_count": 0,
            "created_at": datetime.now(timezone.utc)
        }
        if hasattr(Voucher, "is_active"):
            voucher_kwargs["is_active"] = True

        voucher = Voucher(**voucher_kwargs)
        db.add(voucher)

    await db.commit()
    return {"status": "ok", "message": f"Voucher '{code_clean}' na {payload.days_validity} dni został stworzony."}


@router.post("/vouchers/redeem")
async def redeem_voucher(
    payload: VoucherRedeem, 
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """Realizacja vouchera przez użytkownika."""
    code_clean = payload.code.upper().strip()
    
    stmt_v = select(Voucher).where(Voucher.code == code_clean)
    res_v = await db.execute(stmt_v)
    voucher = res_v.scalar_one_or_none()

    if not voucher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Podany kod jest nieprawidłowy."
        )

    if hasattr(voucher, "is_active") and not voucher.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Ten kod jest nieaktywny."
        )

    if voucher.uses_count >= voucher.max_uses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Ten kod został już wykorzystany limit razy."
        )

    now = datetime.now(timezone.utc)
    current_access = getattr(current_user, "access_until", None)
    
    if current_access and current_access.tzinfo is None:
        current_access = current_access.replace(tzinfo=timezone.utc)

    base_date = current_access if (current_access and current_access > now) else now
    new_access_until = base_date + timedelta(days=voucher.days_validity)

    if hasattr(current_user, "access_until"):
        current_user.access_until = new_access_until
    
    vip_role = UserRole.VIP_GUEST.value if hasattr(UserRole.VIP_GUEST, 'value') else str(UserRole.VIP_GUEST)
    current_user.role = vip_role
    voucher.uses_count += 1

    if voucher.uses_count >= voucher.max_uses and hasattr(voucher, "is_active"):
        voucher.is_active = False

    await db.commit()

    return {
        "status": "ok",
        "message": f"Kod aktywowany! Dostęp został przyznany do: {new_access_until.strftime('%Y-%m-%d %H:%M')}",
        "access_until": new_access_until
    }