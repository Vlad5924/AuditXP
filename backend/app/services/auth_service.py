"""Аутентификация, блокировка и восстановление пароля (UC-1)."""
import asyncio
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AccountLockedError, AuthError, BusinessError
from app.core.security import (
    create_access_token,
    generate_reset_token,
    hash_password,
    hash_reset_token,
    validate_password_policy,
    verify_password,
)
from app.db.base import utcnow
from app.db.models import User
from app.domain.enums import RoleName
from app.repository.audit_repository import AuditRepository
from app.repository.user_repository import UserRepository
from app.services.notification_service import NotificationService


class AuthService:
    def __init__(self, session: AsyncSession,
                 notifier: NotificationService | None = None) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.audit = AuditRepository(session)
        self.notifier = notifier or NotificationService(session)
        self.settings = get_settings()

    async def authenticate(self, login: str,
                           password: str) -> tuple[User, str]:
        """Проверяет пару логин и пароль (FR-1.1) и блокирует после
        пяти неудачных попыток подряд (FR-1.2)."""
        user = await self.users.by_login(login)
        if user is None or not user.is_active:
            self.audit.add(user_id=None, table_name="users",
                           action="LOGIN_FAILED", details=login[:50])
            await self.session.commit()
            raise AuthError("Неверный логин или пароль")
        if user.is_locked:
            raise AccountLockedError(
                "Учетная запись заблокирована, обратитесь к администратору")
        if not verify_password(password, user.password_hash):
            return await self._register_failure(user)
        user.failed_attempts = 0
        user.last_login_at = utcnow()
        self.audit.add(user_id=user.id, table_name="users", action="LOGIN",
                       record_id=user.id)
        await self.session.commit()
        return user, create_access_token(str(user.id), user.role_name)

    async def _register_failure(self, user: User):
        limit = self.settings.max_failed_logins
        user.failed_attempts += 1
        self.audit.add(user_id=user.id, table_name="users",
                       action="LOGIN_FAILED", record_id=user.id)
        if user.failed_attempts >= limit:
            user.is_locked = True
            self.audit.add(user_id=user.id, table_name="users",
                           action="LOCK", record_id=user.id,
                           details=f"{limit} неудачных попыток входа")
            await self.notifier.notify_role(
                RoleName.ADMIN,
                f"Учетная запись {user.login} заблокирована после "
                f"{limit} неудачных попыток входа")
            await self.session.commit()
            raise AccountLockedError(
                f"Учетная запись заблокирована после {limit} "
                f"неудачных попыток входа")
        await self.session.commit()
        left = limit - user.failed_attempts
        raise AuthError(f"Неверный логин или пароль, осталось попыток {left}")

    async def request_password_reset(self, email: str) -> str | None:
        """Отправляет ссылку восстановления на корпоративную почту
        (FR-1.3). Несуществующий адрес не раскрывается."""
        user = await self.users.by_email(email)
        if user is None or not user.is_active:
            return None
        token, token_hash = generate_reset_token()
        user.reset_token_hash = token_hash
        user.reset_token_expires = utcnow() + timedelta(
            minutes=self.settings.reset_token_minutes)
        await self.notifier.notify(user, "Запрошено восстановление пароля")
        await asyncio.to_thread(
            self.notifier.sender.send, user.email,
            "AuditXP – восстановление пароля",
            f"Для смены пароля перейдите по ссылке /#/reset?token={token}")
        self.audit.add(user_id=user.id, table_name="users",
                       action="PASSWORD_RESET_REQUEST", record_id=user.id)
        await self.session.commit()
        return token

    async def reset_password(self, token: str, new_password: str) -> None:
        validate_password_policy(new_password)
        user = await self.users.by_reset_hash(hash_reset_token(token))
        if user is None or user.reset_token_expires is None \
                or user.reset_token_expires < utcnow():
            raise BusinessError("Ссылка восстановления недействительна")
        user.password_hash = hash_password(new_password)
        user.reset_token_hash = None
        user.reset_token_expires = None
        user.failed_attempts = 0
        user.is_locked = False
        self.audit.add(user_id=user.id, table_name="users",
                       action="PASSWORD_RESET", record_id=user.id)
        await self.session.commit()
