"""Интеграционные тесты выявления и обработки рисков (UC-3, UC-4)."""
from datetime import timedelta

from sqlalchemy import func, select

from app.db.models import Notification, Risk
from app.ml.strategies import MLAnomalyDetector
from app.repository.risk_repository import RiskRepository
from app.services.risk_calculation import RiskCalculationService
from tests.conftest import SCOPE

PERIOD = {"date_from": str(SCOPE.date_from), "date_to": str(SCOPE.date_to)}


def service(session):
    return RiskCalculationService(session, MLAnomalyDetector(),
                                  RiskRepository(session))


async def detect(session, users):
    return await service(session).score_transactions(
        SCOPE.date_from, SCOPE.date_to, users["zhdanko"])


async def test_detection_creates_risks(session, users, imported):
    """IT-08. Скоринг создает риски для оценок не ниже 0,85."""
    result = await detect(session, users)
    assert 0.03 <= result.risks_created / result.transactions <= 0.07
    risks = (await session.execute(select(Risk))).scalars().unique().all()
    assert all(float(r.anomaly_score) >= 0.85 for r in risks)
    assert all(0 <= float(r.probability) <= 1 for r in risks)


async def test_detection_rerun_is_idempotent(session, users, imported):
    """IT-09. Повторный скоринг не дублирует риски."""
    first = await detect(session, users)
    second = await detect(session, users)
    assert second.risks_created == 0
    assert second.skipped_existing == first.risks_created


async def test_chief_notified_after_detection(session, users, imported):
    """IT-10. Руководитель получает уведомление о результатах (BR-4)."""
    await detect(session, users)
    stmt = select(func.count(Notification.id)).where(
        Notification.user_id == users["kovalchuk"].id)
    assert (await session.execute(stmt)).scalar() == 1


def test_probability_bounds():
    """UT-26. Вероятность растет с оценкой и не превышает 0,99."""
    calc = RiskCalculationService.calculate_probability
    svc = object.__new__(RiskCalculationService)
    assert float(calc(svc, 0.85)) == 0.15
    assert float(calc(svc, 1.0)) == 0.85
    assert float(calc(svc, 1.0, repeats=5)) == 0.99


async def test_heatmap_api(client, auditor, session, users, imported):
    """IT-11. Тепловая карта 5x5 учитывает все риски периода."""
    result = await detect(session, users)
    response = await client.get("/api/v1/heatmap", params=PERIOD,
                                headers=auditor)
    data = response.json()
    assert len(data["cells"]) == 5 and len(data["cells"][0]) == 5
    assert sum(c["count"] for row in data["cells"] for c in row) == \
        result.risks_created
    assert data["cells"][4][4]["zone"] == "red"
    assert data["cells"][0][0]["zone"] == "green"


async def test_statistical_strategy_via_api(client, auditor, imported):
    """IT-12. Стратегия Z-оценки выбирается параметром запроса."""
    response = await client.post("/api/v1/risks/detect", headers=auditor,
                                 json={**PERIOD, "strategy": "stat"})
    assert response.status_code == 200
    assert response.json()["method"] == "Z-оценка"


async def test_transition_and_invalid_action(client, auditor, session,
                                             users, imported):
    """IT-13. Смена состояния через API и отказ при неверном переходе."""
    risk_id = (await detect(session, users)).risk_ids[0]
    url = f"/api/v1/risks/{risk_id}/transition"
    ok = await client.post(url, json={"action": "assess"}, headers=auditor)
    assert ok.status_code == 200 and ok.json()["status"] == "Оценен"
    bad = await client.post(url, json={"action": "archive"}, headers=auditor)
    assert bad.status_code == 409


async def test_delete_requires_chief(client, auditor, chief, session, users,
                                     imported):
    """IT-14. Аудитор не может удалить риск без руководителя (BR-9)."""
    risk_id = (await detect(session, users)).risk_ids[0]
    url = f"/api/v1/risks/{risk_id}"
    assert (await client.delete(url, headers=auditor)).status_code == 403
    assert (await client.delete(url, headers=chief)).status_code == 204
    assert (await client.get(url, headers=auditor)).status_code == 404


async def test_stale_critical_risks_escalated(client, chief, session, users,
                                              imported):
    """IT-15. Красная зона более 30 дней приводит к эскалации (BR-6)."""
    await detect(session, users)
    risk = (await session.execute(select(Risk).limit(1))).scalars().first()
    risk.level, risk.created_at = "Критический", \
        risk.created_at - timedelta(days=31)
    await session.commit()
    response = await client.post("/api/v1/risks/escalate-stale",
                                 headers=chief)
    assert response.json()["escalated"] == 1


async def test_search_resists_sql_injection(client, auditor, session, users,
                                            imported):
    """ST-01. Строка поиска с SQL-инъекцией не меняет запрос (SEC-03)."""
    await detect(session, users)
    response = await client.get("/api/v1/risks", headers=auditor,
                                params={"q": "' OR 1=1 --"})
    assert response.status_code == 200 and response.json()["total"] == 0


async def test_comment_xss_stripped(client, auditor, session, users,
                                    imported):
    """ST-02. HTML-разметка в комментарии не сохраняется (SEC-03)."""
    risk_id = (await detect(session, users)).risk_ids[0]
    url = f"/api/v1/risks/{risk_id}/transition"
    await client.post(url, json={"action": "assess"}, headers=auditor)
    response = await client.post(url, headers=auditor, json={
        "action": "dismiss", "comment": "<img src=x onerror=alert(1)>Ок"})
    assert response.json()["comment"] == "Ок"
