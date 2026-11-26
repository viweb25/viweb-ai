"""Business errors raised by services and repositories.

The HTTP layer maps each error class to a status code, so inner layers never
depend on the web framework.
"""


class DomainError(Exception):
    code = "domain_error"

    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code


class NotFound(DomainError):
    code = "not_found"


class Conflict(DomainError):
    code = "conflict"


class InvalidInput(DomainError):
    code = "invalid_input"


class PermissionDenied(DomainError):
    code = "permission_denied"


class Unavailable(DomainError):
    code = "unavailable"


class UnsupportedMediaType(DomainError):
    code = "unsupported_media_type"


class PayloadTooLarge(DomainError):
    code = "payload_too_large"
