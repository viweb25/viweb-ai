from celery import Celery
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    redis_url: str = "redis://127.0.0.1:16379/0"


app = Celery("vi_websync", broker=Settings().redis_url)
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_ignore_result=True,
    worker_prefetch_multiplier=1,
)


@app.task(name="vi.health.ping")
def ping():
    """Infrastructure smoke task only; no training or customer data access."""
    return {"status": "ok", "service": "worker"}
