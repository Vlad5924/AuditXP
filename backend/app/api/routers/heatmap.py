"""Тепловая карта рисков (UC-4, FR-4.1)."""
from datetime import date

from fastapi import APIRouter, Depends

from app.api.deps import current_user, get_db
from app.repository.risk_repository import RiskRepository
from app.services.risk_calculation import RiskCalculationService

router = APIRouter(prefix="/heatmap", tags=["Тепловая карта"])


@router.get("", summary="Матрица 5x5 «вероятность x ущерб»")
async def heatmap(date_from: date, date_to: date, _=Depends(current_user),
                  session=Depends(get_db)):
    risks = await RiskRepository(session).for_period(date_from, date_to)
    return RiskCalculationService.build_heatmap(risks)
