"""Перечисления предметной области."""
from enum import StrEnum


class RoleName(StrEnum):
    AUDITOR = "Аудитор"
    CHIEF = "Руководитель"
    ADMIN = "Администратор"


class RiskStatus(StrEnum):
    IDENTIFIED = "Выявлен"
    ASSESSED = "Оценен"
    CONFIRMED = "Подтвержден"
    IN_PROGRESS = "В проработке"
    DISMISSED = "Снят"
    CLOSED = "Закрыт"


class RiskLevel(StrEnum):
    LOW = "Низкий"
    MEDIUM = "Средний"
    HIGH = "Высокий"
    CRITICAL = "Критический"


class ReportStatus(StrEnum):
    DRAFT = "Черновик"
    ON_REVIEW = "На проверке"
    RETURNED = "На доработке"
    APPROVED = "Утвержден"


class ImportStatus(StrEnum):
    RUNNING = "Выполняется"
    SUCCESS = "Успешно"
    WARNING = "С предупреждениями"
    FAILED = "Ошибка"


OPEN_STATUSES = (RiskStatus.IDENTIFIED, RiskStatus.ASSESSED,
                 RiskStatus.CONFIRMED, RiskStatus.IN_PROGRESS)
