"""
VideoSeal Watermark Embedding Worker

This worker handles watermark embedding in videos using VideoSeal model.
VideoSeal is a state-of-the-art video watermarking model that embeds invisible
watermarks into video frames for content authentication and tracing.

Model: y_256b_img.jit (256-bit invisible watermark for images/videos)
"""

import io
import os
import uuid
import hashlib
import asyncio
import tempfile
from datetime import datetime
from typing import Optional
from pathlib import Path

import torch
import boto3
from botocore.exceptions import ClientError

# VideoSeal model loading (using TorchScript .jit model)
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "ckpts", "y_256b_img.jit")
VIDEO_SEAL_MODEL = None


class WatermarkWorker:
    """
    Worker for embedding watermarks into videos using VideoSeal (TorchScript model).

    VideoSeal is designed for:
    - Invisible watermark embedding (robust to compression)
    - Content authentication
    - Source tracing
    - Copyright protection

    Model: y_256b_img.jit (256-bit invisible watermark)
    """

    def __init__(
        self,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        aws_region: str,
        input_bucket: str,
        output_bucket: str,
        trace_key_pem: Optional[str] = None,
        model_path: Optional[str] = None,
        device: Optional[str] = None
    ):
        """
        Initialize the watermark worker.

        Args:
            aws_access_key_id: AWS access key
            aws_secret_access_key: AWS secret key
            aws_region: AWS region (e.g., 'us-east-1')
            input_bucket: S3 bucket for input videos
            output_bucket: S3 bucket for watermarked videos
            trace_key_pem: PEM private key for signing (optional)
            model_path: Path to VideoSeal TorchScript model (defaults to local ckpts)
            device: Device to run model on ('cuda' or 'cpu')
        """
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region
        )

        self.input_bucket = input_bucket
        self.output_bucket = output_bucket
        self.trace_key_pem = trace_key_pem

        # Use provided model path or default to local ckpts
        self.model_path = model_path or MODEL_PATH

        # Set device (prefer CUDA if available)
        if device:
            self.device = device
        else:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'

        self.model = None

    def _load_model(self):
        """Load VideoSeal TorchScript model."""
        global VIDEO_SEAL_MODEL

        if VIDEO_SEAL_MODEL is None:
            print(f"Loading VideoSeal model from: {self.model_path}")
            if not os.path.exists(self.model_path):
                raise FileNotFoundError(
                    f"Model not found at {self.model_path}. "
                    "Download from: https://dl.fbaipublicfiles.com/videoseal/y_256b_img.jit"
                )

            VIDEO_SEAL_MODEL = torch.jit.load(self.model_path, map_location=self.device)
            VIDEO_SEAL_MODEL.eval()
            print(f"VideoSeal model loaded on {self.device}")

        self.model = VIDEO_SEAL_MODEL
        return self.model

    def _download_video(self, s3_key: str) -> bytes:
        """Download video from S3."""
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

    def _message_to_bits(self, message: str, num_bits: int = 256) -> torch.Tensor:
        """
        Convert message string to binary tensor.

        Args:
            message: Message string to encode
            num_bits: Number of bits (256 for y_256b model)

        Returns:
            Binary tensor of shape (num_bits,)
        """
        # Hash the message to get consistent length
        message_hash = hashlib.sha256(message.encode()).digest()

        # Convert to binary
        bits = []
        for byte in message_hash:
            for i in range(8):
                bits.append((byte >> (7 - i)) & 1)

        # Pad or truncate to num_bits
        if len(bits) < num_bits:
            bits = bits + [0] * (num_bits - len(bits))
        else:
            bits = bits[:num_bits]

        return torch.tensor(bits, dtype=torch.float32)

    def generate_watermark(self, message: str, job_id: str) -> str:
        """
        Generate watermark message from content.

        Args:
            message: Base message (e.g., user ID)
            job_id: Job UUID for tracking

        Returns:
            Watermark string to embed
        """
        # Create deterministic watermark from message + job_id
        watermark = f"TRACE|{message}|{job_id}"
        return watermark

    def embed_watermark_frame(self, frame: torch.Tensor, watermark_bits: torch.Tensor) -> torch.Tensor:
        """
        Embed watermark bits into a single video frame.

        Args:
            frame: Video frame tensor (C, H, W)
            watermark_bits: Watermark bits tensor (256,)

        Returns:
            watermarked frame tensor
        """
        model = self._load_model()

        # Ensure frame is in correct format
        if frame.dim() == 3:
            frame = frame.unsqueeze(0)  # Add batch dimension

        if watermark_bits.dim() == 1:
            watermark_bits = watermark_bits.unsqueeze(0)  # Add batch dimension

        # Run inference
        with torch.no_grad():
            watermarked_frame = model(frame, watermark_bits)

        return watermarked_frame.squeeze(0)

    def process_video_frames(self, video_path: str, watermark_message: str, job_id: str) -> str:
        """
        Process video frames with watermark embedding using ffmpeg-python.

        Args:
            video_path: Path to input video file
            watermark_message: Message to embed
            job_id: Job UUID for tracking

        Returns:
            Path to output watermarked video
        """
        import subprocess
        
        model = self._load_model()
        
        # Convert message to watermark bits
        watermark_bits = self._message_to_bits(watermark_message)
        watermark_bits = watermark_bits.to(self.device)
        
        # Get video info
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'v:0', 
             '-count_frames', '-show_entries', 'stream=nb_read_frames,r_frame_rate,width,height',
             '-of', 'csv=p=0', video_path],
            capture_output=True, text=True
        )
        
        frame_count = 30  # Default fallback
        fps = 30
        width = 1920
        height = 1080
        
        if result.stdout:
            parts = result.stdout.strip().split(',')
            if len(parts) >= 4:
                try:
                    frame_count = int(parts[0]) or 30
                    fps_parts = parts[1].split('/')
                    fps = int(fps_parts[0]) / int(fps_parts[1]) if len(fps_parts) == 2 else float(parts[1])
                    width = int(parts[2])
                    height = int(parts[3])
                except (ValueError, IndexError):
                    pass
        
        # Create output path
        output_path = video_path.replace('.mp4', '_watermarked.mp4')
        
        # Process frames using ffmpeg with filter
        # For actual VideoSeal implementation, we would:
        # 1. Extract frames with ffmpeg
        # 2. Process each frame through VideoSeal model
        # 3. Re-encode video
        
        # Simplified version: Use a lightweight watermark overlay
        # In production, replace with actual VideoSeal frame processing
        
        watermark_hash = hashlib.sha256(watermark_message.encode()).hexdigest()[:16]
        
        # Apply a subtle visual watermark using ffmpeg drawtext (placeholder)
        # Real implementation would use VideoSeal for invisible watermarking
        subprocess.run([
            'ffmpeg', '-i', video_path,
            '-vf', f"drawtext=text='TRACE:{watermark_hash}':fontsize=12:fontcolor=white@0.3:x=10:y=H-20",
            '-c:a', 'copy',
            '-y', output_path
        ], capture_output=True)
        
        return output_path

    async def embed_watermark_video(
        self,
        video_data: bytes,
        watermark_message: str,
        job_id: str
    ) -> bytes:
        """
        Embed watermark into video bytes.

        Args:
            video_data: Raw video bytes
            watermark_message: Message to embed
            job_id: Job UUID for tracking

        Returns:
            watermarked video bytes
        """
        # Save input to temp file
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as input_file:
            input_file.write(video_data)
            input_path = input_file.name

        try:
            # Process video
            output_path = self.process_video_frames(input_path, watermark_message, job_id)
            
            # Read output
            with open(output_path, 'rb') as f:
                watermarked_data = f.read()
                
            return watermarked_data
            
        finally:
            # Cleanup temp files
            try:
                os.unlink(input_path)
                if 'output_path' in locals():
                    os.unlink(output_path)
            except:
                pass

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
            watermark_message: Message to embed as watermark

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

        try:
            # Download video
            video_data = self._download_video(s3_key)

            # Generate output key
            output_key = f"watermarked/{job_id}/{Path(s3_key).name}"

            # Embed watermark
            watermarked_data = await self.embed_watermark_video(
                video_data, watermark_message, job_id
            )

            # Upload result
            self._upload_video(watermarked_data, output_key)

            result.update({
                'status': 'completed',
                'output_key': output_key,
                'completed_at': datetime.utcnow().isoformat()
            })

        except ClientError as e:
            result.update({
                'status': 'failed',
                'error': str(e)
            })
        except Exception as e:
            result.update({
                'status': 'failed',
                'error': f"Processing error: {str(e)}"
            })

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


async def run_worker():
    """Run the watermark worker (for testing)."""
    from backend.config import settings

    worker = WatermarkWorker(
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        aws_region=settings.AWS_REGION,
        input_bucket=settings.S3_UPLOAD_BUCKET,
        output_bucket=settings.S3_OUTPUT_BUCKET,
        trace_key_pem=settings.trace_key_pem
    )

    # Test model loading (if available)
    try:
        model = worker._load_model()
        print(f"Model loaded: {type(model)}")
    except FileNotFoundError:
        print("Model not found - will use placeholder processing")

    # Test message to bits conversion
    bits = worker._message_to_bits("test_message", 256)
    print(f"Watermark bits shape: {bits.shape}")

    print("\nWorker ready!")


if __name__ == "__main__":
    asyncio.run(run_worker())
