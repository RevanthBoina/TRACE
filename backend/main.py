"""FastAPI application for TRACE video upload service."""

import hashlib
import uuid
import asyncio
import time
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional
from collections import defaultdict
from threading import Lock

import boto3
from fastapi import FastAPI, File, HTTPException, UploadFile, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from celery import Celery
from celery.result import AsyncResult

from backend.config import settings
from backend.database import get_db, check_duplicate, save_upload, get_upload_by_id, update_upload_status, Upload
from sqlalchemy.orm import Session

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================
# METRICS COLLECTION
# ============================================
class MetricsCollector:
    """Thread-safe metrics collector for TRACE backend."""
    
    def __init__(self):
        self._lock = Lock()
        self._counters = defaultdict(int)
        self._processing_times = defaultdict(list)
        self._start_time = time.time()
    
    def increment(self, metric_name: str, value: int = 1):
        """Increment a counter metric."""
        with self._lock:
            self._counters[f"trace_{metric_name}"] += value
    
    def record_processing_time(self, endpoint: str, duration_ms: float):
        """Record processing time for an endpoint."""
        with self._lock:
            key = f"trace_{endpoint}_duration_ms"
            self._processing_times[key].append(duration_ms)
            # Keep only last 1000 measurements
            if len(self._processing_times[key]) > 1000:
                self._processing_times[key] = self._processing_times[key][-1000:]
    
    def get_metrics(self) -> dict:
        """Get all current metrics."""
        with self._lock:
            uptime = time.time() - self._start_time
            metrics = {
                "uptime_seconds": uptime,
                "uptime_human": f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m",
            }
            
            # Add counters
            for key, value in self._counters.items():
                metrics[key] = value
            
            # Calculate average processing times
            for key, values in self._processing_times.items():
                if values:
                    metrics[f"{key}_avg"] = sum(values) / len(values)
                    metrics[f"{key}_count"] = len(values)
            
            return metrics
    
    def reset(self):
        """Reset all metrics."""
        with self._lock:
            self._counters.clear()
            self._processing_times.clear()
            self._start_time = time.time()

# Global metrics collector
metrics = MetricsCollector()

# Celery configuration
celery_app = Celery(
    "trace_worker",
    broker=settings.CELERY_BROKER_URL or "redis://localhost:6379/0",
    backend=settings.CELERY_RESULT_BACKEND or "redis://localhost:6379/0"
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)


@celery_app.task(name="process_video_task", bind=True)
def process_video_task(self, job_id: str, s3_key: str, watermark_message: str):
    """
    Celery task to process video watermarking.
    Runs in background worker.
    """
    from backend.workers.watermark_worker import WatermarkWorker
    
    self.update_state(state="PROCESSING", meta={"progress": 10})
    
    worker = WatermarkWorker(
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        aws_region=settings.AWS_REGION,
        input_bucket=settings.S3_UPLOAD_BUCKET,
        output_bucket=settings.S3_OUTPUT_BUCKET,
        trace_key_pem=settings.trace_key_pem
    )
    
    self.update_state(state="PROCESSING", meta={"progress": 20})
    result = worker.process_video_sync(job_id, s3_key, watermark_message)
    self.update_state(state="SUCCESS", meta=result)
    
    return result


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    yield


app = FastAPI(
    title="TRACE API",
    description="Video upload service for TRACE application",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for API access
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class UploadResponse(BaseModel):
    """Response model for upload endpoint."""
    job_id: str
    status: str
    message: str
    celery_task_id: Optional[str] = None


class JobStatusResponse(BaseModel):
    """Response model for job status endpoint."""
    job_id: str
    status: str
    progress: int
    output_key: Optional[str] = None
    error: Optional[str] = None
    message: str


@app.post("/upload", response_model=UploadResponse)
async def upload_video(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a video file.

    Computes SHA-256 hash, checks for duplicates, and triggers watermark processing.
    """
    start_time = time.time()
    metrics.increment("upload_requests_total")
    
    # Validate file type
    if not file.filename:
        metrics.increment("upload_errors_invalid_file")
        raise HTTPException(status_code=400, detail="No filename provided")

    content_type = file.content_type or ""
    if not content_type.startswith("video/"):
        metrics.increment("upload_errors_invalid_file")
        raise HTTPException(status_code=400, detail="File must be a video")

    # Read file content
    content = await file.read()
    file_size = len(content)
    metrics.increment("upload_bytes_total", file_size)

    # Compute SHA-256 hash
    file_hash = hashlib.sha256(content).hexdigest()

    # Check for duplicate
    existing = check_duplicate(db, file_hash)
    if existing:
        metrics.increment("upload_duplicates_total")
        logger.info(f"Duplicate upload detected: {file.filename}")
        return UploadResponse(
            job_id=str(existing.id),
            status="duplicate",
            message="File already uploaded"
        )

    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Upload to S3
    s3_key = f"uploads/{job_id}/{file.filename}"

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
        metrics.increment("upload_s3_success_total")
    except Exception as e:
        metrics.increment("upload_s3_errors_total")
        logger.error(f"S3 upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"S3 upload failed: {str(e)}")
    
    # Save to database
    upload = save_upload(db, file_hash, s3_key, file.filename, job_id=job_id)

    # Trigger watermark processing via Celery
    watermark_message = f"TRACE|{upload.id}|{datetime.utcnow().isoformat()}"
    
    celery_task_id = None
    try:
        celery_task = process_video_task.apply_async(
            args=[job_id, s3_key, watermark_message],
            task_id=job_id
        )
        celery_task_id = celery_task.id
        metrics.increment("celery_tasks_created_total")
    except Exception as e:
        logger.error(f"Celery task creation failed: {e}")
        metrics.increment("celery_tasks_failed_total")

    # Record upload time
    upload_duration_ms = (time.time() - start_time) * 1000
    metrics.record_processing_time("upload", upload_duration_ms)
    logger.info(f"Upload processed: {job_id} in {upload_duration_ms:.2f}ms")

    return UploadResponse(
        job_id=job_id,
        status="processing",
        message="File uploaded, watermark processing started",
        celery_task_id=celery_task_id
    )


@app.get("/job/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """
    Get the status of a video processing job.
    Frontend polls this endpoint to track progress.
    """
    metrics.increment("job_status_requests_total")
    
    # Check Celery task status first
    celery_result = AsyncResult(job_id, app=celery_app)
    
    if celery_result.state == "PENDING":
        # Check database for job
        upload = get_upload_by_id(db, job_id)
        if not upload:
            metrics.increment("job_status_errors_not_found")
            raise HTTPException(status_code=404, detail="Job not found")
        
        return JobStatusResponse(
            job_id=job_id,
            status=upload.status or "pending",
            progress=0,
            message="Job is queued"
        )
    elif celery_result.state == "PROCESSING":
        meta = celery_result.info if isinstance(celery_result.info, dict) else {}
        return JobStatusResponse(
            job_id=job_id,
            status="processing",
            progress=meta.get("progress", 50),
            message="Processing video..."
        )
    elif celery_result.state == "SUCCESS":
        result = celery_result.result
        # Update database
        update_upload_status(db, job_id, "completed", result.get("output_key"))
        metrics.increment("watermark_completed_total")
        logger.info(f"Watermark completed: {job_id}")
        
        return JobStatusResponse(
            job_id=job_id,
            status="completed",
            progress=100,
            output_key=result.get("output_key"),
            message="Watermarking complete"
        )
    elif celery_result.state == "FAILURE":
        error_msg = str(celery_result.info) if celery_result.info else "Unknown error"
        update_upload_status(db, job_id, "failed", error=error_msg)
        metrics.increment("watermark_failed_total")
        logger.error(f"Watermark failed: {job_id} - {error_msg}")
        
        return JobStatusResponse(
            job_id=job_id,
            status="failed",
            progress=0,
            error=error_msg,
            message="Processing failed"
        )
    else:
        return JobStatusResponse(
            job_id=job_id,
            status=celery_result.state.lower(),
            progress=0,
            message=f"Job state: {celery_result.state}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/metrics")
async def get_metrics():
    """Get backend metrics for monitoring."""
    return metrics.get_metrics()
