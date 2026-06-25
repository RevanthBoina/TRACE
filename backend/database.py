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


def save_upload(db, file_hash: str, s3_key: str, filename: str) -> Upload:
    """Save a new upload record to the database."""
    upload = Upload(
        file_hash=file_hash,
        s3_key=s3_key,
        filename=filename,
        status="uploaded"
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)
    return upload
