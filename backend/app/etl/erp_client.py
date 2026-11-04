"""Клиент корпоративной ERP-системы, работающий только на чтение (BR-3)."""
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, timedelta

import httpx
import numpy as np
import pandas as pd

from app.core.errors import ErpUnavailableError
from app.etl.mapping import DEFAULT_MAPPING

log = logging.getLogger("auditxp.etl")

DEPARTMENTS = {
    "Реализация": (9_000, ("62", "90"), 0.26),
    "Закупки": (12_000, ("60", "51"), 0.22),
    "Логистика": (4_000, ("44", "60"), 0.16),
    "Производство": (7_000, ("20", "10"), 0.14),
    "Розница": (1_500, ("50", "90"), 0.14),
    "Финансы": (25_000, ("51", "66"), 0.08),
}
COUNTERPARTIES = (
    "ООО «ТрансЛогистик»", "ОАО «МинскСтанкоСервис»", "ЗАО «БелТехСнаб»",
    "ООО «АгроПромТорг»", "ООО «СтройИнвестГрупп»", "ЧУП «ПолиПакПлюс»",
    "ООО «ТехноМаркет Бел»", "ОДО «ЭнергоКомплект»", "ООО «ФинКонсалт»",
    "ООО «МеталлТрейд»", "ОАО «ГродноХимПром»", "ООО «БелАвтоДеталь»",
    "ООО «ОфисЛайн»", "ЗАО «СеверЛес»", "ООО «ДатаСервис»",
    "ООО «МедТехника»", "ИП Ковалев А.С.", "ООО «ПромЭлектро»",
)
RARE_COUNTERPARTIES = (
    "ООО «Вектор-777»", "ИП Сидоренко П.П.", "ООО «Альфа Ресурс»",
    "ООО «КонсалтПлюс Онлайн»", "ООО «Гранд-Импорт»",
)


@dataclass
class ImportScope:
    date_from: date
    date_to: date
    departments: list[str] | None = None


@dataclass
class MockErpSource:
    """Демонстрационный источник, имитирующий REST API ERP."""

    per_day: int = 90
    seed: int = 2026
    fail_times: int = 0
    calls: list[str] = field(default_factory=list)
    _failed: int = 0
    _cache: dict = field(default_factory=dict)

    def ping(self) -> None:
        self.calls.append("GET /health")
        if self._failed < self.fail_times:
            self._failed += 1
            raise ConnectionError("ERP не отвечает")

    def fetch_page(self, scope: ImportScope, page: int,
                   size: int) -> pd.DataFrame:
        self.calls.append(f"GET /transactions?page={page}")
        key = (scope.date_from, scope.date_to,
               tuple(scope.departments or ()))
        if key not in self._cache:
            self._cache[key] = self.generate(scope)
        data = self._cache[key]
        return data.iloc[page * size:(page + 1) * size]

    def generate(self, scope: ImportScope) -> pd.DataFrame:
        rng = np.random.default_rng(self.seed + scope.date_from.toordinal())
        days = pd.date_range(scope.date_from, scope.date_to, freq="D")
        weights = np.where(days.weekday >= 5, 0.25, 1.0)
        counts = rng.poisson(self.per_day * weights)
        day = np.repeat(days.values, counts)
        n = len(day)
        names = [d for d in DEPARTMENTS
                 if not scope.departments or d in scope.departments]
        probs = np.array([DEPARTMENTS[d][2] for d in names])
        dept = rng.choice(names, size=n, p=probs / probs.sum())
        scale = np.array([DEPARTMENTS[d][0] for d in dept], dtype=float)
        amount = rng.lognormal(np.log(scale), 0.7)
        minutes = np.clip(rng.normal(13 * 60, 150, n), 8 * 60, 19 * 60 + 50)
        weights_cp = 1.0 / np.arange(1, len(COUNTERPARTIES) + 1)
        cp = rng.choice(COUNTERPARTIES, size=n,
                        p=weights_cp / weights_cp.sum()).astype(object)

        big = rng.random(n) < 0.006
        amount[big] *= rng.uniform(15, 60, big.sum())
        night = rng.random(n) < 0.008
        minutes[night] = rng.uniform(60, 300, night.sum())
        rare = rng.random(n) < 0.004
        cp[rare] = rng.choice(RARE_COUNTERPARTIES, size=rare.sum())

        stamp = (pd.to_datetime(day)
                 + pd.to_timedelta(minutes.astype(int), unit="m"))
        prefix = scope.date_from.strftime("%y%m")
        frame = pd.DataFrame({
            "Номер документа": [f"ПП-{prefix}-{i:07d}" for i in range(n)],
            "Дата проводки": stamp.strftime("%d.%m.%Y %H:%M"),
            "Сумма": np.round(amount, 2),
            "Контрагент": cp,
            "Счет Дт": [DEPARTMENTS[d][1][0] for d in dept],
            "Счет Кт": [DEPARTMENTS[d][1][1] for d in dept],
            "Подразделение": dept,
        })
        frame = self._inject_defects(frame, rng, prefix)
        return frame.reset_index(drop=True)

    @staticmethod
    def _inject_defects(frame: pd.DataFrame, rng, prefix: str):
        n = len(frame)
        doubles = frame.sample(frac=0.005, random_state=int(rng.integers(1e6)))
        doubles = doubles.assign(**{"Номер документа": [
            f"ПП-{prefix}-Д{i:06d}" for i in range(len(doubles))]})
        exact = frame.sample(frac=0.003, random_state=int(rng.integers(1e6)))
        frame = pd.concat([frame, doubles, exact], ignore_index=True)
        frame["Сумма"] = frame["Сумма"].astype(object)
        empty = rng.choice(len(frame), size=max(1, n // 250), replace=False)
        cols = rng.choice(["Сумма", "Контрагент", "Подразделение"],
                          size=len(empty))
        for idx, col in zip(empty, cols, strict=True):
            frame.at[idx, col] = None
        bad = rng.choice(len(frame), size=max(1, n // 1000), replace=False)
        frame.loc[bad, "Сумма"] = "12 3O0,00"
        order = rng.permutation(len(frame))
        return frame.iloc[order]


class HttpErpSource:
    """Источник данных ERP по HTTPS REST API (SI-01)."""

    def __init__(self, base_url: str, token: str, timeout: float = 30):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        self._http = httpx.Client(base_url=base_url, headers=headers,
                                  timeout=timeout, verify=True)

    def _get(self, path: str, **params) -> httpx.Response:
        response = self._http.get(path, params=params)
        response.raise_for_status()
        return response

    def ping(self) -> None:
        self._get("/health")

    def fetch_page(self, scope: ImportScope, page: int,
                   size: int) -> pd.DataFrame:
        payload = self._get(
            "/transactions", date_from=scope.date_from.isoformat(),
            date_to=scope.date_to.isoformat(), page=page, page_size=size,
            departments=",".join(scope.departments or [])).json()
        return pd.DataFrame(payload.get("items", []))


class ErpClient:
    """Подключение к ERP с повторными попытками (AVA-02)."""

    def __init__(self, source, attempts: int = 3, delay: float = 1.0,
                 page_size: int = 5000,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        self.source = source
        self.attempts = attempts
        self.delay = delay
        self.page_size = page_size
        self.sleep = sleep
        self.connected = False

    def connect(self) -> None:
        for attempt in range(1, self.attempts + 1):
            try:
                self.source.ping()
                self.connected = True
                return
            except (ConnectionError, OSError, httpx.HTTPError) as exc:
                log.warning("ERP попытка %s из %s неуспешна (%s)",
                            attempt, self.attempts, exc)
                if attempt < self.attempts:
                    self.sleep(self.delay * 2 ** (attempt - 1))
        raise ErpUnavailableError(
            f"ERP недоступна после {self.attempts} попыток подключения")

    def fetch_transactions(self, scope: ImportScope) -> pd.DataFrame:
        if not self.connected:
            self.connect()
        frames, page = [], 0
        while True:
            chunk = self.source.fetch_page(scope, page, self.page_size)
            if chunk is None or len(chunk) == 0:
                break
            frames.append(chunk)
            if len(chunk) < self.page_size:
                break
            page += 1
        if not frames:
            return pd.DataFrame(columns=list(DEFAULT_MAPPING))
        return pd.concat(frames, ignore_index=True)


def month_scope(year: int, month: int) -> ImportScope:
    start = date(year, month, 1)
    nxt = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    return ImportScope(start, nxt - timedelta(days=1))


def default_source(settings):
    if settings.erp_mode == "http":
        return HttpErpSource(settings.erp_base_url, settings.erp_token)
    return MockErpSource()


