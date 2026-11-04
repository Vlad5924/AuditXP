"""Иерархия прикладных исключений и их HTTP-коды."""


class DomainError(Exception):
    """Базовая ошибка предметной области."""

    status_code = 400

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class AuthError(DomainError):
    status_code = 401


class PermissionDeniedError(DomainError):
    status_code = 403


class NotFoundError(DomainError):
    status_code = 404


class InvalidTransitionError(DomainError):
    status_code = 409


class AccountLockedError(DomainError):
    status_code = 423


class BusinessError(DomainError):
    status_code = 422


class ErpUnavailableError(DomainError):
    status_code = 503
