"""Журнал аудита: только добавление и чтение (AUD-01, AUD-02)."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def add(self, *, user_id: int | None, table_name: str, action: str,
            record_id: int | None = None, details: str | None = None) -> None:
        self.session.add(AuditLog(user_id=user_id, table_name=table_name,
                                  action=action, record_id=record_id,
                                  details=details))

    async def list_all(self, *, limit: int = 100, offset: int = 0,
                   table_name: str | None = None) -> list[AuditLog]:
        stmt = select(AuditLog).order_by(AuditLog.id.desc())
        if table_name:
            stmt = stmt.where(AuditLog.table_name == table_name)
        stmt = stmt.limit(limit).offset(offset)
        return list((await self.session.execute(stmt)).scalars().unique())
