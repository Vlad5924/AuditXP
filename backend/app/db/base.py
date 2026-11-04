"""Декларативная база ORM-моделей."""
from datetime import UTC, datetime

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase

JsonType = JSON().with_variant(JSONB(), "postgresql")


def utcnow() -> datetime:
    """Текущее время UTC без часового пояса (единый формат хранения)."""
    return datetime.now(UTC).replace(tzinfo=None)


class Base(DeclarativeBase):
    """Базовый класс всех таблиц AuditXP."""
