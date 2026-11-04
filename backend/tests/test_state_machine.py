"""Модульные тесты жизненного цикла риска (диаграмма состояний ЛР8)."""
import pytest

from app.core.errors import BusinessError, InvalidTransitionError
from app.domain.enums import RiskStatus as S
from app.domain.state_machine import available_actions, next_status


def test_full_lifecycle_to_closed():
    """UT-11. Выявлен, Оценен, Подтвержден, В проработке, Закрыт."""
    status = next_status(S.IDENTIFIED, "assess")
    status = next_status(status, "confirm")
    status = next_status(status, "assign_mitigation", mitigation="Сверка")
    status = next_status(status, "complete_mitigation",
                         effectiveness_confirmed=True)
    assert status == S.CLOSED


def test_invalid_transition_rejected():
    """UT-12. Подтверждение без оценки недопустимо."""
    with pytest.raises(InvalidTransitionError):
        next_status(S.IDENTIFIED, "confirm")


def test_close_requires_effectiveness():
    """UT-13. Риск закрывается только после подтверждения (BR-13)."""
    with pytest.raises(BusinessError):
        next_status(S.IN_PROGRESS, "complete_mitigation")


def test_dismiss_requires_comment_and_archives():
    """UT-14. Отклонение требует комментария, затем архивирование."""
    with pytest.raises(BusinessError):
        next_status(S.ASSESSED, "dismiss", comment=" ")
    status = next_status(S.ASSESSED, "dismiss", comment="Ложное срабатывание")
    assert next_status(status, "archive") == S.CLOSED


def test_recalculate_returns_to_assessed():
    """UT-15. Пересчет возвращает подтвержденный риск в «Оценен»."""
    assert next_status(S.CONFIRMED, "recalculate") == S.ASSESSED
    assert set(available_actions(S.CONFIRMED)) == {"assign_mitigation",
                                                   "recalculate"}
