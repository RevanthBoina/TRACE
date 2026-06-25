"""Database module for TRACE backend."""

import uuid
from datetime import datetime

from sqlalchemy import create_engine, String, DateTime, func, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from backend.config import settings


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""
    pass


class Upload(Base):
    """Model for tracking uploaded files."""
    
    __tablename__ = "uploads"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    file_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    s3_key: Mapped[str] = mapped_column(String(512))
    filename: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    status: Mapped[str] = mapped_column(String(50), default="pending")
    error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)


# Use SQLite for local development, PostgreSQL for production
engine = create_engine(
    settings.DATABASE_URL, 
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize the database tables."""
    Base.metadata.create_all(bind=engine)


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


def save_upload(db, file_hash: str, s3_key: str, filename: str, status: str = "uploaded") -> Upload:
    """Save a new upload record to the database."""
    upload = Upload(
        file_hash=file_hash,
        s3_key=s3_key,
        filename=filename,
        status=status
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)
    return upload


def get_upload_by_id(db, upload_id: str) -> Upload | None:
    """Get an upload record by ID."""
    return db.query(Upload).filter(Upload.id == upload_id).first()


def update_upload_status(db, upload_id: str, status: str, output_key: str = None, error: str = None):
    """Update the status of an upload record."""
    upload = get_upload_by_id(db, upload_id)
    if upload:
        upload.status = status
        if output_key:
            upload.s3_key = output_key
        if error:
            upload.error_message = error
        db.commit()
