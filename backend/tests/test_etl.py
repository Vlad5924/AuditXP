"""Интеграционные тесты модуля ETL (UC-2, FR-2.1–FR-2.3, AVA-02)."""
import itertools
import json

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.errors import BusinessError, ErpUnavailableError
from app.db.models import ErpTransaction, ImportBatch, Notification
from app.domain.enums import ImportStatus
from app.etl.erp_client import ErpClient, MockErpSource
from app.etl.module import EtlIntegrationModule
from app.repository.transaction_repository import TransactionRepository
from tests.conftest import SCOPE, run_import


async def count(session, model):
    return (await session.execute(select(func.count(model.id)))).scalar()


async def test_import_loads_clean_rows(session, users):
    """IT-01. Импорт загружает очищенные записи и ведет журнал."""
    result, _ = await run_import(session, users["zhdanko"])
    assert result.rows_loaded > 900
    assert result.duplicates > 0 and result.rows_quarantined > 0
    assert result.status == ImportStatus.WARNING
    assert await count(session, ErpTransaction) == result.rows_loaded
    batch = await session.get(ImportBatch, result.batch_id)
    assert batch.rows_total == result.rows_total


async def test_reimport_is_idempotent(session, users):
    """IT-02. Повторный импорт не создает дубликатов в БД."""
    first, _ = await run_import(session, users["zhdanko"])
    second, _ = await run_import(session, users["zhdanko"])
    assert second.rows_loaded == 0
    assert second.skipped_existing == first.rows_loaded
    assert await count(session, ErpTransaction) == first.rows_loaded


async def test_erp_unavailable_after_three_attempts(session, users):
    """IT-03. Три попытки подключения, затем ошибка и уведомление."""
    with pytest.raises(ErpUnavailableError):
        await run_import(session, users["zhdanko"], fail_times=5)
    batch = (await session.execute(select(ImportBatch))).scalars().one()
    assert batch.status == ImportStatus.FAILED
    assert await count(session, Notification) == 1


async def test_erp_recovers_on_third_attempt(session, users):
    """IT-04. Соединение восстанавливается с третьей попытки."""
    source = MockErpSource(per_day=10, fail_times=2)
    client = ErpClient(source, delay=0)
    result = await EtlIntegrationModule(session, client=client) \
        .import_transactions(SCOPE, users["zhdanko"])
    assert result.rows_loaded > 0
    assert source.calls.count("GET /health") == 3


async def test_rollback_on_integrity_error(session, users, monkeypatch):
    """IT-05. Ошибка целостности откатывает всю загрузку."""
    async def broken(self, records):
        await original(self, itertools.islice(records, 10))
        raise IntegrityError("insert", {}, Exception("duplicate key"))
    original = TransactionRepository.bulk_insert
    monkeypatch.setattr(TransactionRepository, "bulk_insert", broken)
    with pytest.raises(BusinessError):
        await run_import(session, users["zhdanko"])
    assert await count(session, ErpTransaction) == 0
    batch = (await session.execute(select(ImportBatch))).scalars().one()
    assert batch.status == ImportStatus.FAILED


async def test_erp_accessed_read_only(session, users):
    """IT-06. К ERP выполняются только запросы GET (BR-3)."""
    _, source = await run_import(session, users["zhdanko"])
    assert source.calls and all(c.startswith("GET ") for c in source.calls)


async def test_import_api_roles(client, auditor, admin):
    """IT-07. Импорт доступен аудитору и запрещен администратору."""
    body = {"date_from": "2026-09-01", "date_to": "2026-09-07"}
    ok = await client.post("/api/v1/etl/imports", json=body, headers=auditor)
    assert ok.status_code == 200 and ok.json()["rows_loaded"] > 0
    denied = await client.post("/api/v1/etl/imports", json=body,
                               headers=admin)
    assert denied.status_code == 403
    journal = await client.get("/api/v1/etl/imports", headers=auditor)
    assert journal.json()[0]["status"] == ImportStatus.WARNING


async def test_file_import_sets_period(session, users):
    """IT-21. Период импорта из файла определяется по датам проводок."""
    source = MockErpSource()
    frame = source.generate(SCOPE)
    module = EtlIntegrationModule(session)
    result = await module.import_frame(frame, users["zhdanko"])
    assert result.period_from == SCOPE.date_from.isoformat()
    assert result.period_to <= SCOPE.date_to.isoformat()
    batch = await session.get(ImportBatch, result.batch_id)
    assert batch.period_from == SCOPE.date_from


def _csv(frame) -> bytes:
    return frame.to_csv(sep=";", index=False).encode("utf-8-sig")


async def test_erp_check_and_preview_api(client, auditor):
    """ST-22. Проверка подключения и предпросмотр выгрузки ERP."""
    check = await client.get("/api/v1/etl/erp/check", headers=auditor)
    assert check.status_code == 200 and check.json()["connected"]
    body = {"date_from": "2026-09-01", "date_to": "2026-09-07"}
    preview = await client.post("/api/v1/etl/erp/preview", json=body,
                                headers=auditor)
    stats = preview.json()["stats"]
    assert stats["total"] == (stats["clean"] + stats["quarantined"]
                              + stats["duplicates"])
    assert len(preview.json()["rows"]) == 8


async def test_file_preview_import_and_quarantine_api(client, auditor):
    """ST-23. Предпросмотр, импорт файла CSV и просмотр карантина."""
    frame = MockErpSource().generate(SCOPE).rename(
        columns={"Сумма": "Сумма проводки"})
    files = {"file": ("export.csv", _csv(frame), "text/csv")}
    preview = await client.post("/api/v1/etl/file/preview", files=files,
                                headers=auditor)
    states = {s["source"]: s for s in preview.json()["suggestions"]}
    assert states["Сумма проводки"]["status"] == "warning"
    mapping = {k: v["target"] for k, v in states.items() if v["target"]}
    result = await client.post("/api/v1/etl/imports/file", files=files,
                               data={"mapping": json.dumps(mapping)},
                               headers=auditor)
    data = result.json()
    assert result.status_code == 200 and data["rows_loaded"] > 0
    assert data["period_from"] == SCOPE.date_from.isoformat()
    quarantine = await client.get(
        f"/api/v1/etl/imports/{data['batch_id']}/quarantine",
        headers=auditor)
    assert len(quarantine.json()) == data["rows_quarantined"]


async def test_unsupported_file_rejected(client, auditor):
    """ST-24. Файл неподдерживаемого формата отклоняется (код 422)."""
    files = {"file": ("export.txt", b"data", "text/plain")}
    response = await client.post("/api/v1/etl/file/preview", files=files,
                                 headers=auditor)
    assert response.status_code == 422
    assert "CSV" in response.json()["detail"]
