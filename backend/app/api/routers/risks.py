"""Выявление, оценка и обработка рисков (UC-3)."""
from datetime import date

from fastapi import APIRouter, Depends, Query

from app.api.deps import current_user, get_db, require_roles
from app.api.schemas import DetectIn, TransitionIn, risk_out
from app.domain.enums import RoleName
from app.ml.strategies import make_strategy
from app.repository.risk_repository import RiskRepository
from app.services.risk_calculation import RiskCalculationService
from app.services.risk_service import RiskService

router = APIRouter(prefix="/risks", tags=["Риски"])
auditor = require_roles(RoleName.AUDITOR, RoleName.CHIEF)


@router.post("/detect", summary="Скоринг транзакций за период (FR-3.1)")
async def detect(data: DetectIn, user=Depends(auditor),
                 session=Depends(get_db)):
    service = RiskCalculationService(session, make_strategy(data.strategy),
                                     RiskRepository(session))
    result = await service.score_transactions(data.date_from, data.date_to,
                                              user)
    return result.__dict__


@router.get("", summary="Реестр рисков с фильтрами (FR-3.3)")
async def list_risks(status: str | None = None, level: str | None = None,
                     department: str | None = None,
                     q: str | None = Query(default=None, max_length=100),
                     date_from: date | None = None,
                     date_to: date | None = None,
                     limit: int = Query(default=50, le=500),
                     offset: int = Query(default=0, ge=0),
                     _=Depends(current_user), session=Depends(get_db)):
    items, total = await RiskRepository(session).search(
        status=status, level=level, department=department, q=q,
        date_from=date_from, date_to=date_to, limit=limit, offset=offset)
    return {"items": [risk_out(r) for r in items], "total": total}


@router.get("/{risk_id}", summary="Карточка риска")
async def get_risk(risk_id: int, _=Depends(current_user),
                   session=Depends(get_db)):
    return risk_out(await RiskRepository(session).get(risk_id))


@router.post("/{risk_id}/transition", summary="Смена состояния риска")
async def transition(risk_id: int, data: TransitionIn,
                     user=Depends(auditor), session=Depends(get_db)):
    risk = await RiskService(session).transition(
        risk_id, data.action, user, comment=data.comment,
        mitigation_plan=data.mitigation_plan,
        mitigation_owner=data.mitigation_owner,
        mitigation_due=data.mitigation_due,
        effectiveness_confirmed=data.effectiveness_confirmed)
    return risk_out(risk)


@router.post("/{risk_id}/escalate", summary="Эскалация руководителю")
async def escalate(risk_id: int, user=Depends(auditor),
                   session=Depends(get_db)):
    return risk_out(await RiskService(session).escalate(risk_id, user))


@router.post("/escalate-stale", summary="Эскалация просроченных (BR-6)")
async def escalate_stale(user=Depends(require_roles(RoleName.CHIEF,
                                                    RoleName.ADMIN)),
                         session=Depends(get_db)):
    return {"escalated": await RiskService(session).escalate_stale(user)}


@router.delete("/{risk_id}", status_code=204,
               summary="Удаление риска руководителем (BR-9)")
async def delete_risk(risk_id: int, user=Depends(current_user),
                      session=Depends(get_db)):
    await RiskService(session).delete(risk_id, user)
