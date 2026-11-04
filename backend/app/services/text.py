"""Очистка пользовательского текста от разметки (SEC-03)."""
import re

TAG_RE = re.compile(r"<[^>]*>")
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def clean_text(value: str | None, limit: int = 2000) -> str | None:
    """Удаляет HTML-теги и управляющие символы из комментария."""
    if value is None:
        return None
    text = CONTROL_RE.sub("", TAG_RE.sub("", value)).strip()
    return text[:limit] or None
