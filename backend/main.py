"""FastAPI application for TRACE video upload service."""

import hashlib
import uuid
from contextlib import asynccontextmanager

import boto3
from fastapi import FastAPI, File, HTTPException, UploadFile, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.config import settings
from backend.database import get_db, check_duplicate, save_upload, Upload, _init_db
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


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
