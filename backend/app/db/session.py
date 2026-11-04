"""Подключение к СУБД и фабрика асинхронных сессий."""
from collections.abc import AsyncIterator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import PermissionDeniedError
from app.db.base import Base

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def _enable_sqlite_fk(dbapi_connection, _record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


def get_engine() -> AsyncEngine:
    global _engine, _sessionmaker
    if _engine is None:
        settings = get_settings()
        kwargs = {"pool_pre_ping": True}
        if not settings.is_sqlite:
            kwargs.update(pool_size=10, max_overflow=20)
        _engine = create_async_engine(settings.database_url, **kwargs)
        if settings.is_sqlite:
            event.listen(_engine.sync_engine, "connect", _enable_sqlite_fk)
        _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    get_engine()
    assert _sessionmaker is not None
    return _sessionmaker


async def dispose_engine() -> None:
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
    _engine, _sessionmaker = None, None


async def get_session() -> AsyncIterator[AsyncSession]:
    """Зависимость FastAPI, выдающая сессию на время запроса."""
    async with get_sessionmaker()() as session:
        yield session


async def init_models(drop: bool = False) -> None:
    from app.db import models  # noqa: F401  регистрация таблиц

    async with get_engine().begin() as conn:
        if drop:
            await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@event.listens_for(Session, "before_flush")
def _protect_audit_log(session: Session, _ctx, _instances) -> None:
    """Запрещает изменение и удаление записей журнала аудита (AUD-02)."""
    from app.db.models import AuditLog

    changed = [o for o in session.dirty if session.is_modified(o)]
    for obj in changed + list(session.deleted):
        if isinstance(obj, AuditLog):
            raise PermissionDeniedError(
                "Записи журнала аудита нельзя изменять или удалять")
