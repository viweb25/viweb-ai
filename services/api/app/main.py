import json
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException

ROOT = Path(__file__).resolve().parents[3]
app = FastAPI(title="VI WebSync API", version="0.1.0")


class Health(BaseModel):
    status: str
    service: str


class FunctionTemplate(BaseModel):
    id: str
    name: str
    stage: str
    config_schema: dict


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


@app.get("/api/v1/function-templates", response_model=list[FunctionTemplate], tags=["catalogue"])
def templates():
    """Public static catalogue; no customer data. All templates are planned, not trained."""
    path = ROOT / "packages/schemas/functions/catalogue.json"
    return json.loads(path.read_text())
