"""Модуль ETL-интеграции с ERP (UC-2, алгоритм ЛР8)."""
import asyncio
import time
from collections.abc import Iterator
from dataclasses import asdict, dataclass

import pandas as pd
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import BusinessError, ErpUnavailableError
from app.db.base import utcnow
from app.db.models import ImportBatch, User
from app.domain.enums import ImportStatus
from app.etl.cleaner import DataCleaner
from app.etl.erp_client import ErpClient, ImportScope, default_source
from app.etl.mapping import FieldMapper
from app.repository.audit_repository import AuditRepository
from app.repository.transaction_repository import TransactionRepository
from app.services.notification_service import NotificationService


def _iso(value) -> str | None:
    return value.isoformat() if value is not None else None


def _text(value) -> str | None:
    return None if value is None or pd.isna(value) else str(value)[:10]


@dataclass
class ImportResult:
    batch_id: int
    status: str
    rows_total: int
    rows_loaded: int
    rows_quarantined: int
    duplicates: int
    skipped_existing: int
    duration_s: float
    message: str
    period_from: str | None = None
    period_to: str | None = None

    def as_dict(self) -> dict:
        return asdict(self)


class EtlIntegrationModule:
    def __init__(self, session: AsyncSession,
                 client: ErpClient | None = None,
                 mapping: dict[str, str] | None = None,
                 notifier: NotificationService | None = None) -> None:
        settings = get_settings()
        self.session = session
        self.client = client or ErpClient(
            default_source(settings), attempts=settings.erp_retry_attempts,
            delay=settings.erp_retry_delay,
            page_size=settings.erp_page_size)
        self.mapper = FieldMapper(mapping)
        self.repo = TransactionRepository(session)
        self.audit = AuditRepository(session)
        self.notifier = notifier or NotificationService(session)

    async def import_transactions(self, scope: ImportScope,
                                  user: User | None) -> ImportResult:
        """Импорт транзакций ERP за период с очисткой и откатом."""
        started = time.perf_counter()
        batch_id = await self._open_batch(user, "erp", scope)
        try:
            await asyncio.to_thread(self.client.connect)
            raw = await asyncio.to_thread(self.client.fetch_transactions,
                                          scope)
        except ErpUnavailableError as exc:
            await self._fail(batch_id, user, exc.message)
            raise
        return await self._process(batch_id, raw, user, started)

    async def import_frame(self, raw: pd.DataFrame, user: User | None,
                           source: str = "file") -> ImportResult:
        """Импорт из загруженного файла CSV или XLSX."""
        started = time.perf_counter()
        batch_id = await self._open_batch(user, source, None)
        return await self._process(batch_id, raw, user, started)

    async def _open_batch(self, user, source, scope) -> int:
        batch = ImportBatch(user_id=user.id if user else None,
                            source=source,
                            period_from=scope.date_from if scope else None,
                            period_to=scope.date_to if scope else None)
        self.session.add(batch)
        await self.session.commit()
        return batch.id

    async def _process(self, batch_id: int, raw: pd.DataFrame, user,
                       started: float) -> ImportResult:
        cleaner = DataCleaner(self.mapper)
        result = await asyncio.to_thread(cleaner.split, raw)
        mapped = await asyncio.to_thread(self.mapper.map_fields,
                                         result.clean)
        try:
            departments = await self.repo.department_map(
                mapped["department"].unique())
            existing = await self.repo.existing_doc_numbers(
                mapped["doc_number"].tolist())
            fresh = mapped[~mapped["doc_number"].isin(existing)]
            records = self._records(fresh, departments, batch_id)
            loaded = await self.repo.bulk_insert(records)
            quarantined = await self.repo.add_quarantine(
                batch_id, result.quarantined)
            batch = await self.session.get(ImportBatch, batch_id)
            if batch.period_from is None and len(mapped):
                # для файла период определяется по датам проводок
                dates = mapped["transaction_date"]
                batch.period_from = dates.min().date()
                batch.period_to = dates.max().date()
            batch.rows_total = len(raw)
            batch.rows_loaded = loaded
            batch.rows_quarantined = quarantined
            batch.duplicates = result.duplicates
            batch.skipped_existing = len(mapped) - len(fresh)
            batch.status = (ImportStatus.WARNING if quarantined
                            else ImportStatus.SUCCESS)
            batch.finished_at = utcnow()
            batch.message = (f"Загружено {loaded}, в карантине "
                             f"{quarantined}, дубликатов "
                             f"{result.duplicates}")
            self.audit.add(user_id=user.id if user else None,
                           table_name="erp_transactions", action="IMPORT",
                           record_id=batch_id, details=batch.message)
            if user is not None:
                await self.notifier.notify(user, "Импорт завершен. "
                                           + batch.message)
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            await self._fail(batch_id, user,
                             "Нарушена целостность данных, изменения "
                             "отменены")
            raise BusinessError(
                "Импорт отменен из-за ошибки целостности") from None
        return ImportResult(
            batch_id=batch_id, status=batch.status, rows_total=len(raw),
            rows_loaded=loaded, rows_quarantined=quarantined,
            duplicates=result.duplicates,
            skipped_existing=batch.skipped_existing,
            duration_s=round(time.perf_counter() - started, 3),
            message=batch.message,
            period_from=_iso(batch.period_from),
            period_to=_iso(batch.period_to))

    @staticmethod
    def _records(frame: pd.DataFrame, departments: dict[str, int],
                 batch_id: int) -> Iterator[dict]:
        """Построчно формирует записи для вставки без копии в памяти."""
        now = utcnow()
        dates = pd.to_datetime(frame["transaction_date"]).dt.to_pydatetime()
        for row, stamp in zip(frame.itertuples(index=False), dates,
                              strict=True):
            yield {
                "doc_number": row.doc_number,
                "department_id": departments[row.department],
                "transaction_date": stamp,
                "amount": round(float(row.amount), 2),
                "counterparty_info": str(row.counterparty_info)[:255],
                "account_debit": _text(getattr(row, "account_debit", None)),
                "account_credit": _text(getattr(row, "account_credit",
                                                None)),
                "batch_id": batch_id, "imported_at": now}

    async def _fail(self, batch_id: int, user, message: str) -> None:
        batch = await self.session.get(ImportBatch, batch_id)
        batch.status = ImportStatus.FAILED
        batch.finished_at = utcnow()
        batch.message = message
        self.audit.add(user_id=user.id if user else None,
                       table_name="erp_transactions",
                       action="IMPORT_FAILED", record_id=batch_id,
                       details=message)
        if user is not None:
            await self.notifier.notify(user, "Импорт не выполнен. "
                                       + message)
        await self.session.commit()
