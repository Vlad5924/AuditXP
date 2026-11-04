"""Данные рабочего стола «Обзор» (ЛР6)."""
from collections import Counter
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ImportBatch
from app.domain.enums import OPEN_STATUSES, RiskLevel
from app.repository.risk_repository import RiskRepository
from app.repository.transaction_repository import TransactionRepository


class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def overview(self, date_from: date, date_to: date) -> dict:
        risks = await RiskRepository(self.session).for_period(date_from,
                                                              date_to)
        transactions = await TransactionRepository(
            self.session).count_period(date_from, date_to)
        levels = Counter(r.level for r in risks)
        processed = [r for r in risks if r.status not in OPEN_STATUSES[:2]]
        open_risks = [r for r in risks if r.status in OPEN_STATUSES]
        priority = sorted(open_risks, key=lambda r: (
            r.materiality, float(r.anomaly_score)), reverse=True)[:5]
        departments = Counter(r.transaction.department.name for r in risks)
        weeks: list[dict] = []
        start = date_from
        while start <= date_to:
            end = min(start + timedelta(days=6), date_to)
            count = sum(start <= r.transaction.transaction_date.date() <= end
                        for r in risks)
            weeks.append({"label": f"{start:%d.%m}–{end:%d.%m}",
                          "count": count})
            start = end + timedelta(days=1)
        stmt = select(ImportBatch).order_by(ImportBatch.id.desc()).limit(1)
        last = (await self.session.execute(stmt)).scalars().first()
        total = len(risks) or 1
        return {
            "period_from": date_from, "period_to": date_to,
            "transactions": transactions, "risks": len(risks),
            "critical": levels.get(RiskLevel.CRITICAL, 0),
            "levels": {lvl.value: levels.get(lvl, 0) for lvl in RiskLevel},
            "processed": len(processed),
            "processed_pct": round(100 * len(processed) / total),
            "priority": priority,
            "departments": [{"name": n, "count": c,
                             "share": round(100 * c / total)}
                            for n, c in departments.most_common(5)],
            "weekly": weeks,
            "last_import": last.finished_at if last else None,
        }
