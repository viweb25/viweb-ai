from fastapi import FastAPI

from vi_api.interfaces.http.controllers.catalogue import router as catalogue_router
from vi_api.interfaces.http.controllers.health import router as health_router
from vi_api.interfaces.http.errors import register_error_handlers

app = FastAPI(title="VI WebSync API", version="0.1.0")
register_error_handlers(app)
app.include_router(health_router)
app.include_router(catalogue_router)
