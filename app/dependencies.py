# app/dependencies.py
from typing import Optional
import uuid
import jwt
from fastapi import Depends, Request, HTTPException, status
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_token_from_request, verify_active_access
from app.db.session import get_db
from app.models.db_models import User


async def get_current_user_optional(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Pobiera zalogowanego użytkownika z ciasteczka lub nagłówka Bearer.
    Jesli e-mail znajduje się na liście ADMIN_EMAILS, dynamicznie przyznaje
    uprawnienia administratora w obiekcie sesji.
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
        if not user_id_str:
            return None

        # Konwersja na UUID zgodny z modelem SQLAlchemy
        user_id = uuid.UUID(user_id_str)
    except (jwt.PyJWTError, ValueError):
        return None

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalars().first()

    # Dynamiczne nadawanie uprawnień administratora na podstawie config.py
    if user and user.email:
        admin_emails = [email.strip().lower() for email in getattr(settings, "ADMIN_EMAILS", [])]
        if user.email.strip().lower() in admin_emails:
            user.is_admin = True
            if hasattr(user, "role"):
                user.role = "ADMIN"

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
    Wymaga zalogowania ORAZ aktywnego dostępu.
    Administratorzy i właściciele (is_admin=True lub rola ADMIN/SUPER_ADMIN) 
    otrzymują pełny, nielimitowany dostęp bez sprawdzania subskrypcji.
    """
    role_str = str(getattr(current_user, "role", "")).upper()
    is_admin = getattr(current_user, "is_admin", False)

    # Pełny darmowy dostęp dla administratorów i właścicieli
    if is_admin or role_str in ["ADMIN", "SUPER_ADMIN"]:
        return current_user

    # Domyślne sprawdzanie limitów dla zwykłych użytkowników
    verify_active_access(current_user)
    return current_user