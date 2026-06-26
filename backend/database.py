"""Database module for TRACE backend."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine, String, DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from backend.config import settings


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""
    pass


class Upload(Base):
    """Model for tracking uploaded files."""

    __tablename__ = "uploads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=True)
    file_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    s3_key: Mapped[str] = mapped_column(String(512))
    filename: Mapped[str] = mapped_column(String(255))
    output_key: Mapped[str] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    error: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_duplicate(db, file_hash: str) -> Upload | None:
    """Check if a file hash already exists in the database."""
    return db.query(Upload).filter(Upload.file_hash == file_hash).first()


def save_upload(db, file_hash: str, s3_key: str, filename: str, job_id: Optional[str] = None) -> Upload:
    """Save a new upload record to the database."""
    upload = Upload(
        file_hash=file_hash,
        s3_key=s3_key,
        filename=filename,
        job_id=job_id,
        status="uploaded"
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)
    return upload


def get_upload_by_id(db, job_id: str) -> Upload | None:
    """Get upload by job_id."""
    return db.query(Upload).filter(Upload.job_id == job_id).first()


def update_upload_status(db, job_id: str, status: str, output_key: Optional[str] = None, error: Optional[str] = None):
    """Update the status of an upload."""
    upload = get_upload_by_id(db, job_id)
    if upload:
        upload.status = status
        if output_key:
            upload.output_key = output_key
        if error:
            upload.error = error
        db.commit()
        return upload
    return None
