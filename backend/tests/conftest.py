"""Общие фикстуры тестов. По умолчанию используется временная SQLite,
переменная TEST_DATABASE_URL позволяет запустить тесты на PostgreSQL."""
import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="auditxp-test-")
os.environ.update({
    "DATABASE_URL": os.environ.get(
        "TEST_DATABASE_URL", f"sqlite+aiosqlite:///{_TMP}/test.db"),
    "SEED_DEMO": "false", "AUTO_CREATE_SCHEMA": "false",
    "BCRYPT_ROUNDS": "4", "ERP_RETRY_DELAY": "0",
    "FRONTEND_DIST": f"{_TMP}/no-frontend",
})

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.db.session import dispose_engine, get_sessionmaker, init_models  # noqa: E402
from app.etl.erp_client import ErpClient, MockErpSource, month_scope  # noqa: E402
from app.etl.module import EtlIntegrationModule  # noqa: E402
from app.main import create_app  # noqa: E402
from app.seed import seed_base  # noqa: E402
from app.services.notification_service import outbox  # noqa: E402

PASSWORDS = {"zhdanko": "Auditor2026", "litvinova": "Auditor2026",
             "kovalchuk": "Chief2026", "admin": "Admin2026"}


@pytest_asyncio.fixture
async def session():
    await dispose_engine()
    await init_models(drop=True)
    outbox.messages.clear()
    async with get_sessionmaker()() as db:
        yield db
    await dispose_engine()


@pytest_asyncio.fixture
async def users(session):
    return await seed_base(session)


@pytest_asyncio.fixture
async def client(session, users):
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport,
                           base_url="http://test") as http:
        yield http


async def auth_headers(client, login: str) -> dict:
    response = await client.post("/api/v1/auth/login", json={
        "login": login, "password": PASSWORDS[login]})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest_asyncio.fixture
async def auditor(client):
    return await auth_headers(client, "zhdanko")


@pytest_asyncio.fixture
async def chief(client):
    return await auth_headers(client, "kovalchuk")


@pytest_asyncio.fixture
async def admin(client):
    return await auth_headers(client, "admin")


SCOPE = month_scope(2026, 9)


async def run_import(session, user, per_day: int = 40, **source_kw):
    source = MockErpSource(per_day=per_day, **source_kw)
    module = EtlIntegrationModule(session, client=ErpClient(source, delay=0))
    return await module.import_transactions(SCOPE, user), source


@pytest_asyncio.fixture
async def imported(session, users):
    result, _ = await run_import(session, users["zhdanko"])
    return result
