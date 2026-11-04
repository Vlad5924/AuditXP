"""Хеширование паролей, JWT-токены и электронная подпись отчетов."""
import hashlib
import hmac
import re
import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import get_settings
from app.core.errors import BusinessError

PASSWORD_RE = re.compile(r"^(?=.*[A-Za-zА-Яа-я])(?=.*\d).{8,64}$")


def hash_password(password: str) -> str:
    """Хеширует пароль алгоритмом bcrypt (требование SEC-02)."""
    rounds = get_settings().bcrypt_rounds
    salt = bcrypt.gensalt(rounds=rounds)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"),
                              password_hash.encode("ascii"))
    except ValueError:
        return False


def validate_password_policy(password: str) -> None:
    """Пароль от 8 символов, содержит буквы и цифры."""
    if not PASSWORD_RE.match(password or ""):
        raise BusinessError(
            "Пароль должен содержать от 8 символов, буквы и цифры")


def create_access_token(subject: str, role: str,
                        expires_minutes: int | None = None) -> str:
    """Выпускает JWT-токен HS256 (требование SI-02)."""
    settings = get_settings()
    now = datetime.now(UTC)
    ttl = expires_minutes or settings.jwt_expires_minutes
    payload = {"sub": subject, "role": role, "iat": now,
               "exp": now + timedelta(minutes=ttl)}
    return jwt.encode(payload, settings.jwt_secret,
                      algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret,
                      algorithms=[settings.jwt_algorithm])


def generate_reset_token() -> tuple[str, str]:
    """Возвращает пару (токен для письма, хеш для хранения в БД)."""
    token = secrets.token_urlsafe(32)
    return token, hash_reset_token(token)


def hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def sign_document(content: bytes) -> str:
    """Формирует ЭЦП отчета как HMAC-SHA256 от его содержимого."""
    key = get_settings().signature_secret.encode("utf-8")
    return hmac.new(key, content, hashlib.sha256).hexdigest()


def verify_signature(content: bytes, signature: str) -> bool:
    return hmac.compare_digest(sign_document(content), signature or "")
