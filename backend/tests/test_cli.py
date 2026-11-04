"""Интеграционные тесты служебных команд установки (ЛР11)."""
from sqlalchemy import func, select

from app import cli
from app.db.models import Department, Role


async def test_init_db_and_create_admin(session):
    """IT-22. Команды init-db и create-admin готовят пустую БД к работе."""
    assert "созданы" in await cli.init_db()
    assert "созданы" in await cli.init_db()
    assert await session.scalar(select(func.count(Role.id))) == 3
    assert await session.scalar(select(func.count(Department.id))) == 6
    created = await cli.create_admin("root", "Администратор системы",
                                     "root@goldberg-soft.by", "Admin2026")
    again = await cli.create_admin("root", "Администратор системы",
                                   "root@goldberg-soft.by", "Admin2026")
    assert "создан" in created and "уже существует" in again
    assert "Пользователей 1" in await cli.check()


def test_cli_rejects_weak_password(capsys):
    """IT-23. Команда create-admin отклоняет слабый пароль (код 1)."""
    code = cli.main(["create-admin", "--email", "root@goldberg-soft.by",
                     "--password", "12345"])
    assert code == 1
    assert "Пароль должен" in capsys.readouterr().err
