"""Доступ к учетным записям и ролям."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.db.models import Role, User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: int) -> User:
        user = await self.session.get(User, user_id)
        if user is None:
            raise NotFoundError(f"Пользователь {user_id} не найден")
        return user

    async def by_login(self, login: str) -> User | None:
        stmt = select(User).where(User.login == login.strip().lower())
        return (await self.session.execute(stmt)).scalars().first()

    async def by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email.strip().lower())
        return (await self.session.execute(stmt)).scalars().first()

    async def by_reset_hash(self, token_hash: str) -> User | None:
        stmt = select(User).where(User.reset_token_hash == token_hash)
        return (await self.session.execute(stmt)).scalars().first()

    async def list_all(self) -> list[User]:
        stmt = select(User).order_by(User.id)
        return list((await self.session.execute(stmt)).scalars().unique())

    async def with_role(self, role_name: str) -> list[User]:
        stmt = (select(User).join(User.role)
                .where(Role.name == role_name, User.is_active.is_(True)))
        return list((await self.session.execute(stmt)).scalars().unique())

    async def role(self, name: str) -> Role:
        stmt = select(Role).where(Role.name == name)
        role = (await self.session.execute(stmt)).scalars().first()
        if role is None:
            raise NotFoundError(f"Роль «{name}» не найдена")
        return role

    async def roles(self) -> list[Role]:
        return list((await self.session.execute(
            select(Role).order_by(Role.id))).scalars())
