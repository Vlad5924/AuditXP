"""Интеграционные тесты отчетов (UC-4, UC-5, UC-6, FR-6.1–FR-6.3)."""
import io

import pytest
from openpyxl import load_workbook

from app.services.notification_service import outbox
from tests.test_risks import PERIOD, detect


@pytest.fixture
async def report(client, auditor, session, users, imported):
    await detect(session, users)
    response = await client.post("/api/v1/reports", headers=auditor,
                                 json={**PERIOD, "title": "Отчет 09.2026"})
    assert response.status_code == 200
    return response.json()


async def test_report_created_as_draft(report):
    """IT-16. Отчет формируется по шаблону со сводкой (FR-4.2)."""
    assert report["status"] == "Черновик"
    assert report["summary"]["transactions"] > 0
    assert report["summary"]["risks"] > 0
    assert len(report["summary"]["heatmap"]["cells"]) == 5


async def test_submit_sets_on_review(client, auditor, report):
    """IT-17. Отправка переводит отчет в статус «На проверке»."""
    url = f"/api/v1/reports/{report['id']}/submit"
    response = await client.post(url, headers=auditor)
    assert response.json()["status"] == "На проверке"
    assert any("на утверждение" in m["subject"] for m in outbox.messages)


async def test_only_chief_approves_with_signature(client, auditor, chief,
                                                  report):
    """IT-18. Утверждение руководителем с ЭЦП (FR-6.1, FR-6.3)."""
    rid = report["id"]
    await client.post(f"/api/v1/reports/{rid}/submit", headers=auditor)
    denied = await client.post(f"/api/v1/reports/{rid}/approve",
                               headers=auditor)
    assert denied.status_code == 403
    approved = await client.post(f"/api/v1/reports/{rid}/approve",
                                 headers=chief)
    assert approved.json()["status"] == "Утвержден"
    assert len(approved.json()["signature"]) == 64
    verify = await client.get(f"/api/v1/reports/{rid}/verify",
                              headers=auditor)
    assert verify.json()["valid"] is True
    assert outbox.messages[-1]["to"] == "v.zhdanko@goldberg-soft.by"


async def test_return_requires_comment(client, auditor, chief, report):
    """IT-19. Возврат на доработку только с комментарием (FR-6.2)."""
    rid = report["id"]
    await client.post(f"/api/v1/reports/{rid}/submit", headers=auditor)
    url = f"/api/v1/reports/{rid}/return"
    empty = await client.post(url, json={"comment": ""}, headers=chief)
    assert empty.status_code == 422
    ok = await client.post(url, headers=chief,
                           json={"comment": "Уточнить ущерб по RK-1001"})
    assert ok.json()["status"] == "На доработке"


async def test_export_pdf_and_xlsx(client, auditor, report):
    """IT-20. Экспорт отчета в PDF и Excel (FR-5.1, FR-5.2)."""
    url = f"/api/v1/reports/{report['id']}/export"
    pdf = await client.get(url, params={"format": "pdf"}, headers=auditor)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    xlsx = await client.get(url, params={"format": "xlsx"}, headers=auditor)
    book = load_workbook(io.BytesIO(xlsx.content))
    assert book.sheetnames == ["Сводка", "Реестр рисков", "Тепловая карта"]
    assert book["Реестр рисков"].max_row == report["summary"]["risks"] + 1
