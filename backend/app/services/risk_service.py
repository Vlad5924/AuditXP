"""Обработка рисков аудитором и руководителем (UC-3, BR-6, BR-9)."""
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import PermissionDeniedError
from app.db.base import utcnow
from app.db.models import Risk, User
from app.domain.enums import RoleName
from app.domain.state_machine import ACTION_TITLES, next_status
from app.repository.audit_repository import AuditRepository
from app.repository.risk_repository import RiskRepository
from app.services.notification_service import NotificationService
from app.services.text import clean_text


class RiskService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = RiskRepository(session)
        self.audit = AuditRepository(session)
        self.notifier = NotificationService(session)

    async def transition(self, risk_id: int, action: str, user: User, *,
                         comment: str | None = None,
                         mitigation_plan: str | None = None,
                         mitigation_owner: str | None = None,
                         mitigation_due: date | None = None,
                         effectiveness_confirmed: bool = False) -> Risk:
        """Переводит риск в новое состояние (verify_risk, ЛР8)."""
        risk = await self.repo.get(risk_id)
        comment = clean_text(comment)
        mitigation_plan = clean_text(mitigation_plan)
        new_status = next_status(
            risk.status, action, comment=comment,
            mitigation=mitigation_plan,
            effectiveness_confirmed=effectiveness_confirmed)
        old_status = risk.status
        risk.status = new_status
        if comment:
            risk.comment = comment
        if action == "assign_mitigation":
            risk.mitigation_plan = mitigation_plan
            risk.mitigation_owner = clean_text(mitigation_owner)
            risk.mitigation_due = mitigation_due
        if action == "complete_mitigation":
            risk.effectiveness_confirmed = True
        if action == "recalculate":
            risk.calculate_level()
        self.audit.add(user_id=user.id, table_name="risks", action="UPDATE",
                       record_id=risk.id,
                       details=f"{ACTION_TITLES[action]}. {old_status} -> "
                               f"{new_status}")
        await self.session.commit()
        return risk

    async def escalate(self, risk_id: int, user: User) -> Risk:
        risk = await self.repo.get(risk_id)
        await self._escalate(risk, f"Эскалация риска {risk.code} "
                                   f"пользователем {user.full_name}")
        self.audit.add(user_id=user.id, table_name="risks",
                       action="ESCALATE", record_id=risk.id)
        await self.session.commit()
        return risk

    async def escalate_stale(self, user: User | None = None) -> int:
        """Эскалирует критические риски без действий более 30 дней."""
        days = get_settings().escalation_days
        stale = await self.repo.stale_critical(utcnow() - timedelta(days))
        for risk in stale:
            await self._escalate(
                risk, f"Риск {risk.code} находится в красной зоне более "
                      f"{days} дней без действий")
        self.audit.add(user_id=user.id if user else None,
                       table_name="risks", action="ESCALATE",
                       details=f"Автоматическая эскалация {len(stale)}")
        await self.session.commit()
        return len(stale)

    async def _escalate(self, risk: Risk, message: str) -> None:
        risk.escalated_at = utcnow()
        await self.notifier.notify_role(RoleName.CHIEF, message,
                                        subject="AuditXP – эскалация риска")

    async def delete(self, risk_id: int, user: User) -> None:
        """Удаление доступно только руководителю службы (BR-9)."""
        if user.role_name != RoleName.CHIEF:
            raise PermissionDeniedError(
                "Удаление риска требует согласования руководителя службы")
        risk = await self.repo.get(risk_id)
        self.audit.add(user_id=user.id, table_name="risks", action="DELETE",
                       record_id=risk.id, details=risk.code)
        await self.session.delete(risk)
        await self.session.commit()
