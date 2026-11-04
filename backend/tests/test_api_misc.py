"""Системные тесты служебных функций API."""
from tests.test_risks import detect


async def test_health(client):
    """ST-18. Проверка работоспособности сервиса и СУБД."""
    response = await client.get("/api/v1/health")
    assert response.json()["status"] == "ok"


async def test_security_headers(client):
    """ST-19. Ответы содержат защитные заголовки."""
    response = await client.get("/api/v1/health")
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]


async def test_overview(client, auditor, session, users, imported):
    """ST-20. Рабочий стол «Обзор» возвращает показатели периода."""
    await detect(session, users)
    data = (await client.get("/api/v1/dashboard/overview",
                             headers=auditor)).json()
    assert data["transactions"] > 0 and data["risks"] > 0
    assert len(data["priority"]) == 5 and len(data["weekly"]) == 5


async def test_openapi_published(client):
    """ST-21. Спецификация OpenAPI описывает все ресурсы (SI-01)."""
    spec = (await client.get("/api/openapi.json")).json()
    assert len(spec["paths"]) >= 30
