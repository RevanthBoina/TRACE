"""FastAPI application for TRACE video upload service."""

import hashlib
import uuid
from contextlib import asynccontextmanager

import boto3
from fastapi import FastAPI, File, HTTPException, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.config import settings
from backend.database import get_db, check_duplicate, save_upload, Upload
from sqlalchemy.orm import Session


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
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class UploadResponse(BaseModel):
    """Response model for upload endpoint."""
    job_id: str
    status: str
    message: str


@app.post("/upload", response_model=UploadResponse)
async def upload_video(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a video file.
    
    Computes SHA-256 hash, checks for duplicates, and uploads to S3.
    """
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    content_type = file.content_type or ""
    if not content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="File must be a video")
    
    # Read file content
    content = await file.read()
    
    # Compute SHA-256 hash
    file_hash = hashlib.sha256(content).hexdigest()
    
    # Check for duplicate
    existing = check_duplicate(db, file_hash)
    if existing:
        return UploadResponse(
            job_id=str(existing.id),
            status="duplicate",
            message="File already uploaded"
        )
    
    # Upload to S3
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
    
    # Save to database
    upload = save_upload(db, file_hash, s3_key, file.filename)
    
    return UploadResponse(
        job_id=str(upload.id),
        status="uploaded",
        message="File uploaded successfully"
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
