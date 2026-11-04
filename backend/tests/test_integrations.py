"""Интеграционные тесты внешних интерфейсов ERP и SMTP (SI-01, FR-6.3)."""
from datetime import date
from types import SimpleNamespace

import httpx

from app.etl import erp_client
from app.etl.erp_client import ErpClient, HttpErpSource, ImportScope
from app.services import notification_service
from app.services.notification_service import SmtpEmailSender

SCOPE = ImportScope(date(2026, 10, 1), date(2026, 10, 31), ["Закупки"])
ROW = {"doc_number": "PO-1", "department": "Закупки",
       "transaction_date": "2026-10-05", "amount": "1250.40",
       "counterparty": "ООО «ДатаСервис»", "account_debit": "60",
       "account_credit": "51"}


def test_http_erp_source_reads_pages(monkeypatch):
    """IT-24. Клиент REST API ERP передает токен и читает все страницы."""
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/health"):
            return httpx.Response(200, json={"status": "ok"})
        page = int(request.url.params["page"])
        items = [dict(ROW, doc_number=f"PO-{page}-{i}") for i in range(2)]
        return httpx.Response(200, json={"items": items if page < 2 else []})

    real_client = httpx.Client
    monkeypatch.setattr(erp_client.httpx, "Client", lambda **kw: real_client(
        transport=httpx.MockTransport(handler), **kw))
    source = HttpErpSource("https://erp.goldberg-soft.by/api", "secret")
    frame = ErpClient(source, page_size=2, delay=0).fetch_transactions(SCOPE)
    assert len(frame) == 4 and frame["doc_number"].is_unique
    assert all(r.headers["Authorization"] == "Bearer secret"
               for r in requests)
    assert [r.method for r in requests] == ["GET"] * len(requests)
    assert requests[0].url.path == "/api/health"
    assert requests[1].url.params["departments"] == "Закупки"


def test_smtp_sender_uses_starttls(monkeypatch):
    """IT-25. Письмо уходит через SMTP с STARTTLS и авторизацией."""
    log: list[tuple] = []

    class FakeSmtp:
        def __init__(self, host, port, timeout):
            log.append(("connect", host, port))

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            log.append(("quit",))

        def starttls(self):
            log.append(("starttls",))

        def login(self, user, password):
            log.append(("login", user))

        def send_message(self, msg):
            log.append(("send", msg["To"], msg["Subject"]))

    monkeypatch.setattr(notification_service.smtplib, "SMTP", FakeSmtp)
    settings = SimpleNamespace(
        smtp_host="mail.goldberg-soft.by", smtp_port=587,
        smtp_user="auditxp", smtp_password="pwd",
        mail_from="auditxp@goldberg-soft.by")
    SmtpEmailSender(settings).send("chief@goldberg-soft.by",
                                   "Отчет утвержден", "Текст")
    assert log == [("connect", "mail.goldberg-soft.by", 587), ("starttls",),
                   ("login", "auditxp"),
                   ("send", "chief@goldberg-soft.by", "Отчет утвержден"),
                   ("quit",)]
