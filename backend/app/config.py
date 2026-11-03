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

    database_url: str = "postgresql+asyncpg://sehat_app:sehat_app@localhost:55432/sehat"
    migration_database_url: str = "postgresql+asyncpg://sehat:sehat@localhost:55432/sehat"
    app_db_role: str = "sehat_app"

    redis_dsn: str = "redis://localhost:6379/0"

    minio_endpoint: str = "http://localhost:9000"
    minio_public_url: str = "http://localhost:9000"
    minio_root_user: str = "sehat"
    minio_root_password: str = "sehat-secret"
    minio_bucket: str = "sehat-bridge"

    max_file_bytes: int = 25 * 1024 * 1024
    allowed_content_types: tuple[str, ...] = (
        "image/png",
        "image/jpeg",
        "application/pdf",
        "text/plain",
        "text/csv",
    )
    quota_bytes: int = 1024 * 1024 * 1024
    upload_url_ttl_seconds: int = 600
    download_url_ttl_seconds: int = 300

    site_url: str = "http://localhost:8080"

    secret_key: str = "dev-only-change-me-32-bytes-minimum"
    app_encryption_key: str = "dev-only-change-me-32-bytes-minimum"

    jwt_issuer: str = "sehat-bridge"
    jwt_audience: str = "sehat-bridge-api"
    access_token_ttl_seconds: int = 900
    refresh_token_ttl_days: int = 30
    registration_enabled: bool = True
    demo_password: str = "demo-password-123"
    platform_admin_token: str = "dev-platform-token"

    login_limit: int = 5
    login_window_seconds: int = 300
    register_limit: int = 10
    register_window_seconds: int = 3600
    refresh_limit: int = 30
    refresh_window_seconds: int = 3600

    @property
    def is_prod(self) -> bool:
        return self.env == "prod"


@lru_cache
def get_settings() -> Settings:
    return Settings()
