"""Configuration module for TRACE backend."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_REGION: str = "us-east-1"
    S3_UPLOAD_BUCKET: str | None = None
    S3_OUTPUT_BUCKET: str | None = None
    DATABASE_URL: str = "postgresql://localhost:5432/trace"
    
    # Redis for Celery
    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str | None = None
    
    # PEM Key (from Vercel env or local file)
    trace_key_pem: str | None = None

    # CORS — comma-separated list of allowed origins
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
