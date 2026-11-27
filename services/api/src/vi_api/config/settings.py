from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql+asyncpg://vi:vi_local@127.0.0.1:15432/viws"
    inference_url: str = "http://127.0.0.1:8001"
    redis_cache_url: str = ""
    demo_image_dir: str = Field(default="", validation_alias="VI_DEMO_IMAGE_DIR")
    training_image_dir: str = Field(default="", validation_alias="VI_TRAINING_IMAGE_DIR")
    training_run_dir: str = Field(default="", validation_alias="VI_TRAINING_RUN_DIR")
    app_origin: str = "http://127.0.0.1:3000"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_from: str = ""
    smtp_username: str = ""
    smtp_password: SecretStr = SecretStr("")
