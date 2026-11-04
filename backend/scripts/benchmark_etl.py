"""Замер требования PER-01 (импорт 1 000 000 строк не дольше 5 мин).

Запуск из каталога backend
    python scripts/benchmark_etl.py --url postgresql+asyncpg://...
"""
import argparse
import asyncio
import json
import os
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


async def run(url: str, per_day: int) -> dict:
    os.environ.update(DATABASE_URL=url, SEED_DEMO="false", BCRYPT_ROUNDS="4")
    from app.db.session import dispose_engine, get_sessionmaker, init_models
    from app.etl.erp_client import ErpClient, ImportScope, MockErpSource
    from app.etl.module import EtlIntegrationModule
    from app.seed import seed_base

    await init_models(drop=True)
    scope = ImportScope(date(2026, 9, 1), date(2026, 9, 30))
    source = MockErpSource(per_day=per_day)
    started = time.perf_counter()
    source.fetch_page(scope, 0, 1)
    generated = time.perf_counter() - started
    async with get_sessionmaker()() as session:
        users = await seed_base(session)
        client = ErpClient(source, delay=0, page_size=50_000)
        module = EtlIntegrationModule(session, client=client)
        started = time.perf_counter()
        result = await module.import_transactions(scope, users["zhdanko"])
        elapsed = time.perf_counter() - started
    await dispose_engine()
    return {"rows_total": result.rows_total,
            "rows_loaded": result.rows_loaded,
            "rows_quarantined": result.rows_quarantined,
            "duplicates": result.duplicates,
            "erp_generation_s": round(generated, 2),
            "import_s": round(elapsed, 2),
            "rows_per_s": round(result.rows_total / elapsed),
            "limit_s": 300, "passed": elapsed <= 300}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--per-day", type=int, default=42_000)
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run(args.url, args.per_day)),
                     ensure_ascii=False, indent=2))
