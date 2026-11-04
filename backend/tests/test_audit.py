"""Тесты журнала аудита (AUD-01, AUD-02, BR-10)."""
import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.core.errors import PermissionDeniedError
from app.db.models import AuditLog


async def test_actions_are_logged(client, admin, session, imported):
    """ST-14. Вход и импорт фиксируются в журнале (AUD-01)."""
    rows = (await client.get("/api/v1/audit-log", headers=admin)).json()
    actions = {r["action"] for r in rows}
    assert {"LOGIN", "IMPORT"} <= actions


async def test_orm_cannot_modify_log(session, imported):
    """ST-15. Изменение записи журнала через ORM запрещено (AUD-02)."""
    entry = (await session.execute(select(AuditLog))).scalars().first()
    entry.details = "подмена"
    with pytest.raises(PermissionDeniedError):
        await session.flush()
    await session.rollback()


async def test_database_trigger_blocks_changes(session, imported):
    """ST-16. Триггер СУБД запрещает UPDATE и DELETE журнала."""
    for sql in ("UPDATE audit_log SET details = 'x'", "DELETE FROM audit_log"):
        with pytest.raises(DBAPIError):
            await session.execute(text(sql))
        await session.rollback()


async def test_log_api_read_only(client, admin, auditor):
    """ST-17. API не предоставляет удаления, аудитору журнал закрыт."""
    assert (await client.delete("/api/v1/audit-log",
                                headers=admin)).status_code == 405
    assert (await client.get("/api/v1/audit-log",
                             headers=auditor)).status_code == 403
