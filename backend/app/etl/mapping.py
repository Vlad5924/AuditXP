"""Сопоставление полей ERP с моделью данных AuditXP."""
import pandas as pd

DEFAULT_MAPPING: dict[str, str] = {
    "Номер документа": "doc_number",
    "Дата проводки": "transaction_date",
    "Сумма": "amount",
    "Контрагент": "counterparty_info",
    "Счет Дт": "account_debit",
    "Счет Кт": "account_credit",
    "Подразделение": "department",
}
REQUIRED_FIELDS = ("doc_number", "transaction_date", "amount",
                   "counterparty_info", "department")
SYNONYMS: dict[str, tuple[str, ...]] = {
    "doc_number": ("номер документа", "номер", "документ", "doc_number"),
    "transaction_date": ("дата проводки", "дата", "date",
                         "transaction_date"),
    "amount": ("сумма", "сумма byn", "amount", "sum"),
    "counterparty_info": ("контрагент", "counterparty", "поставщик"),
    "account_debit": ("счет дт", "дебет", "дт", "account_debit"),
    "account_credit": ("счет кт", "кредит", "кт", "account_credit"),
    "department": ("подразделение", "отдел", "цфо", "department"),
}


class FieldMapper:
    """Переименовывает и нормализует столбцы выгрузки ERP."""

    def __init__(self, mapping: dict[str, str] | None = None) -> None:
        self.mapping = dict(mapping or DEFAULT_MAPPING)
        missing = set(REQUIRED_FIELDS) - set(self.mapping.values())
        if missing:
            raise ValueError("Не сопоставлены обязательные поля "
                             + ", ".join(sorted(missing)))

    def source_of(self, target: str) -> str | None:
        for source, mapped in self.mapping.items():
            if mapped == target:
                return source
        return None

    @staticmethod
    def suggest(headers: list[str]) -> list[dict]:
        """Предлагает сопоставление столбцов файла полям AuditXP."""
        result = []
        for header in headers:
            norm = header.strip().lower().replace("ё", "е")
            target, status = None, "missing"
            for field, names in SYNONYMS.items():
                if norm in names:
                    target, status = field, "ok"
                    break
                if any(name in norm for name in names):
                    target, status = field, "warning"
            result.append({"source": header, "target": target,
                           "status": status})
        return result

    def map_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Возвращает таблицу в терминах модели AuditXP."""
        frame = df.rename(columns=self.mapping)
        columns = [c for c in self.mapping.values() if c in frame.columns]
        frame = frame[columns].copy()
        for col in ("doc_number", "counterparty_info", "department",
                    "account_debit", "account_credit"):
            if col in frame.columns:
                frame[col] = frame[col].astype("string").str.strip()
        return frame
