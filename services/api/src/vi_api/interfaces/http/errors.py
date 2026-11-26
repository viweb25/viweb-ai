import logging
from enum import StrEnum

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from vi_api.domain.errors import (
    Conflict,
    DomainError,
    InvalidInput,
    NotFound,
    PayloadTooLarge,
    PermissionDenied,
    Unavailable,
    UnsupportedMediaType,
)

logger = logging.getLogger("vi_api")
DOMAIN_STATUS = {
    NotFound: 404,
    Conflict: 409,
    InvalidInput: 422,
    PermissionDenied: 403,
    Unavailable: 503,
    UnsupportedMediaType: 415,
    PayloadTooLarge: 413,
}


class ErrorCode(StrEnum):
    SIGNUP_CONFLICT = "signup_conflict"
    INFERENCE_UNAVAILABLE = "inference_unavailable"
    INVALID_CREDENTIALS = "invalid_credentials"
    SIGN_IN_RATE_LIMITED = "sign_in_rate_limited"
    AUTHENTICATION_REQUIRED = "authentication_required"
    ORGANISATION_ACCESS_DENIED = "organisation_access_denied"
    SIGN_IN_UNAVAILABLE = "sign_in_unavailable"
    INVALID_REQUEST_ORIGIN = "invalid_request_origin"
    DEMO_DISABLED = "demo_disabled"
    EXAMPLE_IMAGE_NOT_FOUND = "example_image_not_found"
    UNSUPPORTED_IMAGE_TYPE = "unsupported_image_type"
    IMAGE_TOO_LARGE = "image_too_large"
    INVALID_IMAGE = "invalid_image"


class ApiError(HTTPException):
    def __init__(self, status_code: int, code: ErrorCode, message: str):
        super().__init__(status_code=status_code, detail=message)
        self.code = code


async def http_error(request: Request, exc: HTTPException):
    code = exc.code if isinstance(exc, ApiError) else f"http_{exc.status_code}"
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": code, "message": str(exc.detail)}},
        headers=exc.headers,
    )


async def validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": {"code": "validation_error", "message": "Request does not match the contract"}
        },
    )


def error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


async def domain_error(request: Request, exc: DomainError):
    status = next((DOMAIN_STATUS[kind] for kind in type(exc).__mro__ if kind in DOMAIN_STATUS), 400)
    return JSONResponse(status_code=status, content=error_body(exc.code, exc.message))


async def unexpected_error(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", None)
    logger.exception("Unhandled error", extra={"request_id": request_id})
    return JSONResponse(
        status_code=500,
        content=error_body("internal_error", "Something went wrong. Try again."),
        headers={"X-Request-ID": request_id} if request_id else None,
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, http_error)
    app.add_exception_handler(RequestValidationError, validation_error)
    app.add_exception_handler(DomainError, domain_error)
    app.add_exception_handler(Exception, unexpected_error)
