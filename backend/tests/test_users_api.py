"""Системные тесты администрирования учетных записей (UC-7)."""
USERS = "/api/v1/users"
NEW = {"login": "petrov", "full_name": "Петров А.А.",
       "email": "a.petrov@goldberg-soft.by", "password": "Petrov2026",
       "role": "Аудитор"}


async def test_admin_creates_user(client, admin):
    """ST-09. Создание записи и контроль уникальности (FR-7.1)."""
    created = await client.post(USERS, json=NEW, headers=admin)
    assert created.status_code == 201
    duplicate = await client.post(USERS, json=NEW, headers=admin)
    assert duplicate.status_code == 422
    weak = await client.post(USERS, headers=admin,
                             json={**NEW, "login": "p2", "password": "1"})
    assert weak.status_code == 422


async def test_non_admin_forbidden(client, auditor):
    """ST-10. Аудитор не имеет доступа к администрированию."""
    assert (await client.get(USERS, headers=auditor)).status_code == 403


async def test_assign_role(client, admin):
    """ST-11. Администратор назначает роль (FR-7.2)."""
    user = (await client.post(USERS, json=NEW, headers=admin)).json()
    response = await client.put(f"{USERS}/{user['id']}", headers=admin,
                                json={"role": "Руководитель"})
    assert response.json()["role_name"] == "Руководитель"


async def test_block_and_unblock(client, admin):
    """ST-12. Заблокированный пользователь не может войти."""
    user = (await client.post(USERS, json=NEW, headers=admin)).json()
    await client.post(f"{USERS}/{user['id']}/block", headers=admin)
    body = {"login": "petrov", "password": "Petrov2026"}
    assert (await client.post("/api/v1/auth/login",
                              json=body)).status_code == 423
    await client.post(f"{USERS}/{user['id']}/unblock", headers=admin)
    assert (await client.post("/api/v1/auth/login",
                              json=body)).status_code == 200


async def test_delete_deactivates(client, admin):
    """ST-13. Удаление деактивирует запись без потери истории."""
    user = (await client.post(USERS, json=NEW, headers=admin)).json()
    response = await client.delete(f"{USERS}/{user['id']}", headers=admin)
    assert response.json()["is_active"] is False
    login = await client.post("/api/v1/auth/login", json={
        "login": "petrov", "password": "Petrov2026"})
    assert login.status_code == 401
