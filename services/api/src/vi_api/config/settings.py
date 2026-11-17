from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql+asyncpg://vi:vi_local@127.0.0.1:15432/viws"
    inference_url: str = "http://127.0.0.1:8001"
