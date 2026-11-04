"""Модульные тесты очистки и маппинга выгрузки ERP (FR-2.2)."""
import pandas as pd
import pytest

from app.etl.cleaner import DataCleaner, parse_amount
from app.etl.mapping import FieldMapper


def frame(rows):
    columns = ["Номер документа", "Дата проводки", "Сумма", "Контрагент",
               "Счет Дт", "Счет Кт", "Подразделение"]
    return pd.DataFrame(rows, columns=columns)


GOOD = ["ПП-1", "14.09.2026 10:32", "1 850 000,00", "ООО «ТрансЛогистик»",
        "60", "51", "Логистика"]


def test_duplicates_removed():
    """UT-16. Повторный номер документа удаляется и учитывается."""
    result = DataCleaner(FieldMapper()).split(frame([GOOD, GOOD, GOOD]))
    assert len(result.clean) == 1 and result.duplicates == 2


def test_empty_required_field_quarantined():
    """UT-17. Запись без контрагента помещается в карантин."""
    bad = GOOD.copy()
    bad[0], bad[3] = "ПП-2", "  "
    result = DataCleaner(FieldMapper()).split(frame([GOOD, bad]))
    assert len(result.clean) == 1
    assert result.quarantined["_reason"].iloc[0] == \
        "Пустое значение поля «Контрагент»"


@pytest.mark.parametrize("field, value, reason", [
    (2, "12 3O0,00", "Неверный формат суммы"),
    (2, "-15,00", "Нулевая или отрицательная сумма"),
    (1, "31.02.2026 25:61", "Неверный формат даты")])
def test_invalid_formats_quarantined(field, value, reason):
    """UT-18. Неверные форматы суммы и даты отбраковываются."""
    bad = GOOD.copy()
    bad[0], bad[field] = "ПП-3", value
    result = DataCleaner(FieldMapper()).split(frame([bad]))
    assert result.clean.empty
    assert result.quarantined["_reason"].iloc[0] == reason


def test_amount_parsing():
    """UT-19. Сумма с пробелами разрядов и запятой разбирается."""
    parsed = parse_amount(pd.Series(["1 850 000,00", "12.5", 7]))
    assert parsed.tolist() == [1_850_000.0, 12.5, 7.0]


def test_mapping_and_suggestions():
    """UT-20. Поля ERP сопоставляются модели AuditXP."""
    mapped = FieldMapper().map_fields(frame([GOOD]))
    assert {"doc_number", "amount", "department"} <= set(mapped.columns)
    hints = {h["source"]: h["status"] for h in FieldMapper.suggest(
        ["Номер документа", "Сумма платежа", "Комментарий"])}
    assert hints == {"Номер документа": "ok", "Сумма платежа": "warning",
                     "Комментарий": "missing"}
    with pytest.raises(ValueError):
        FieldMapper({"Сумма": "amount"})
