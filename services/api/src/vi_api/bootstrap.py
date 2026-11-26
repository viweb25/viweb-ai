import re
from secrets import token_hex

from fastapi import FastAPI, Request

from vi_api.interfaces.http.controllers.auth import router as auth_router
from vi_api.interfaces.http.controllers.catalogue import router as catalogue_router
from vi_api.interfaces.http.controllers.demo_examples import router as demo_examples_router
from vi_api.interfaces.http.controllers.health import router as health_router
from vi_api.interfaces.http.controllers.inspection import router as inspection_router
from vi_api.interfaces.http.controllers.training_datasets import router as training_datasets_router
from vi_api.interfaces.http.controllers.training_jobs import router as training_jobs_router
from vi_api.interfaces.http.controllers.workspaces import router as workspaces_router
from vi_api.interfaces.http.errors import register_error_handlers

REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
}

app = FastAPI(title="VI WebSync API", version="0.1.0")
register_error_handlers(app)
for router in (
    health_router,
    catalogue_router,
    demo_examples_router,
    auth_router,
    inspection_router,
    training_datasets_router,
    training_jobs_router,
    workspaces_router,
):
    app.include_router(router)


@app.middleware("http")
async def request_context(request: Request, call_next):
    """Tag each request with an ID for log correlation and add security headers."""
    supplied = request.headers.get("x-request-id", "")
    request.state.request_id = supplied if REQUEST_ID.fullmatch(supplied) else token_hex(8)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    if request.url.path.startswith("/api/v1/auth/"):
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
    return response
