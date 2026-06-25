"""Configuration module for TRACE backend."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_REGION: str = "eu-north-1"
    S3_UPLOAD_BUCKET: str = "trace-upload-temp"
    S3_OUTPUT_BUCKET: str = "trace-watermarked-out"
    DATABASE_URL: str | None = None  # PostgreSQL on RDS in production
    RESEND_API_KEY: str | None = None

    model_config = {
        "extra": "ignore",  # Allow extra env vars
    }


settings = Settings()
