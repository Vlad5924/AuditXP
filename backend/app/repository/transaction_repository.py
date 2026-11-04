"""Доступ к транзакциям ERP, подразделениям и карантину."""
from collections.abc import Iterable
from datetime import date, datetime, time, timedelta

import pandas as pd
from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Department, ErpTransaction, QuarantineRecord
from app.etl.cleaner import frame_to_payload

CHUNK = 5000


def period_bounds(date_from: date, date_to: date) -> tuple[datetime,
                                                           datetime]:
    """Полуинтервал [начало первого дня; начало следующего за последним)."""
    return (datetime.combine(date_from, time.min),
            datetime.combine(date_to + timedelta(days=1), time.min))


class TransactionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def department_map(self, names) -> dict[str, int]:
        names = {str(n) for n in names if n}
        rows = (await self.session.execute(select(Department))).scalars()
        known = {d.name: d.id for d in rows}
        for name in sorted(names - known.keys()):
            dept = Department(name=name)
            self.session.add(dept)
            await self.session.flush()
            known[name] = dept.id
        return known

    async def existing_doc_numbers(self, numbers) -> set[str]:
        numbers = list(numbers)
        found: set[str] = set()
        for i in range(0, len(numbers), CHUNK):
            part = numbers[i:i + CHUNK]
            stmt = select(ErpTransaction.doc_number).where(
                ErpTransaction.doc_number.in_(part))
            found.update((await self.session.execute(stmt)).scalars())
        return found

    async def bulk_insert(self, records: Iterable[dict]) -> int:
        """Пакетная вставка порциями по 5 000 строк."""
        total, chunk = 0, []
        for record in records:
            chunk.append(record)
            if len(chunk) == CHUNK:
                await self.session.execute(insert(ErpTransaction), chunk)
                total, chunk = total + len(chunk), []
        if chunk:
            await self.session.execute(insert(ErpTransaction), chunk)
            total += len(chunk)
        return total

    async def add_quarantine(self, batch_id: int,
                             frame: pd.DataFrame) -> int:
        rows = [{"batch_id": batch_id, "reason": row["_reason"],
                 "doc_number": row.get("Номер документа"),
                 "payload": frame_to_payload(row)}
                for _, row in frame.iterrows()]
        for row in rows:
            if row["doc_number"] is not None and pd.isna(row["doc_number"]):
                row["doc_number"] = None
        if rows:
            await self.session.execute(insert(QuarantineRecord), rows)
        return len(rows)

    async def count_period(self, date_from: date, date_to: date) -> int:
        start, end = period_bounds(date_from, date_to)
        stmt = select(func.count(ErpTransaction.id)).where(
            ErpTransaction.transaction_date >= start,
            ErpTransaction.transaction_date < end)
        return int((await self.session.execute(stmt)).scalar_one())
