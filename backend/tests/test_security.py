"""Модульные тесты безопасности (SEC-02, SI-02, FR-6.1)."""
import jwt
import pytest

from app.core.errors import BusinessError
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    sign_document,
    validate_password_policy,
    verify_password,
    verify_signature,
)
from app.services.text import clean_text


def test_password_hashed_with_bcrypt():
    """UT-01. Пароль хранится только в виде bcrypt-хеша."""
    hashed = hash_password("Auditor2026")
    assert hashed.startswith("$2b$") and "Auditor2026" not in hashed
    assert verify_password("Auditor2026", hashed)
    assert not verify_password("auditor2026", hashed)


@pytest.mark.parametrize("password", ["short1", "БезЦифрПароль", "12345678"])
def test_weak_password_rejected(password):
    """UT-02. Политика паролей отклоняет слабые пароли."""
    with pytest.raises(BusinessError):
        validate_password_policy(password)


def test_jwt_roundtrip():
    """UT-03. Токен содержит идентификатор и роль пользователя."""
    payload = decode_access_token(create_access_token("7", "Аудитор"))
    assert payload["sub"] == "7" and payload["role"] == "Аудитор"


def test_jwt_expired():
    """UT-04. Просроченный токен отклоняется."""
    token = create_access_token("7", "Аудитор", expires_minutes=-1)
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)


def test_document_signature_detects_tampering():
    """UT-05. ЭЦП отчета становится недействительной при изменении."""
    signature = sign_document(b"report-42")
    assert verify_signature(b"report-42", signature)
    assert not verify_signature(b"report-43", signature)


def test_comment_markup_removed():
    """UT-06. Из комментария удаляются HTML-теги (SEC-03)."""
    assert clean_text("<script>alert(1)</script>Проверено") == \
        "alert(1)Проверено"
