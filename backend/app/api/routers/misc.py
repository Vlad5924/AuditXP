"""Обзор, уведомления, журнал аудита и проверка состояния."""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text, update

from app.api.deps import current_user, get_db, require_roles
from app.api.schemas import risk_out
from app.core.config import get_settings
from app.core.errors import DB_UNAVAILABLE_ERRORS
from app.db.models import ErpTransaction, Notification
from app.domain.enums import RoleName
from app.repository.audit_repository import AuditRepository
from app.services.dashboard_service import DashboardService

router = APIRouter(tags=["Сервис"])


async def default_period(session) -> tuple[date, date]:
    last = (await session.execute(
        select(func.max(ErpTransaction.transaction_date)))).scalar()
    day = last.date() if last else date.today()
    start = day.replace(day=1)
    end = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    return start, end - timedelta(days=1)


@router.get("/health", summary="Проверка работоспособности")
async def health(session=Depends(get_db)):
    s = get_settings()
    body = {"status": "ok", "database": "ok", "version": s.app_version,
            "environment": s.app_env}
    try:
        await session.execute(text("SELECT 1"))
    except DB_UNAVAILABLE_ERRORS:
        body.update(status="degraded", database="unavailable")
        return JSONResponse(body, status_code=503)
    return body


@router.get("/dashboard/overview", summary="Рабочий стол «Обзор»")
async def overview(date_from: date | None = None, date_to: date | None = None,
                   _=Depends(current_user), session=Depends(get_db)):
    if not (date_from and date_to):
        date_from, date_to = await default_period(session)
    data = await DashboardService(session).overview(date_from, date_to)
    data["priority"] = [risk_out(r) for r in data["priority"]]
    return data


@router.get("/notifications", summary="Уведомления пользователя")
async def notifications(user=Depends(current_user), session=Depends(get_db)):
    stmt = (select(Notification).where(Notification.user_id == user.id)
            .order_by(Notification.id.desc()).limit(30))
    rows = (await session.execute(stmt)).scalars().all()
    return [{"id": n.id, "message": n.message, "is_read": n.is_read,
             "created_at": n.created_at} for n in rows]


@router.post("/notifications/read-all", summary="Отметить прочитанными")
async def read_all(user=Depends(current_user), session=Depends(get_db)):
    await session.execute(update(Notification)
                          .where(Notification.user_id == user.id)
                          .values(is_read=True))
    await session.commit()
    return {"detail": "ok"}


@router.get("/audit-log", summary="Журнал аудита (AUD-01)")
async def audit_log(limit: int = Query(default=100, le=1000),
                    offset: int = Query(default=0, ge=0),
                    table_name: str | None = None,
                    _=Depends(require_roles(RoleName.ADMIN, RoleName.CHIEF)),
                    session=Depends(get_db)):
    rows = await AuditRepository(session).list_all(limit=limit, offset=offset,
                                               table_name=table_name)
    return [{"id": r.id, "created_at": r.created_at,
             "user": r.user.full_name if r.user else "Система",
             "table_name": r.table_name, "action": r.action,
             "record_id": r.record_id, "details": r.details} for r in rows]
