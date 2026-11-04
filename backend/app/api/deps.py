"""Зависимости FastAPI: сессия БД, текущий пользователь и роли."""
from collections.abc import Callable

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import (
    AccountLockedError,
    AuthError,
    PermissionDeniedError,
)
from app.core.security import decode_access_token
from app.db.models import User
from app.db.session import get_session

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token",
                              auto_error=False)


async def get_db(session: AsyncSession = Depends(get_session)):
    return session


async def current_user(token: str | None = Depends(oauth2),
                       session: AsyncSession = Depends(get_session)) -> User:
    if not token:
        raise AuthError("Требуется вход в систему")
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise AuthError("Срок действия сессии истек") from None
    except jwt.PyJWTError:
        raise AuthError("Недействительный токен доступа") from None
    user = await session.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise AuthError("Пользователь не найден")
    if user.is_locked:
        raise AccountLockedError("Учетная запись заблокирована")
    return user


def require_roles(*roles: str) -> Callable:
    async def checker(user: User = Depends(current_user)) -> User:
        if user.role_name not in roles:
            raise PermissionDeniedError(
                "Недостаточно прав для выполнения операции")
        return user
    return checker
