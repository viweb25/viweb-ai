from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from starlette.exceptions import HTTPException

from app.api.v1.controllers.catalogue import router as catalogue_router
from app.db import engine

app = FastAPI(title="VI WebSync API", version="0.1.0")


class Health(BaseModel):
    status: str
    service: str


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": f"http_{exc.status_code}", "message": str(exc.detail)}},
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": {"code": "validation_error", "message": "Request does not match the contract"}
        },
    )


@app.get("/health/live", response_model=Health, tags=["health"])
def live():
    """Process liveness only; does not claim database or hardware readiness."""
    return Health(status="ok", service="api")


app.include_router(catalogue_router)


@app.get(
    "/health/ready",
    response_model=Health,
    tags=["health"],
    responses={503: {"model": ErrorResponse}},
)
async def ready():
    """Database and migration readiness, independent of model availability."""
    import asyncio

    try:
        async with asyncio.timeout(3):
            async with engine.connect() as connection:
                revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))
                if revision != "0002":
                    raise RuntimeError("Migration revision mismatch")
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"error": {"code": "not_ready", "message": "Database migration not ready"}},
        )
    return Health(status="ok", service="api")
