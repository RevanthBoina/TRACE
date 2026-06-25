"""Configuration module for TRACE backend."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_REGION: str = "us-east-1"
    S3_UPLOAD_BUCKET: str | None = None
    S3_OUTPUT_BUCKET: str | None = None
    DATABASE_URL: str = "sqlite:///./trace.db"
    USE_SQLITE: bool = True  # Fallback to SQLite if PostgreSQL unavailable

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
