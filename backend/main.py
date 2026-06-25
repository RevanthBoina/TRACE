"""FastAPI application for TRACE video upload service."""

import hashlib
import uuid
import asyncio
from contextlib import asynccontextmanager

import boto3
from fastapi import FastAPI, File, HTTPException, UploadFile, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.config import settings
from backend.database import get_db, check_duplicate, save_upload, update_upload_status, Upload, init_db
from backend.workers.watermark_worker import WatermarkWorker
from sqlalchemy.orm import Session


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    init_db()
    yield


app = FastAPI(
    title="TRACE API",
    description="Video upload service for TRACE application",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS - update with your Vercel/frontend domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class UploadResponse(BaseModel):
    """Response model for upload endpoint."""
    job_id: str
    status: str
    message: str
    fingerprint: str | None = None


def get_watermark_worker() -> WatermarkWorker:
    """Create a WatermarkWorker instance with current settings."""
    return WatermarkWorker(
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        aws_region=settings.AWS_REGION,
        input_bucket=settings.S3_UPLOAD_BUCKET,
        output_bucket=settings.S3_OUTPUT_BUCKET,
    )


async def process_watermark(job_id: str, s3_key: str, fingerprint: str, db: Session):
    """
    Background task to process video watermark.
    Downloads from S3, watermarks, uploads result, updates DB.
    """
    try:
        worker = get_watermark_worker()
        result = await worker.process_video(
            job_id=job_id,
            s3_key=s3_key,
            watermark_message=fingerprint
        )
        
        # Update upload status in database
        if result.get("status") == "completed":
            update_upload_status(db, job_id, "watermarked", result.get("output_key"))
            print(f"✅ Job {job_id}: Watermarking completed")
        else:
            update_upload_status(db, job_id, "failed", error=result.get("error"))
            print(f"❌ Job {job_id}: Watermarking failed - {result.get('error')}")
            
    except Exception as e:
        print(f"❌ Job {job_id}: Unexpected error - {str(e)}")
        update_upload_status(db, job_id, "failed", error=str(e))


@app.post("/upload", response_model=UploadResponse)
async def upload_video(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Upload a video file.
    
    Computes SHA-256 hash, checks for duplicates, uploads to S3,
    and triggers background watermarking.
    """
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    content_type = file.content_type or ""
    if not content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="File must be a video")
    
    # Read file content
    content = await file.read()
    
    # Compute SHA-256 hash (this becomes our fingerprint)
    file_hash = hashlib.sha256(content).hexdigest()
    
    # Check for duplicate
    existing = check_duplicate(db, file_hash)
    if existing:
        return UploadResponse(
            job_id=str(existing.id),
            status="duplicate",
            message="File already uploaded"
        )
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    s3_key = f"uploads/{job_id}/{file.filename}"
    
    # Upload to S3
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
    
    # Save to database with "processing" status
    upload = save_upload(db, file_hash, s3_key, file.filename, status="processing")
    
    # Trigger background watermarking
    if background_tasks:
        background_tasks.add_task(process_watermark, job_id, s3_key, file_hash, db)
    
    return UploadResponse(
        job_id=job_id,
        status="processing",
        message="Video uploaded, watermarking in progress",
        fingerprint=file_hash[:16]  # First 16 chars of SHA-256
    )


@app.get("/job/{job_id}")
async def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """Get the status of a watermarking job."""
    from backend.database import get_upload_by_id
    
    upload = get_upload_by_id(db, job_id)
    if not upload:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "job_id": str(upload.id),
        "status": upload.status,
        "filename": upload.filename,
        "fingerprint": upload.file_hash[:16],
        "created_at": upload.created_at.isoformat() if upload.created_at else None,
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
