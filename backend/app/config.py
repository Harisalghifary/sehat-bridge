"""Application settings, loaded once and cached."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: str = "dev"
    version: str = "0.1.0"

    database_url: str = "postgresql+asyncpg://sehat:sehat@localhost:5432/sehat"
    redis_dsn: str = "redis://localhost:6379/0"

    minio_endpoint: str = "http://localhost:9000"
    minio_public_url: str = "http://localhost:9000"
    minio_root_user: str = "sehat"
    minio_root_password: str = "sehat-secret"
    minio_bucket: str = "sehat-bridge"

    site_url: str = "http://localhost:8080"

    secret_key: str = "dev-only-change-me"
    app_encryption_key: str = "dev-only-change-me-32-bytes-minimum"

    @property
    def is_prod(self) -> bool:
        return self.env == "prod"


@lru_cache
def get_settings() -> Settings:
    return Settings()
