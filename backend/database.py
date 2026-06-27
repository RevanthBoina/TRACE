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


class RegisteredVideo(Base):
    """Model for videos registered for infringement monitoring."""

    __tablename__ = "registered_videos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(512))
    platform: Mapped[str] = mapped_column(String(64))
    canonical_url: Mapped[str] = mapped_column(String(1024))
    status: Mapped[str] = mapped_column(String(50), default="active")
    failure_reason: Mapped[str] = mapped_column(Text, nullable=True)
    last_scanned: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InfringingLink(Base):
    """Model for detected infringing copies of registered videos."""

    __tablename__ = "infringing_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    registered_video_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    url: Mapped[str] = mapped_column(String(1024))
    confidence: Mapped[int] = mapped_column(default=0)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    dmca_filed: Mapped[bool] = mapped_column(default=False)


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


def get_all_registered_videos(db) -> list[RegisteredVideo]:
    """Get all registered videos ordered by creation date descending."""
    return db.query(RegisteredVideo).order_by(RegisteredVideo.created_at.desc()).all()


def get_infringing_links(db, registered_video_id: uuid.UUID) -> list[InfringingLink]:
    """Get all infringing links for a registered video."""
    return db.query(InfringingLink).filter(
        InfringingLink.registered_video_id == registered_video_id
    ).order_by(InfringingLink.detected_at.desc()).all()


def save_registered_video(db, job_id: str, title: str, platform: str, canonical_url: str) -> RegisteredVideo:
    """Save a new registered video record."""
    video = RegisteredVideo(job_id=job_id, title=title, platform=platform, canonical_url=canonical_url)
    db.add(video)
    db.commit()
    db.refresh(video)
    return video


def save_infringing_link(db, registered_video_id: uuid.UUID, url: str, confidence: int) -> InfringingLink:
    """Save a detected infringing link."""
    link = InfringingLink(registered_video_id=registered_video_id, url=url, confidence=confidence)
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def mark_dmca_filed(db, link_id: uuid.UUID) -> InfringingLink | None:
    """Mark an infringing link as DMCA filed."""
    link = db.query(InfringingLink).filter(InfringingLink.id == link_id).first()
    if link:
        link.dmca_filed = True
        db.commit()
        return link
    return None
