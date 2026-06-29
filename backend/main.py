"""FastAPI application for TRACE video upload service."""

import hashlib
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

import boto3
from fastapi import FastAPI, File, HTTPException, UploadFile, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.config import settings
from backend.database import (
    get_db, check_duplicate, save_upload, Upload, _init_db,
)
from sqlalchemy.orm import Session


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="TRACE API",
    description="Video upload service for TRACE application",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class UploadResponse(BaseModel):
    job_id: str
    status: str
    message: str


class StatusResponse(BaseModel):
    job_id: str
    status: str
    output_key: str | None = None


class InfringingLinkResponse(BaseModel):
    id: str
    url: str
    detected_at: str
    confidence: float


class RegisteredVideoResponse(BaseModel):
    id: str
    title: str
    platform: str
    status: str
    last_scanned: str | None = None
    already_protected: bool = False
    failure_reason: str | None = None
    infringing_links: list[InfringingLinkResponse] = []


class RegisterLinkRequest(BaseModel):
    link: str
    platform: str


class DMCARequest(BaseModel):
    link_id: str
    platform: str
    dmca_url: str


def _run_watermark(job_id: str, s3_key: str, filename: str):
    """Background task: watermark the uploaded video."""
    from backend.workers.watermark_worker import WatermarkWorker
    worker = WatermarkWorker(
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        aws_region=settings.AWS_REGION,
        input_bucket=settings.S3_UPLOAD_BUCKET,
        output_bucket=settings.S3_OUTPUT_BUCKET,
    )
    result = worker.process_video_sync(job_id, s3_key, f"TRACE|{job_id}")

    # Update DB status
    try:
        _init_db()
        from backend.database import SessionLocal
        db = SessionLocal()
        upload = db.query(Upload).filter(Upload.id == uuid.UUID(job_id)).first()
        if upload:
            upload.status = result["status"]
            if result.get("output_key"):
                upload.output_key = result["output_key"]
            db.commit()
        db.close()
    except Exception as e:
        print(f"DB status update failed: {e}")


@app.post("/upload", response_model=UploadResponse)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    content_type = file.content_type or ""
    if not content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="File must be a video")

    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()

    existing = check_duplicate(db, file_hash)
    if existing:
        return UploadResponse(
            job_id=str(existing.id),
            status="duplicate",
            message="File already uploaded",
        )

    s3_key = f"uploads/{uuid.uuid4()}/{file.filename}"

    try:
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )
        s3_client.put_object(
            Bucket=settings.S3_UPLOAD_BUCKET,
            Key=s3_key,
            Body=content,
            ContentType=content_type,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"S3 upload failed: {str(e)}")

    upload = save_upload(db, file_hash, s3_key, file.filename)
    job_id = str(upload.id)

    background_tasks.add_task(_run_watermark, job_id, s3_key, file.filename)

    return UploadResponse(
        job_id=job_id,
        status="processing",
        message="File uploaded, watermarking in progress",
    )


@app.get("/status/{job_id}", response_model=StatusResponse)
@app.get("/job/{job_id}", response_model=StatusResponse)
async def get_status(job_id: str, db: Session = Depends(get_db)):
    try:
        upload = db.query(Upload).filter(Upload.id == uuid.UUID(job_id)).first()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job_id")
    if not upload:
        raise HTTPException(status_code=404, detail="Job not found")
    return StatusResponse(
        job_id=str(upload.id),
        status=upload.status,
        output_key=getattr(upload, "output_key", None),
    )


class DownloadResponse(BaseModel):
    download_url: str
    expires_in: int  # seconds


@app.get("/download/{job_id}", response_model=DownloadResponse)
async def get_download_url(job_id: str, db: Session = Depends(get_db)):
    """Generate a presigned S3 URL for downloading the watermarked video."""
    try:
        upload = db.query(Upload).filter(Upload.id == uuid.UUID(job_id)).first()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job_id")
    if not upload:
        raise HTTPException(status_code=404, detail="Job not found")
    if upload.status != "completed" or not upload.output_key:
        raise HTTPException(status_code=400, detail="Watermarked video not ready yet")

    try:
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )
        url = s3_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.S3_OUTPUT_BUCKET,
                "Key": upload.output_key,
            },
            ExpiresIn=3600,  # 1 hour
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate download URL: {str(e)}")

    return DownloadResponse(download_url=url, expires_in=3600)


# In-memory dashboard store (replace with DB in production)
_dashboard_store: dict[str, dict] = {}


@app.get("/dashboard", response_model=list[RegisteredVideoResponse])
async def get_dashboard(db: Session = Depends(get_db)):
    """Get all registered videos with their infringing links."""
    videos = []
    for vid in _dashboard_store.values():
        videos.append(RegisteredVideoResponse(
            id=vid.get("id", ""),
            title=vid.get("title", ""),
            platform=vid.get("platform", ""),
            status=vid.get("status", "Active"),
            last_scanned=vid.get("last_scanned"),
            already_protected=vid.get("already_protected", False),
            failure_reason=vid.get("failure_reason"),
            infringing_links=[
                InfringingLinkResponse(
                    id=link["id"],
                    url=link["url"],
                    detected_at=link["detected_at"],
                    confidence=link["confidence"],
                )
                for link in vid.get("infringing_links", [])
            ],
        ))
    return videos


@app.post("/dashboard/register")
async def register_link(req: RegisterLinkRequest, db: Session = Depends(get_db)):
    """Register a video link for monitoring."""
    video_id = str(uuid.uuid4())
    video = {
        "id": video_id,
        "title": req.link.split("/")[-1][:100] or "Untitled Video",
        "platform": req.platform,
        "status": "Active",
        "last_scanned": None,
        "already_protected": False,
        "failure_reason": None,
        "infringing_links": [],
        "registered_link": req.link,
    }
    _dashboard_store[video_id] = video
    return {"id": video_id, "status": "registered", "message": "Link registered for monitoring"}


@app.post("/dashboard/dmca/{link_id}")
async def file_dmca(link_id: str, req: DMCARequest, db: Session = Depends(get_db)):
    """Record that a DMCA takedown was filed for an infringing link."""
    for vid in _dashboard_store.values():
        for link in vid.get("infringing_links", []):
            if link["id"] == link_id:
                link["dmca_filed"] = True
                link["dmca_filed_at"] = str(datetime.utcnow())
                link["dmca_platform_url"] = req.dmca_url
                return {"status": "ok", "message": "DMCA filing recorded"}
    return {"status": "not_found", "message": "Link not found"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
