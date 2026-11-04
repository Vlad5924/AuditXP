"""Заполнение базы демонстрационными данными (python -m app.seed)."""
import asyncio
import logging
import random
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.models import Department, Risk, Role, User
from app.domain.enums import RiskStatus, RoleName
from app.etl.erp_client import (
    DEPARTMENTS,
    ErpClient,
    MockErpSource,
    month_scope,
)
from app.etl.module import EtlIntegrationModule
from app.ml.strategies import MLAnomalyDetector
from app.repository.risk_repository import RiskRepository
from app.services.report_service import ReportService
from app.services.risk_calculation import RiskCalculationService
from app.services.risk_service import RiskService

log = logging.getLogger("auditxp.seed")

ROLES = {
    RoleName.AUDITOR: ["etl:run", "risks:detect", "risks:update",
                       "reports:create"],
    RoleName.CHIEF: ["etl:run", "risks:detect", "risks:update",
                     "risks:delete", "reports:create", "reports:approve",
                     "audit:read"],
    RoleName.ADMIN: ["users:manage", "audit:read"],
}
USERS = (
    ("zhdanko", "Жданько В.И.", "v.zhdanko@goldberg-soft.by",
     RoleName.AUDITOR, "Auditor2026"),
    ("litvinova", "Литвинова Е.С.", "e.litvinova@goldberg-soft.by",
     RoleName.AUDITOR, "Auditor2026"),
    ("kovalchuk", "Ковальчук О.П.", "o.kovalchuk@goldberg-soft.by",
     RoleName.CHIEF, "Chief2026"),
    ("admin", "Савицкий Д.Н.", "d.savitsky@goldberg-soft.by",
     RoleName.ADMIN, "Admin2026"),
)
MANAGERS = {"Реализация": "Орлов С.В.", "Закупки": "Гриневич Т.А.",
            "Логистика": "Мельник П.Д.", "Производство": "Бондарь И.К.",
            "Розница": "Ясинская Н.Л.", "Финансы": "Шульга Р.М."}
MONTHS = ((2026, 7), (2026, 8), (2026, 9), (2026, 10))


async def seed_base(session: AsyncSession) -> dict[str, User]:
    roles = {name: Role(name=name, permissions=perms)
             for name, perms in ROLES.items()}
    session.add_all(roles.values())
    users = {}
    for login, name, email, role, password in USERS:
        users[login] = User(login=login, full_name=name, email=email,
                            role=roles[role],
                            password_hash=hash_password(password))
    session.add_all(users.values())
    session.add_all(Department(name=n, manager_name=MANAGERS.get(n))
                    for n in DEPARTMENTS)
    await session.commit()
    return users


async def _process(session, risk_ids, auditor, rng, share_done) -> None:
    service = RiskService(session)
    for risk_id in risk_ids:
        roll = rng.random()
        if roll > share_done + 0.2:
            continue
        await service.transition(risk_id, "assess", auditor)
        if roll > share_done:
            continue
        if rng.random() < 0.18:
            await service.transition(risk_id, "dismiss", auditor,
                                     comment="Операция подтверждена "
                                             "первичными документами")
            await service.transition(risk_id, "archive", auditor)
            continue
        await service.transition(risk_id, "confirm", auditor)
        await service.transition(
            risk_id, "assign_mitigation", auditor,
            mitigation_plan="Сверка с контрагентом и сторно проводки",
            mitigation_owner="Главный бухгалтер",
            mitigation_due=date(2026, 11, 30))
        if rng.random() < share_done:
            await service.transition(risk_id, "complete_mitigation",
                                     auditor, effectiveness_confirmed=True)


async def seed_demo(session: AsyncSession) -> bool:
    """Создает роли, пользователей, импорт за четыре месяца, риски
    и отчеты. Повторный запуск ничего не меняет."""
    if (await session.execute(select(User.id).limit(1))).first():
        return False
    log.info("Заполнение демонстрационными данными")
    users = await seed_base(session)
    auditor, chief = users["zhdanko"], users["kovalchuk"]
    rng = random.Random(42)
    client = ErpClient(MockErpSource(), delay=0)
    reports = ReportService(session)
    for index, (year, month) in enumerate(MONTHS):
        scope = month_scope(year, month)
        await EtlIntegrationModule(session, client=client) \
            .import_transactions(scope, auditor)
        detector = RiskCalculationService(session, MLAnomalyDetector(),
                                          RiskRepository(session))
        result = await detector.score_transactions(scope.date_from,
                                                   scope.date_to, auditor)
        share = (0.95, 0.9, 0.8, 0.35)[index]
        await _process(session, result.risk_ids, auditor, rng, share)
        title = f"Отчет по рискам за {scope.date_from:%m.%Y}"
        report = await reports.create(title=title,
                                      period_from=scope.date_from,
                                      period_to=scope.date_to, user=auditor)
        await reports.submit(report.id, auditor)
        if month < 10:
            await reports.approve(report.id, chief)
    await reports.create(title="Квартальный отчет по рискам за III квартал",
                         period_from=date(2026, 7, 1),
                         period_to=date(2026, 9, 30), user=auditor)
    old = (await session.execute(
        select(Risk).where(Risk.status == RiskStatus.IDENTIFIED)
        .limit(3))).scalars().all()
    for risk in old:
        risk.created_at = risk.created_at - timedelta(days=35)
    await session.commit()
    return True


async def _main() -> None:
    from app.db.session import dispose_engine, get_sessionmaker, init_models

    await init_models()
    async with get_sessionmaker()() as session:
        created = await seed_demo(session)
    await dispose_engine()
    print("Демо-данные созданы" if created else "База уже заполнена")


if __name__ == "__main__":
    asyncio.run(_main())
