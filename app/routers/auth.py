# app/routers/auth.py
from datetime import datetime, timedelta
from bson import ObjectId
from fastapi import APIRouter, HTTPException, status, Depends

from app.database import get_database
from app.models.user import UserRegister, UserLogin, TokenResponse, UserResponse, UserRole, VoucherCreate, VoucherRedeem
from app.core.security import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["Auth & Access"])

@router.post("/register", response_model=TokenResponse)
async def register(payload: UserRegister):
    db = get_database()
    users_col = db["users"]

    # 1. Sprawdzenie, czy email jest unikalny
    existing = await users_col.find_one({"email": payload.email.lower()})
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Konto z tym adresem e-mail już istnieje.")

    # 2. Tworzenie dokumentu użytkownika
    # Pierwsze konta lub wybrane maile można ustawić jako SUPER_ADMIN
    role = UserRole.USER
    
    user_doc = {
        "email": payload.email.lower(),
        "password_hash": hash_password(payload.password),
        "full_name": payload.full_name,
        "role": role,
        "access_until": None,  # Domyślnie brak dostępu do czasu aktywacji vouchera/subskrypcji
        "created_at": datetime.utcnow()
    }

    result = await users_col.insert_one(user_doc)
    user_id = str(result.inserted_id)

    token = create_access_token(user_id=user_id, role=role)
    
    user_resp = UserResponse(
        id=user_id,
        email=payload.email.lower(),
        full_name=payload.full_name,
        role=role,
        access_until=None,
        created_at=user_doc["created_at"]
    )

    return TokenResponse(access_token=token, user=user_resp)


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin):
    db = get_database()
    user = await db["users"].find_one({"email": payload.email.lower()})

    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Błędny e-mail lub hasło.")

    user_id = str(user["_id"])
    token = create_access_token(user_id=user_id, role=user["role"])

    user_resp = UserResponse(
        id=user_id,
        email=user["email"],
        full_name=user["full_name"],
        role=user["role"],
        access_until=user.get("access_until"),
        created_at=user["created_at"]
    )

    return TokenResponse(access_token=token, user=user_resp)


@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        full_name=current_user["full_name"],
        role=current_user["role"],
        access_until=current_user.get("access_until"),
        created_at=current_user["created_at"]
    )


# --- ZARZĄDZANIE VOUCHERAMI ---

@router.post("/vouchers/create", tags=["Admin Vouchers"])
async def create_voucher(payload: VoucherCreate, current_user: dict = Depends(get_current_user)):
    """Tworzenie kodów promocyjnych (Dostępne tylko dla ról SUPER_ADMIN)."""
    if current_user["role"] != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Brak uprawnień administratora.")

    db = get_database()
    vouchers_col = db["vouchers"]

    code_clean = payload.code.upper().strip()
    
    voucher_doc = {
        "code": code_clean,
        "days_validity": payload.days_validity,
        "max_uses": payload.max_uses,
        "uses_count": 0,
        "created_at": datetime.utcnow()
    }

    await vouchers_col.update_one({"code": code_clean}, {"$set": voucher_doc}, upsert=True)
    return {"status": "ok", "message": f"Voucher '{code_clean}' na {payload.days_validity} dni został stworzony."}


@router.post("/vouchers/redeem")
async def redeem_voucher(payload: VoucherRedeem, current_user: dict = Depends(get_current_user)):
    """Realizacja vouchera przez użytkownika."""
    db = get_database()
    vouchers_col = db["vouchers"]
    users_col = db["users"]

    code_clean = payload.code.upper().strip()
    voucher = await vouchers_col.find_one({"code": code_clean})

    if not voucher:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Podany kod jest nieprawidłowy.")

    if voucher["uses_count"] >= voucher["max_uses"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ten kod został już wykorzystany limit razy.")

    # Wyliczanie nowej daty ważności konta
    now = datetime.utcnow()
    current_access = current_user.get("access_until")
    
    # Jeśli użytkownik miał już ważny dostęp, wydłużamy od tamtego momentu, jeśli nie - od teraz
    base_date = current_access if (current_access and current_access > now) else now
    new_access_until = base_date + timedelta(days=voucher["days_validity"])

    # Aktualizacja w bazie
    await users_col.update_one(
        {"_id": ObjectId(current_user["id"])},
        {"$set": {"access_until": new_access_until, "role": UserRole.VIP_GUEST}}
    )

    await vouchers_col.update_one(
        {"_id": voucher["_id"]},
        {"$inc": {"uses_count": 1}}
    )

    return {
        "status": "ok",
        "message": f"Kod aktywowany! Dostęp do raportów został przyznany do: {new_access_until.strftime('%Y-%m-%d %H:%M')}",
        "access_until": new_access_until
    }