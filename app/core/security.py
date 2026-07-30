# app/core/security.py
import hashlib
import os
from datetime import datetime, timedelta
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings
from app.database import get_database
from app.models.user import UserRole

security = HTTPBearer()

def hash_password(password: str) -> str:
    """Szyfruje hasło za pomocą PBKDF2-HMAC-SHA256 z unikalną solą."""
    salt = os.urandom(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return salt.hex() + ":" + pwd_hash.hex()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Weryfikuje zgodność wpisanego hasła z zaszyfrowanym ciągiem z bazy."""
    try:
        salt_hex, hash_hex = hashed_password.split(":")
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', plain_password.encode('utf-8'), salt, 100000)
        return pwd_hash == expected_hash
    except Exception:
        return False

def create_access_token(user_id: str, role: str) -> str:
    """Generuje szyfrowany token JWT dla użytkownika."""
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": user_id,
        "role": role,
        "exp": expire
    }
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Pobiera i weryfikuje użytkownika z tokena Bearer JWT."""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Nieprawidłowy token autoryzacji.")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Błąd dekodowania tokena lub token wygasł.")

    db = get_database()
    from bson import ObjectId
    user = await db["users"].find_one({"_id": ObjectId(user_id)})
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Konto użytkownika nie istnieje.")
    
    user["id"] = str(user["_id"])
    return user

def verify_active_access(user: dict):
    """
    Kluczowa logika SevArt:
    - SUPER_ADMIN ma stały, bezwarunkowy dostęp (Seba + Wspólnik).
    - Pozostali muszą posiadać aktualną datę access_until > teraz.
    """
    if user.get("role") == UserRole.SUPER_ADMIN:
        return True

    access_until = user.get("access_until")
    if not access_until or access_until < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Brak aktywnego dostępu do generowania raportów. Aktywuj kod voucher lub przedłuż pakiet."
        )
    return True