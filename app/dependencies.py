# app/dependencies.py
from typing import Optional
import jwt
from fastapi import Depends, Request, HTTPException, status
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_token_from_request, verify_active_access
from app.db.session import get_db
from app.db.models import User


async def get_current_user_optional(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Pobiera zalogowanego użytkownika z ciasteczka lub nagłówka Bearer.
    
    - Zwraca obiekt User, jeśli token jest prawidłowy.
    - Zwraca None, jeśli brak tokena lub jest nieprawidłowy (obsługa gości).
    Nie rzuca wyjątku HTTP 401.
    """
    token = get_token_from_request(request)
    if not token:
        return None

    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            return None
        user_id = int(user_id_str)
    except (jwt.PyJWTError, ValueError):
        return None

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalars().first()

    return user


async def get_current_user_required(
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> User:
    """
    Wymaga aktywnego zalogowania.
    Jeśli brak sesji lub użytkownik nie istnieje, rzuca wyjątek HTTP 401.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wymagane zalogowanie, aby uzyskać dostęp.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


async def get_current_active_user(
    current_user: User = Depends(get_current_user_required)
) -> User:
    """
    Wymaga zalogowania ORAZ aktywnego dostępu/pakietu subskrypcyjnego.
    Korzysta z funkcji verify_active_access z pliku security.py.
    """
    verify_active_access(current_user)
    return current_user