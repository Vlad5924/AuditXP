"""Доступ к отчетам по рискам."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.db.models import AuditReport


class ReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, report_id: int) -> AuditReport:
        report = await self.session.get(AuditReport, report_id)
        if report is None:
            raise NotFoundError(f"Отчет {report_id} не найден")
        return report

    async def list_all(self) -> list[AuditReport]:
        stmt = select(AuditReport).order_by(AuditReport.period_from.desc(),
                                            AuditReport.id.desc())
        return list((await self.session.execute(stmt)).scalars().unique())
