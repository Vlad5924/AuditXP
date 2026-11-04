"""Конечный автомат жизненного цикла риска (диаграмма состояний ЛР8)."""
from app.core.errors import BusinessError, InvalidTransitionError
from app.domain.enums import RiskStatus as S

TRANSITIONS: dict[tuple[S, str], S] = {
    (S.IDENTIFIED, "assess"): S.ASSESSED,
    (S.ASSESSED, "confirm"): S.CONFIRMED,
    (S.ASSESSED, "dismiss"): S.DISMISSED,
    (S.CONFIRMED, "assign_mitigation"): S.IN_PROGRESS,
    (S.CONFIRMED, "recalculate"): S.ASSESSED,
    (S.IN_PROGRESS, "complete_mitigation"): S.CLOSED,
    (S.DISMISSED, "archive"): S.CLOSED,
}

ACTION_TITLES = {
    "assess": "Оценить",
    "confirm": "Подтвердить",
    "dismiss": "Отклонить",
    "assign_mitigation": "Назначить мероприятие",
    "recalculate": "Пересчитать",
    "complete_mitigation": "Выполнить мероприятие",
    "archive": "Архивировать",
}


def available_actions(status: str) -> list[str]:
    return [action for (state, action) in TRANSITIONS if state == status]


def next_status(status: str, action: str, *, comment: str | None = None,
                mitigation: str | None = None,
                effectiveness_confirmed: bool = False) -> S:
    """Возвращает новое состояние или возбуждает ошибку перехода."""
    key = (S(status), action)
    if key not in TRANSITIONS:
        title = ACTION_TITLES.get(action, action)
        raise InvalidTransitionError(
            f"Переход «{title}» недопустим из состояния «{status}»")
    if action == "dismiss" and not (comment or "").strip():
        raise BusinessError("Для отклонения риска нужен комментарий")
    if action == "assign_mitigation" and not (mitigation or "").strip():
        raise BusinessError("Не указано корректирующее мероприятие")
    if action == "complete_mitigation" and not effectiveness_confirmed:
        raise BusinessError(
            "Риск закрывается только после подтверждения "
            "эффективности мероприятия (BR-13)")
    return TRANSITIONS[key]
