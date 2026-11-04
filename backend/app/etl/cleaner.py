"""Очистка выгрузки ERP от дубликатов и некорректных записей (FR-2.2)."""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.etl.mapping import REQUIRED_FIELDS, FieldMapper


@dataclass
class CleanResult:
    clean: pd.DataFrame
    quarantined: pd.DataFrame
    duplicates: int


DATE_FORMATS = ("%d.%m.%Y %H:%M", "%d.%m.%Y", "ISO8601")


def parse_dates(values: pd.Series) -> pd.Series:
    """Разбирает даты ERP, перебирая допустимые форматы."""
    if pd.api.types.is_datetime64_any_dtype(values):
        return values
    text = values.astype("string")
    result = pd.Series(pd.NaT, index=values.index, dtype="datetime64[ns]")
    pending = text.notna()
    for fmt in DATE_FORMATS:
        if not pending.any():
            break
        parsed = pd.to_datetime(text[pending], format=fmt, errors="coerce")
        result.loc[pending] = parsed
        pending &= result.isna()
    return result


def parse_amount(values: pd.Series) -> pd.Series:
    """Разбирает суммы вида «1 850 000,00» и 1850000.0."""
    if pd.api.types.is_numeric_dtype(values):
        return values.astype(float)
    numeric = pd.to_numeric(values, errors="coerce")
    rest = numeric.isna() & values.notna()
    if not rest.any():
        return numeric
    text = values[rest].astype("string")
    text = text.str.replace(r"[\s\u00a0]", "", regex=True)
    text = text.str.replace(",", ".", regex=False)
    numeric.loc[rest] = pd.to_numeric(text, errors="coerce")
    return numeric


class DataCleaner:
    """Делит записи на корректные и помещаемые в карантин."""

    def __init__(self, mapper: FieldMapper) -> None:
        self.key = mapper.source_of("doc_number")
        self.date = mapper.source_of("transaction_date")
        self.amount = mapper.source_of("amount")
        self.required = [mapper.source_of(f) for f in REQUIRED_FIELDS]

    def split(self, df: pd.DataFrame) -> CleanResult:
        frame = df.copy()
        for col in self.required:
            if col not in frame.columns:
                frame[col] = pd.NA
            if frame[col].dtype == object or frame[col].dtype == "string":
                frame[col] = frame[col].astype("string").str.strip()
                frame[col] = frame[col].replace("", pd.NA)
        dup = frame.duplicated(subset=[self.key], keep="first")
        dup &= frame[self.key].notna()
        duplicates = int(dup.sum())
        frame = frame.loc[~dup]

        amount = parse_amount(frame[self.amount])
        dates = parse_dates(frame[self.date])
        reason = pd.Series("", index=frame.index, dtype=object)
        missing = frame[self.required].isna()
        for col in self.required:
            mask = missing[col] & (reason == "")
            reason[mask] = f"Пустое значение поля «{col}»"
        rules = (
            (amount.isna() & ~missing[self.amount],
             "Неверный формат суммы"),
            (amount.notna() & (amount <= 0),
             "Нулевая или отрицательная сумма"),
            (dates.isna() & ~missing[self.date], "Неверный формат даты"),
        )
        for mask, text in rules:
            reason[mask & (reason == "")] = text

        bad = reason != ""
        clean = frame.loc[~bad].copy()
        clean[self.amount] = amount[~bad].round(2)
        clean[self.date] = dates[~bad]
        quarantined = frame.loc[bad].copy()
        quarantined["_reason"] = reason[bad]
        return CleanResult(clean=clean, quarantined=quarantined,
                           duplicates=duplicates)


def frame_to_payload(row: pd.Series) -> dict:
    """Готовит строку карантина к сохранению в JSON."""
    payload = {}
    for key, value in row.items():
        if key == "_reason":
            continue
        if value is pd.NA or (isinstance(value, float) and np.isnan(value)):
            payload[str(key)] = None
        else:
            payload[str(key)] = str(value)
    return payload
