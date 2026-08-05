import hashlib
import os
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.db.models import User, UserRole

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


def create_access_token(user_id: int, role: str) -> str:
    """Generuje szyfrowany token JWT dla użytkownika."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": str(user_id),
        "role": role,
        "exp": expire
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Pobiera i weryfikuje użytkownika z tokena Bearer JWT w bazie SQLAlchemy."""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Nieprawidłowy token autoryzacji."
            )
        user_id = int(user_id_str)
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Błąd dekodowania tokena lub token wygasł."
        )

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Konto użytkownika nie istnieje."
        )

    return user


def verify_active_access(user: User) -> bool:
    """Weryfikacja praw dostępu (ADMIN vs zwykły użytkownik)."""
    if user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
        return True

    now_utc = datetime.now(timezone.utc)
    if not user.access_until or user.access_until.replace(tzinfo=timezone.utc) < now_utc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Brak aktywnego dostępu do generowania raportów. Odnów pakiet subskrypcyjny."
        )
    return True