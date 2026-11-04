"""ETL-импорт транзакций из ERP и файлов (UC-2)."""
import asyncio
import io
import json

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import select

from app.api.deps import current_user, get_db, require_roles
from app.api.schemas import ImportIn
from app.core.config import get_settings
from app.core.errors import BusinessError
from app.db.models import ImportBatch, QuarantineRecord
from app.domain.enums import RoleName
from app.etl.cleaner import DataCleaner
from app.etl.erp_client import ErpClient, ImportScope, default_source
from app.etl.mapping import DEFAULT_MAPPING, FieldMapper
from app.etl.module import EtlIntegrationModule

router = APIRouter(prefix="/etl", tags=["ETL-импорт"])
importer = require_roles(RoleName.AUDITOR, RoleName.CHIEF)


def _client() -> ErpClient:
    s = get_settings()
    return ErpClient(default_source(s), attempts=s.erp_retry_attempts,
                     delay=s.erp_retry_delay, page_size=s.erp_page_size)


def _read_file(name: str, content: bytes) -> pd.DataFrame:
    if name.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(content), dtype=str)
    if name.lower().endswith(".csv"):
        text = content.decode("utf-8-sig", errors="replace")
        sep = ";" if text.count(";") > text.count(",") else ","
        return pd.read_csv(io.StringIO(text), sep=sep, dtype=str)
    raise BusinessError("Поддерживаются файлы CSV и XLSX")


def _preview(frame: pd.DataFrame, mapping: dict[str, str]) -> dict:
    mapper = FieldMapper(mapping)
    result = DataCleaner(mapper).split(frame)
    sample = mapper.map_fields(result.clean.head(8))
    return {
        "headers": [str(c) for c in frame.columns],
        "suggestions": FieldMapper.suggest([str(c) for c in frame.columns]),
        "rows": json.loads(sample.to_json(orient="records",
                                          date_format="iso",
                                          force_ascii=False)),
        "stats": {"total": len(frame), "clean": len(result.clean),
                  "quarantined": len(result.quarantined),
                  "duplicates": result.duplicates},
    }


@router.get("/erp/check", summary="Проверка подключения к ERP")
async def erp_check(_=Depends(importer)):
    client = _client()
    await asyncio.to_thread(client.connect)
    return {"connected": client.connected,
            "source": get_settings().erp_mode,
            "base_url": get_settings().erp_base_url}


@router.post("/erp/preview", summary="Предпросмотр выгрузки ERP")
async def erp_preview(data: ImportIn, _=Depends(importer)):
    client = _client()
    scope = ImportScope(data.date_from, data.date_to, data.departments)
    frame = await asyncio.to_thread(client.fetch_transactions, scope)
    return await asyncio.to_thread(_preview, frame, DEFAULT_MAPPING)


@router.post("/imports", summary="Запуск импорта из ERP (FR-2.1–FR-2.3)")
async def run_import(data: ImportIn, user=Depends(importer),
                     session=Depends(get_db)):
    scope = ImportScope(data.date_from, data.date_to, data.departments)
    result = await EtlIntegrationModule(session).import_transactions(scope,
                                                                    user)
    return result.as_dict()


@router.post("/imports/file", summary="Импорт из файла CSV или XLSX")
async def import_file(file: UploadFile = File(...),
                      mapping: str | None = Form(default=None),
                      user=Depends(importer), session=Depends(get_db)):
    frame = _read_file(file.filename or "", await file.read())
    fields = json.loads(mapping) if mapping else DEFAULT_MAPPING
    module = EtlIntegrationModule(session, mapping=fields)
    return (await module.import_frame(frame, user)).as_dict()


@router.post("/file/preview", summary="Предпросмотр файла и маппинг")
async def file_preview(file: UploadFile = File(...),
                       _=Depends(importer)):
    frame = _read_file(file.filename or "", await file.read())
    suggestions = FieldMapper.suggest([str(c) for c in frame.columns])
    mapping = {s["source"]: s["target"] for s in suggestions if s["target"]}
    try:
        return await asyncio.to_thread(_preview, frame, mapping)
    except ValueError as exc:
        raise BusinessError(str(exc)) from None


@router.get("/imports", summary="Журнал импорта")
async def journal(_=Depends(current_user), session=Depends(get_db)):
    stmt = select(ImportBatch).order_by(ImportBatch.id.desc()).limit(50)
    batches = (await session.execute(stmt)).scalars().unique().all()
    return [{"id": b.id, "source": b.source, "status": b.status,
             "period_from": b.period_from, "period_to": b.period_to,
             "started_at": b.started_at, "finished_at": b.finished_at,
             "rows_total": b.rows_total, "rows_loaded": b.rows_loaded,
             "rows_quarantined": b.rows_quarantined,
             "duplicates": b.duplicates,
             "skipped_existing": b.skipped_existing, "message": b.message,
             "user": b.user.full_name if b.user else "Система"}
            for b in batches]


@router.get("/imports/{batch_id}/quarantine", summary="Записи в карантине")
async def quarantine(batch_id: int, _=Depends(current_user),
                     session=Depends(get_db)):
    stmt = (select(QuarantineRecord)
            .where(QuarantineRecord.batch_id == batch_id)
            .order_by(QuarantineRecord.id).limit(500))
    rows = (await session.execute(stmt)).scalars().all()
    return [{"id": r.id, "doc_number": r.doc_number, "reason": r.reason,
             "payload": r.payload} for r in rows]
