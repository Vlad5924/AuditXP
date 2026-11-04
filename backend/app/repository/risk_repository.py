"""Репозиторий рисков (паттерн «Репозиторий», ЛР8)."""
from abc import ABC, abstractmethod
from datetime import date, datetime

import pandas as pd
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.db.models import Department, ErpTransaction, Risk
from app.domain.enums import OPEN_STATUSES, RiskLevel
from app.repository.transaction_repository import period_bounds


class IRiskRepository(ABC):
    """Абстракция хранилища, от которой зависит сервис расчета рисков."""

    @abstractmethod
    async def get_transactions(self, date_from: date,
                               date_to: date) -> pd.DataFrame: ...

    @abstractmethod
    async def existing_transaction_ids(self, ids) -> set[int]: ...

    @abstractmethod
    async def save_all(self, risks: list[Risk]) -> None: ...


class RiskRepository(IRiskRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_transactions(self, date_from: date,
                               date_to: date) -> pd.DataFrame:
        start, end = period_bounds(date_from, date_to)
        stmt = (select(ErpTransaction.id, ErpTransaction.doc_number,
                       ErpTransaction.department_id,
                       Department.name.label("department"),
                       ErpTransaction.transaction_date,
                       ErpTransaction.amount,
                       ErpTransaction.counterparty_info)
                .join(Department)
                .where(ErpTransaction.transaction_date >= start,
                       ErpTransaction.transaction_date < end)
                .order_by(ErpTransaction.id))
        rows = (await self.session.execute(stmt)).all()
        columns = ["id", "doc_number", "department_id", "department",
                   "transaction_date", "amount", "counterparty_info"]
        return pd.DataFrame(rows, columns=columns)

    async def existing_transaction_ids(self, ids) -> set[int]:
        ids = [int(i) for i in ids]
        found: set[int] = set()
        for i in range(0, len(ids), 5000):
            stmt = select(Risk.transaction_id).where(
                Risk.transaction_id.in_(ids[i:i + 5000]))
            found.update((await self.session.execute(stmt)).scalars())
        return found

    async def save_all(self, risks: list[Risk]) -> None:
        self.session.add_all(risks)
        await self.session.flush()

    async def get(self, risk_id: int) -> Risk:
        risk = await self.session.get(Risk, risk_id)
        if risk is None:
            raise NotFoundError(f"Риск {risk_id} не найден")
        return risk

    def _filtered(self, *, status=None, level=None, department=None,
                  q=None, date_from=None, date_to=None):
        stmt = (select(Risk).join(Risk.transaction)
                .join(ErpTransaction.department))
        if status == "open":
            stmt = stmt.where(Risk.status.in_(OPEN_STATUSES))
        elif status:
            stmt = stmt.where(Risk.status == status)
        if level:
            stmt = stmt.where(Risk.level == level)
        if department:
            stmt = stmt.where(Department.name == department)
        if date_from and date_to:
            start, end = period_bounds(date_from, date_to)
            stmt = stmt.where(ErpTransaction.transaction_date >= start,
                              ErpTransaction.transaction_date < end)
        if q:
            pattern = f"%{q.strip()}%"
            stmt = stmt.where(or_(
                Risk.risk_type.ilike(pattern),
                Risk.description.ilike(pattern),
                ErpTransaction.counterparty_info.ilike(pattern),
                ErpTransaction.doc_number.ilike(pattern)))
        return stmt

    async def search(self, *, limit: int = 50, offset: int = 0,
                     **filters) -> tuple[list[Risk], int]:
        stmt = self._filtered(**filters)
        total = (await self.session.execute(
            select(func.count()).select_from(stmt.subquery()))).scalar_one()
        stmt = stmt.order_by(Risk.materiality.desc(),
                             Risk.anomaly_score.desc(), Risk.id)
        items = (await self.session.execute(
            stmt.limit(limit).offset(offset))).scalars().unique().all()
        return list(items), int(total)

    async def for_period(self, date_from: date, date_to: date) -> list[Risk]:
        stmt = self._filtered(date_from=date_from, date_to=date_to)
        return list((await self.session.execute(stmt)).scalars().unique())

    async def stale_critical(self, older_than: datetime) -> list[Risk]:
        stmt = select(Risk).where(
            Risk.level == RiskLevel.CRITICAL,
            Risk.status.in_(OPEN_STATUSES[:2]),
            Risk.created_at < older_than, Risk.escalated_at.is_(None))
        return list((await self.session.execute(stmt)).scalars().unique())
