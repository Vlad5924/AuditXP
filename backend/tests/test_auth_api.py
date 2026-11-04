"""Системные тесты входа и восстановления пароля (UC-1, FR-1.1–FR-1.3)."""
import re

from app.services.notification_service import outbox

LOGIN = "/api/v1/auth/login"


async def test_login_success(client):
    """ST-03. Вход с верными данными выдает токен (FR-1.1)."""
    response = await client.post(LOGIN, json={"login": "zhdanko",
                                              "password": "Auditor2026"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    me = await client.get("/api/v1/auth/me",
                          headers={"Authorization": f"Bearer {token}"})
    assert me.json()["role_name"] == "Аудитор"


async def test_wrong_password(client):
    """ST-04. Неверный пароль отклоняется с остатком попыток."""
    response = await client.post(LOGIN, json={"login": "zhdanko",
                                              "password": "wrong"})
    assert response.status_code == 401
    assert "осталось попыток 4" in response.json()["detail"]


async def test_lock_after_five_failures(client, admin):
    """ST-05. Пять неудачных попыток блокируют запись (FR-1.2)."""
    codes = [(await client.post(LOGIN, json={
        "login": "zhdanko", "password": "bad"})).status_code
        for _ in range(5)]
    assert codes == [401, 401, 401, 401, 423]
    correct = await client.post(LOGIN, json={"login": "zhdanko",
                                             "password": "Auditor2026"})
    assert correct.status_code == 423
    notes = await client.get("/api/v1/notifications", headers=admin)
    assert "заблокирована" in notes.json()[0]["message"]


async def test_protected_endpoint_requires_token(client):
    """ST-06. Без токена или с поддельным токеном доступ запрещен."""
    assert (await client.get("/api/v1/risks")).status_code == 401
    fake = {"Authorization": "Bearer abc.def.ghi"}
    assert (await client.get("/api/v1/risks", headers=fake)).status_code \
        == 401


async def test_password_recovery_flow(client):
    """ST-07. Восстановление пароля по корпоративной почте (FR-1.3)."""
    response = await client.post("/api/v1/auth/password-recovery",
                                 json={"email": "v.zhdanko@goldberg-soft.by"})
    assert response.status_code == 200
    token = re.search(r"token=(\S+)", outbox.messages[-1]["body"]).group(1)
    weak = await client.post("/api/v1/auth/password-reset",
                             json={"token": token, "new_password": "123"})
    assert weak.status_code == 422
    ok = await client.post("/api/v1/auth/password-reset", json={
        "token": token, "new_password": "NewPass2026"})
    assert ok.status_code == 200
    login = await client.post(LOGIN, json={"login": "zhdanko",
                                           "password": "NewPass2026"})
    assert login.status_code == 200


async def test_recovery_hides_unknown_email(client):
    """ST-08. Ответ не раскрывает наличие адреса в системе."""
    response = await client.post("/api/v1/auth/password-recovery",
                                 json={"email": "nobody@goldberg-soft.by"})
    assert response.status_code == 200 and not outbox.messages
