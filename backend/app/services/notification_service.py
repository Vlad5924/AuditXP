"""Уведомления в системе и по корпоративной почте (FR-6.3)."""
import asyncio
import logging
import smtplib
from email.message import EmailMessage
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import Notification, User
from app.repository.user_repository import UserRepository

log = logging.getLogger("auditxp.mail")


class EmailSender(Protocol):
    def send(self, to: str, subject: str, body: str) -> None: ...


class OutboxEmailSender:
    """Почтовый ящик разработчика: письма сохраняются в памяти."""

    def __init__(self) -> None:
        self.messages: list[dict] = []

    def send(self, to: str, subject: str, body: str) -> None:
        self.messages.append({"to": to, "subject": subject, "body": body})
        log.info("Письмо для %s: %s", to, subject)


class SmtpEmailSender:
    def __init__(self, settings) -> None:
        self.settings = settings

    def send(self, to: str, subject: str, body: str) -> None:
        msg = EmailMessage()
        msg["From"], msg["To"], msg["Subject"] = (
            self.settings.mail_from, to, subject)
        msg.set_content(body)
        with smtplib.SMTP(self.settings.smtp_host,
                          self.settings.smtp_port, timeout=15) as smtp:
            smtp.starttls()
            if self.settings.smtp_user:
                smtp.login(self.settings.smtp_user,
                           self.settings.smtp_password)
            smtp.send_message(msg)


outbox = OutboxEmailSender()


def get_email_sender() -> EmailSender:
    settings = get_settings()
    return SmtpEmailSender(settings) if settings.smtp_host else outbox


class NotificationService:
    def __init__(self, session: AsyncSession,
                 sender: EmailSender | None = None) -> None:
        self.session = session
        self.sender = sender or get_email_sender()

    async def notify(self, user: User, message: str,
                     subject: str | None = None) -> None:
        self.session.add(Notification(user_id=user.id, message=message))
        if subject:
            try:
                await asyncio.to_thread(self.sender.send, user.email,
                                        subject, message)
            except Exception as exc:  # почта не должна ломать сценарий
                log.error("Не удалось отправить письмо (%s)", exc)

    async def notify_role(self, role: str, message: str,
                          subject: str | None = None) -> int:
        users = await UserRepository(self.session).with_role(role)
        for user in users:
            await self.notify(user, message, subject)
        return len(users)
