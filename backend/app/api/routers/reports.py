"""Отчеты по рискам, согласование и экспорт (UC-4, UC-5, UC-6)."""
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Response

from app.api.deps import current_user, get_db, require_roles
from app.api.schemas import ReportCreate, ReturnIn, report_out
from app.domain.enums import RoleName
from app.repository.report_repository import ReportRepository
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Отчеты"])
author = require_roles(RoleName.AUDITOR, RoleName.CHIEF)


@router.post("", summary="Сформировать отчет по шаблону (FR-4.2)")
async def create_report(data: ReportCreate, user=Depends(author),
                        session=Depends(get_db)):
    report = await ReportService(session).create(
        title=data.title, period_from=data.date_from,
        period_to=data.date_to, user=user)
    return report_out(report, full=True)


@router.get("", summary="Список отчетов")
async def list_reports(_=Depends(current_user), session=Depends(get_db)):
    return [report_out(r) for r in await ReportRepository(session).list_all()]


@router.get("/{report_id}", summary="Отчет с тепловой картой")
async def get_report(report_id: int, _=Depends(current_user),
                     session=Depends(get_db)):
    return report_out(await ReportRepository(session).get(report_id), True)


@router.post("/{report_id}/submit", summary="Отправить на утверждение")
async def submit(report_id: int, user=Depends(author),
                 session=Depends(get_db)):
    return report_out(await ReportService(session).submit(report_id, user))


@router.post("/{report_id}/approve", summary="Утвердить с ЭЦП (FR-6.1)")
async def approve(report_id: int, user=Depends(current_user),
                  session=Depends(get_db)):
    return report_out(await ReportService(session).approve(report_id, user))


@router.post("/{report_id}/return", summary="Вернуть на доработку (FR-6.2)")
async def return_report(report_id: int, data: ReturnIn,
                        user=Depends(current_user),
                        session=Depends(get_db)):
    report = await ReportService(session).return_for_rework(
        report_id, user, data.comment)
    return report_out(report)


@router.get("/{report_id}/verify", summary="Проверка ЭЦП отчета")
async def verify(report_id: int, _=Depends(current_user),
                 session=Depends(get_db)):
    return {"valid": await ReportService(session).verify(report_id)}


@router.get("/{report_id}/export", summary="Экспорт в PDF или XLSX (UC-5)")
async def export(report_id: int,
                 format: str = Query(default="pdf", pattern="^(pdf|xlsx)$"),
                 user=Depends(current_user), session=Depends(get_db)):
    content, media, name = await ReportService(session).export(
        report_id, format, user)
    return Response(content, media_type=media, headers={
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}"})
