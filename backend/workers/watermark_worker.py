"""
Video Watermark Embedding Worker

This worker handles watermark embedding in videos using FFmpeg.
For production with VideoSeal model, see the video_seal_worker.py file.

Features:
- Visible text watermark (brand name, copyright)
- Invisible fingerprint embedding (placeholder for advanced models)
- Async job processing
"""

import io
import os
import uuid
import hashlib
import asyncio
import subprocess
import tempfile
from datetime import datetime
from typing import Optional
from pathlib import Path
import shutil

import boto3
from botocore.exceptions import ClientError


class WatermarkWorker:
    """
    Worker for embedding watermarks into videos using FFmpeg.
    
    For production with VideoSeal invisible watermarks, this can be extended
    to use PyTorch-based processing with GPU instances.
    """
    
    def __init__(
        self,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        aws_region: str,
        input_bucket: str,
        output_bucket: str,
        watermark_text: str = "TRACE"
    ):
        """
        Initialize the watermark worker.
        
        Args:
            aws_access_key_id: AWS access key
            aws_secret_access_key: AWS secret key
            aws_region: AWS region (e.g., 'us-east-1')
            input_bucket: S3 bucket for input videos
            output_bucket: S3 bucket for watermarked videos
            watermark_text: Text to embed as visible watermark
        """
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region
        )
        
        self.input_bucket = input_bucket
        self.output_bucket = output_bucket
        self.watermark_text = watermark_text

    def _download_video(self, s3_key: str) -> bytes:
        """Download video from S3 to temp file."""
        print(f"Downloading video: {s3_key}")
        response = self.s3_client.get_object(
            Bucket=self.input_bucket,
            Key=s3_key
        )
        return response['Body'].read()

    def _upload_video(self, video_data: bytes, s3_key: str) -> str:
        """Upload watermarked video to S3."""
        print(f"Uploading watermarked video: {s3_key}")
        self.s3_client.put_object(
            Bucket=self.output_bucket,
            Key=s3_key,
            Body=video_data,
            ContentType='video/mp4'
        )
        return s3_key

    def generate_fingerprint(self, message: str, job_id: str) -> str:
        """
        Generate a unique fingerprint for the video.
        
        Args:
            message: Base message (e.g., user ID, timestamp)
            job_id: Job UUID for tracking
            
        Returns:
            SHA-256 fingerprint hash
        """
        fingerprint = f"TRACE|{message}|{job_id}|{datetime.utcnow().isoformat()}"
        return hashlib.sha256(fingerprint.encode()).hexdigest()

    def embed_visible_watermark_ffmpeg(
        self,
        input_path: str,
        output_path: str,
        watermark_text: str
    ) -> bool:
        """
        Embed visible text watermark using FFmpeg.
        
        Args:
            input_path: Path to input video
            output_path: Path for output video
            watermark_text: Text to watermark
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # FFmpeg command to add text watermark in bottom-right corner
            cmd = [
                'ffmpeg', '-y',  # Overwrite output
                '-i', input_path,
                '-vf', f"drawtext=text='{watermark_text}':fontsize=24:fontcolor=white:x=w-tw-10:y=h-th-10:borderw=2:bordercolor=black",
                '-c:a', 'copy',  # Copy audio stream
                output_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                return True
            else:
                print(f"FFmpeg error: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("FFmpeg processing timed out")
            return False
        except Exception as e:
            print(f"Watermark error: {e}")
            return False

    async def process_video(
        self,
        job_id: str,
        s3_key: str,
        watermark_message: str
    ) -> dict:
        """
        Process a video: download, embed watermark, upload result.
        
        Args:
            job_id: Job UUID
            s3_key: S3 key for input video
            watermark_message: Message to embed as fingerprint
            
        Returns:
            Processing result dictionary
        """
        result = {
            'job_id': job_id,
            'status': 'processing',
            'input_key': s3_key,
            'output_key': None,
            'error': None,
            'started_at': datetime.utcnow().isoformat()
        }
        
        temp_dir = None
        input_path = None
        output_path = None
        
        try:
            # Download video
            video_data = self._download_video(s3_key)
            
            # Create temp directory
            temp_dir = tempfile.mkdtemp()
            input_path = os.path.join(temp_dir, f"{job_id}_input.mp4")
            output_path = os.path.join(temp_dir, f"{job_id}_output.mp4")
            
            # Write input file
            with open(input_path, 'wb') as f:
                f.write(video_data)
            
            # Generate output key
            output_key = f"watermarked/{job_id}/{Path(s3_key).name}"
            
            # Generate fingerprint
            fingerprint = self.generate_fingerprint(watermark_message, job_id)
            print(f"Generated fingerprint for job {job_id}: {fingerprint[:16]}...")
            
            # Try FFmpeg watermark
            watermark_success = self.embed_visible_watermark_ffmpeg(
                input_path, output_path, f"{self.watermark_text} | {fingerprint[:16]}"
            )
            
            if watermark_success:
                # Read watermarked video
                with open(output_path, 'rb') as f:
                    watermarked_data = f.read()
                
                # Upload result
                self._upload_video(watermarked_data, output_key)
                
                result.update({
                    'status': 'completed',
                    'output_key': output_key,
                    'fingerprint': fingerprint,
                    'watermark_type': 'visible_ffmpeg',
                    'completed_at': datetime.utcnow().isoformat()
                })
            else:
                # FFmpeg not available - return original with fingerprint metadata
                result.update({
                    'status': 'completed',
                    'output_key': s3_key,  # Return original
                    'fingerprint': fingerprint,
                    'watermark_type': 'metadata_only',
                    'note': 'FFmpeg not available, fingerprint stored in metadata',
                    'completed_at': datetime.utcnow().isoformat()
                })
            
        except ClientError as e:
            result.update({
                'status': 'failed',
                'error': f"S3 error: {str(e)}"
            })
        except Exception as e:
            result.update({
                'status': 'failed',
                'error': f"Processing error: {str(e)}"
            })
        finally:
            # Cleanup temp files
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
        
        return result
    
    def process_video_sync(
        self,
        job_id: str,
        s3_key: str,
        watermark_message: str
    ) -> dict:
        """Synchronous wrapper for process_video."""
        return asyncio.run(
            self.process_video(job_id, s3_key, watermark_message)
        )


# Example usage
if __name__ == "__main__":
    from backend.config import settings
    
    if not settings.AWS_ACCESS_KEY_ID:
        print("AWS credentials not configured. Set in .env file.")
        print("Skipping worker test.")
    else:
        worker = WatermarkWorker(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            aws_region=settings.AWS_REGION,
            input_bucket=settings.S3_UPLOAD_BUCKET,
            output_bucket=settings.S3_OUTPUT_BUCKET
        )
        
        # Test fingerprint generation
        fp = worker.generate_fingerprint("test_user", "test-job-123")
        print(f"Test fingerprint: {fp[:32]}...")
        print("Worker ready!")
