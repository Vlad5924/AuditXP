"""Тесты производительности (pytest -m perf), PER-01–PER-03."""
import time
from types import SimpleNamespace

import numpy as np
import pytest

from app.etl.cleaner import DataCleaner
from app.etl.erp_client import ImportScope, MockErpSource
from app.etl.mapping import FieldMapper
from app.services.risk_calculation import RiskCalculationService
from tests.test_risks import detect

pytestmark = pytest.mark.perf


def test_clean_and_map_million_rows():
    """PT-01. Очистка и маппинг 1 000 000 строк (часть PER-01)."""
    from datetime import date
    frame = MockErpSource(per_day=42_000).generate(
        ImportScope(date(2026, 9, 1), date(2026, 9, 30)))
    assert len(frame) >= 1_000_000
    started = time.perf_counter()
    mapper = FieldMapper()
    result = DataCleaner(mapper).split(frame)
    mapper.map_fields(result.clean)
    elapsed = time.perf_counter() - started
    print(f"\nPT-01 rows={len(frame)} time={elapsed:.2f}s")
    assert elapsed < 120


def test_heatmap_for_twenty_thousand_risks():
    """PT-02. Тепловая карта для 20 000 рисков менее 10 с (PER-03)."""
    rng = np.random.default_rng(5)
    risks = [SimpleNamespace(id=i, code=f"RK-{i}", risk_type="Тест",
                             level="Средний", materiality=int(m),
                             probability=float(p), impact=float(a))
             for i, (p, a, m) in enumerate(zip(
                 rng.uniform(0.15, 0.99, 20_000),
                 rng.lognormal(10, 1.5, 20_000),
                 rng.integers(1, 26, 20_000), strict=True))]
    started = time.perf_counter()
    heat = RiskCalculationService.build_heatmap(risks)
    elapsed = time.perf_counter() - started
    print(f"\nPT-02 risks={heat['total']} time={elapsed:.3f}s")
    assert elapsed < 10


async def test_overview_response_time(client, auditor, session, users,
                                      imported):
    """PT-03. Ответ рабочего стола менее 2 с (PER-02)."""
    await detect(session, users)
    timings = []
    for _ in range(20):
        started = time.perf_counter()
        response = await client.get("/api/v1/dashboard/overview",
                                    headers=auditor)
        timings.append(time.perf_counter() - started)
        assert response.status_code == 200
    p95 = sorted(timings)[int(len(timings) * 0.95) - 1]
    print(f"\nPT-03 p95={p95:.3f}s max={max(timings):.3f}s")
    assert p95 < 2
