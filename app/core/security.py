# app/core/security.py
import hashlib
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Any
import jwt
from fastapi import Request, HTTPException, status

from app.core.config import settings
# Poprawiony import modelu z db_models.py
from app.models.db_models import User


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


def create_access_token(user_id: Any, role: str) -> str:
    """Generuje szyfrowany token JWT dla użytkownika."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": str(user_id),
        "role": str(role),
        "exp": expire
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_token_from_request(request: Request) -> Optional[str]:
    """
    Uniwersalne pobieranie tokena:
    1. Najpierw szuka w ciasteczkach (klucz 'access_token') - dla przeglądarki/Jinja2.
    2. Jeśli brak, szuka w nagłówku 'Authorization: Bearer <token>' - dla klientów REST API.
    """
    token = request.cookies.get("access_token")
    if token:
        return token
    
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1]
        
    return None


def verify_active_access(user: User) -> bool:
    """Weryfikacja praw dostępu (ADMIN vs zwykły użytkownik)."""
    role_val = str(getattr(user, "role", "")).upper()
    is_admin_flag = getattr(user, "is_admin", False)

    # 1. Administratorzy i właściciele mają zawsze pełny dostęp
    if is_admin_flag or role_val in ["SUPER_ADMIN", "ADMIN"]:
        return True

    # 2. Bezpieczna weryfikacja dostępu dla zwykłych użytkowników
    access_until = getattr(user, "access_until", None)
    now_utc = datetime.now(timezone.utc)

    if access_until is None:
        # Jeśli użytkownik nie jest adminem i nie ma ustawionej daty dostępu
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Brak aktywnego dostępu do generowania raportów. Odnów pakiet subskrypcyjny."
        )

    if access_until.tzinfo is None:
        access_until = access_until.replace(tzinfo=timezone.utc)

    if access_until < now_utc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Brak aktywnego dostępu do generowania raportów. Odnów pakiet subskrypcyjny."
        )

    return True