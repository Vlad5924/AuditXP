"""Формирует демонстрационную выгрузку ERP в формате CSV.

Запуск из каталога backend
    python -m scripts.make_sample 2026-11-01 2026-11-03
"""
import sys
from datetime import date
from pathlib import Path

from app.etl.erp_client import ImportScope, MockErpSource

TARGET = Path(__file__).resolve().parents[2] / "samples"


def main(date_from: str, date_to: str) -> Path:
    scope = ImportScope(date.fromisoformat(date_from),
                        date.fromisoformat(date_to))
    frame = MockErpSource(seed=2026).generate(scope)
    frame = frame.rename(columns={"Сумма": "Сумма проводки",
                                  "Подразделение": "ЦФО"})
    frame["Сумма проводки"] = frame["Сумма проводки"].map(
        lambda v: f"{v:.2f}".replace(".", ",") if isinstance(v, float)
        else v)
    frame["Комментарий"] = "Выгрузка из ERP"
    TARGET.mkdir(exist_ok=True)
    path = TARGET / f"erp_export_{date_from}_{date_to}.csv"
    frame.to_csv(path, sep=";", index=False, encoding="utf-8-sig")
    return path


if __name__ == "__main__":
    args = sys.argv[1:] or ["2026-11-01", "2026-11-03"]
    print(main(*args))
