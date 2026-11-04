"""Конфигурация приложения, считываемая из переменных окружения и .env."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    """Параметры работы AuditXP (значения по умолчанию для разработки)."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AuditXP: Риск-менеджмент"
    app_version: str = "1.0.0"
    app_env: str = "development"

    database_url: str = (
        f"sqlite+aiosqlite:///{(BACKEND_DIR / 'auditxp.db').as_posix()}"
    )
    auto_create_schema: bool = True
    seed_demo: bool = True

    jwt_secret: str = "dev-secret-change-me-in-production-32b"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 480
    signature_secret: str = "dev-signature-secret-change-me-32b"
    bcrypt_rounds: int = 12
    max_failed_logins: int = 5
    reset_token_minutes: int = 30

    erp_mode: str = "mock"
    erp_base_url: str = "https://erp.goldberg.local/api/v1"
    erp_token: str = ""
    erp_retry_attempts: int = 3
    erp_retry_delay: float = 1.0
    erp_page_size: int = 5000

    risk_threshold: float = 0.85
    fraud_alert_amount: float = 10_000
    escalation_days: int = 30
    escalation_score: int = 15
    retention_years: int = 5

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    mail_from: str = "auditxp@goldberg-soft.by"

    cors_origins: str = "http://localhost:5173"
    frontend_dist: str = str(PROJECT_DIR / "frontend" / "dist")

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    """Возвращает единственный экземпляр настроек."""
    return Settings()
