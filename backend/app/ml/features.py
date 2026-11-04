"""Построение признаков транзакций для алгоритмов скоринга."""
import numpy as np
import pandas as pd

FEATURES = ["log_amount", "dept_z", "weekday", "off_hours", "cp_rarity",
            "dup_count"]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Формирует признаки по столбцам amount, department_id,
    transaction_date и counterparty_info."""
    out = pd.DataFrame(index=df.index)
    amount = df["amount"].astype(float).abs()
    out["log_amount"] = np.log1p(amount)
    grouped = out.groupby(df["department_id"])["log_amount"]
    std = grouped.transform("std").replace(0, np.nan).fillna(1.0)
    out["dept_z"] = (out["log_amount"] - grouped.transform("mean")) / std
    dates = pd.to_datetime(df["transaction_date"])
    out["weekday"] = dates.dt.weekday
    hour = dates.dt.hour
    out["off_hours"] = ((out["weekday"] >= 5) | (hour < 8) | (hour >= 20)
                        ).astype(int)
    freq = df["counterparty_info"].map(
        df["counterparty_info"].value_counts())
    out["cp_rarity"] = 1.0 / freq.astype(float)
    key = (df["counterparty_info"].astype(str) + "|"
           + amount.round(2).astype(str))
    out["dup_count"] = key.map(key.value_counts()).astype(int) - 1
    out["hour"] = hour
    return out


def classify(row: pd.Series) -> tuple[str, str]:
    """Определяет тип риска и пояснение по преобладающему признаку."""
    if row["dup_count"] > 0:
        return ("Дублирование проводки",
                f"Совпадают сумма и контрагент у "
                f"{int(row['dup_count']) + 1} проводок периода")
    if abs(row["dept_z"]) >= 3:
        sigma = f"{abs(row['dept_z']):.1f}".replace(".", ",")
        return ("Аномальная сумма",
                f"Отклонение суммы {sigma} сигма от среднего по "
                f"подразделению")
    if row["off_hours"]:
        return ("Операция в нерабочее время",
                "Проводка выполнена в выходной день или вне 08:00–20:00")
    if row["cp_rarity"] >= 0.5:
        return ("Нетипичный контрагент",
                "Контрагент встречается в периоде не более двух раз")
    return ("Нетипичная операция",
            "Сочетание признаков отличается от типового профиля")
