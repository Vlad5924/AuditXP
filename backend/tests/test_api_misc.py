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


class _BrokenSession:
    """Сессия, имитирующая отказ соединения с СУБД."""

    async def execute(self, *_args, **_kwargs):
        raise ConnectionRefusedError(111, "Connection refused")

    async def scalar(self, *_args, **_kwargs):
        raise ConnectionRefusedError(111, "Connection refused")


async def test_database_unavailable_returns_503(session, users):
    """ST-25. При отказе СУБД API отвечает 503 с понятным сообщением."""
    from httpx import ASGITransport, AsyncClient

    from app.api.deps import get_db
    from app.main import create_app

    app = create_app()
    app.dependency_overrides[get_db] = lambda: _BrokenSession()
    async with AsyncClient(transport=ASGITransport(app=app),
                           base_url="http://test") as http:
        health = await http.get("/api/v1/health")
        assert health.status_code == 503
        assert health.json()["database"] == "unavailable"
        login = await http.post("/api/v1/auth/login", json={
            "login": "zhdanko", "password": "Auditor2026"})
        assert login.status_code == 503
        assert "недоступна" in login.json()["detail"]
