"""Управление учетными записями и ролями (UC-7, FR-7.1, FR-7.2)."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessError
from app.core.security import hash_password, validate_password_policy
from app.db.models import User
from app.repository.audit_repository import AuditRepository
from app.repository.user_repository import UserRepository


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.audit = AuditRepository(session)

    async def create(self, *, login: str, full_name: str, email: str,
                     password: str, role: str, actor: User) -> User:
        validate_password_policy(password)
        login, email = login.strip().lower(), email.strip().lower()
        if await self.users.by_login(login):
            raise BusinessError(f"Логин «{login}» уже занят")
        if await self.users.by_email(email):
            raise BusinessError(f"Почта «{email}» уже используется")
        role_obj = await self.users.role(role)
        user = User(login=login, full_name=full_name.strip(), email=email,
                    password_hash=hash_password(password), role=role_obj)
        self.session.add(user)
        await self.session.flush()
        self._log(actor, "CREATE", user, f"Роль {role}")
        await self.session.commit()
        return user

    async def update(self, user_id: int, *, actor: User,
                     full_name: str | None = None, email: str | None = None,
                     role: str | None = None) -> User:
        user = await self.users.get(user_id)
        if full_name:
            user.full_name = full_name.strip()
        if email:
            user.email = email.strip().lower()
        if role and role != user.role_name:
            user.role = await self.users.role(role)
            self._log(actor, "ROLE", user, f"Назначена роль {role}")
        self._log(actor, "UPDATE", user)
        await self.session.commit()
        return user

    async def set_locked(self, user_id: int, locked: bool,
                         actor: User) -> User:
        user = await self.users.get(user_id)
        if user.id == actor.id and locked:
            raise BusinessError("Нельзя заблокировать собственную запись")
        user.is_locked = locked
        user.failed_attempts = 0
        self._log(actor, "LOCK" if locked else "UNLOCK", user)
        await self.session.commit()
        return user

    async def deactivate(self, user_id: int, actor: User) -> User:
        """Учетная запись не удаляется физически, чтобы сохранить
        связь с журналом аудита (BR-10, BR-11)."""
        user = await self.users.get(user_id)
        if user.id == actor.id:
            raise BusinessError("Нельзя удалить собственную запись")
        user.is_active = False
        self._log(actor, "DELETE", user, "Запись деактивирована")
        await self.session.commit()
        return user

    def _log(self, actor: User, action: str, user: User,
             details: str | None = None) -> None:
        self.audit.add(user_id=actor.id, table_name="users", action=action,
                       record_id=user.id, details=details or user.login)
