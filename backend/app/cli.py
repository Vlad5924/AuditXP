"""Служебные команды установки и сопровождения AuditXP.

Примеры запуска из каталога backend
    python -m app.cli init-db
    python -m app.cli create-admin --login admin --email admin@goldberg-soft.by
    python -m app.cli seed-demo
    python -m app.cli check
"""
import argparse
import asyncio
import getpass
import sys

from sqlalchemy import func, select, text

from app.core.config import get_settings
from app.core.security import hash_password, validate_password_policy
from app.db.models import Department, ErpTransaction, Risk, Role, User
from app.db.session import dispose_engine, get_sessionmaker, init_models
from app.domain.enums import RoleName
from app.etl.erp_client import DEPARTMENTS
from app.seed import MANAGERS, ROLES, seed_demo


async def init_db() -> str:
    """Создает таблицы, роли и справочник подразделений."""
    await init_models()
    async with get_sessionmaker()() as session:
        existing = set((await session.execute(select(Role.name)))
                       .scalars())
        session.add_all(Role(name=name, permissions=perms)
                        for name, perms in ROLES.items()
                        if name not in existing)
        known = set((await session.execute(select(Department.name)))
                    .scalars())
        session.add_all(Department(name=n, manager_name=MANAGERS.get(n))
                        for n in DEPARTMENTS if n not in known)
        await session.commit()
    return "Схема БД, роли и подразделения созданы"


async def create_admin(login: str, full_name: str, email: str,
                       password: str) -> str:
    """Создает учетную запись администратора системы."""
    validate_password_policy(password)
    await init_db()
    async with get_sessionmaker()() as session:
        if (await session.execute(select(User).where(User.login == login))
                ).scalar_one_or_none():
            return f"Пользователь {login} уже существует"
        role = (await session.execute(
            select(Role).where(Role.name == RoleName.ADMIN))).scalar_one()
        session.add(User(login=login, full_name=full_name, email=email,
                         role=role, password_hash=hash_password(password)))
        await session.commit()
    return f"Администратор {login} создан"


async def demo() -> str:
    await init_models()
    async with get_sessionmaker()() as session:
        created = await seed_demo(session)
    return "Демо-данные созданы" if created else "База уже заполнена"


async def check() -> str:
    """Проверяет подключение к БД и выводит объем данных."""
    settings = get_settings()
    async with get_sessionmaker()() as session:
        await session.execute(text("SELECT 1"))
        users = await session.scalar(select(func.count(User.id)))
        rows = await session.scalar(select(func.count(ErpTransaction.id)))
        risks = await session.scalar(select(func.count(Risk.id)))
    engine = settings.database_url.split("://", 1)[0]
    return (f"БД доступна ({engine}). Пользователей {users}, "
            f"проводок {rows}, рисков {risks}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli",
                                     description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init-db", help="создать схему БД и справочники")
    admin = sub.add_parser("create-admin", help="создать администратора")
    admin.add_argument("--login", default="admin")
    admin.add_argument("--full-name", default="Администратор системы")
    admin.add_argument("--email", required=True)
    admin.add_argument("--password", help="если не указан, будет запрошен")
    sub.add_parser("seed-demo", help="заполнить демонстрационными данными")
    sub.add_parser("check", help="проверить подключение к БД")
    args = parser.parse_args(argv)
    if args.command == "init-db":
        job = init_db()
    elif args.command == "create-admin":
        password = args.password or getpass.getpass("Пароль ")
        job = create_admin(args.login, args.full_name, args.email, password)
    elif args.command == "seed-demo":
        job = demo()
    else:
        job = check()

    async def run() -> str:
        try:
            return await job
        finally:
            await dispose_engine()

    try:
        print(asyncio.run(run()))
    except Exception as exc:  # noqa: BLE001  вывод причины для оператора
        print(f"Ошибка {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
