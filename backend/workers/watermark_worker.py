"""
VideoSeal Watermark Embedding Worker

Embeds invisible 256-bit watermarks into video frames using the
VideoSeal TorchScript model (y_256b_img.jit), then re-encodes to MP4.
"""

import asyncio
import hashlib
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

import boto3
import cv2
import numpy as np
import torch
from botocore.exceptions import ClientError

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "ckpts", "y_256b_img.jit")
_MODEL_CACHE = None


def _load_model(model_path: str, device: str):
    global _MODEL_CACHE
    if _MODEL_CACHE is None:
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"VideoSeal model not found at {model_path}.\n"
                "Download: https://dl.fbaipublicfiles.com/videoseal/y_256b_img.jit"
            )
        _MODEL_CACHE = torch.jit.load(model_path, map_location=device)
        _MODEL_CACHE.eval()
        print(f"VideoSeal model loaded on {device}")
    return _MODEL_CACHE


def _message_to_bits(message: str, num_bits: int = 256) -> torch.Tensor:
    digest = hashlib.sha256(message.encode()).digest()
    bits = [(byte >> (7 - i)) & 1 for byte in digest for i in range(8)]
    bits = bits[:num_bits] + [0] * max(0, num_bits - len(bits))
    return torch.tensor(bits, dtype=torch.float32)


def _embed_frame(model, frame_bgr: np.ndarray, bits: torch.Tensor, device: str) -> np.ndarray:
    """Embed watermark bits into a single BGR frame, return BGR frame."""
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    tensor = torch.from_numpy(rgb).permute(2, 0, 1).unsqueeze(0).to(device)
    msg = bits.unsqueeze(0).to(device)
    with torch.no_grad():
        out = model(tensor, msg)
    out_np = out.squeeze(0).permute(1, 2, 0).cpu().numpy()
    out_np = np.clip(out_np * 255, 0, 255).astype(np.uint8)
    return cv2.cvtColor(out_np, cv2.COLOR_RGB2BGR)


class WatermarkWorker:
    def __init__(
        self,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        aws_region: str,
        input_bucket: str,
        output_bucket: str,
        trace_key_pem: Optional[str] = None,
        model_path: Optional[str] = None,
        device: Optional[str] = None,
    ):
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region,
        )
        self.input_bucket = input_bucket
        self.output_bucket = output_bucket
        self.trace_key_pem = trace_key_pem
        self.model_path = model_path or MODEL_PATH
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None

    def _load_model(self):
        self.model = _load_model(self.model_path, self.device)
        return self.model

    def _message_to_bits(self, message: str, num_bits: int = 256) -> torch.Tensor:
        return _message_to_bits(message, num_bits)

    def generate_watermark(self, message: str, job_id: str) -> str:
        return f"TRACE|{message}|{job_id}"

    def _download_video(self, s3_key: str) -> bytes:
        print(f"Downloading video: {s3_key}")
        return self.s3_client.get_object(Bucket=self.input_bucket, Key=s3_key)["Body"].read()

    def _upload_video(self, video_data: bytes, s3_key: str) -> str:
        print(f"Uploading watermarked video: {s3_key}")
        self.s3_client.put_object(
            Bucket=self.output_bucket, Key=s3_key, Body=video_data, ContentType="video/mp4"
        )
        return s3_key

    def embed_watermark_frame(self, frame: torch.Tensor, watermark_bits: torch.Tensor) -> torch.Tensor:
        model = self._load_model()
        if frame.dim() == 3:
            frame = frame.unsqueeze(0)
        if watermark_bits.dim() == 1:
            watermark_bits = watermark_bits.unsqueeze(0)
        with torch.no_grad():
            watermarked_frame = model(frame, watermark_bits)
        return watermarked_frame.squeeze(0)

    def process_video_frames(self, video_path: str, watermark_message: str, job_id: str) -> str:
        """Process all frames with VideoSeal watermark embedding using OpenCV."""
        model = self._load_model()
        bits = _message_to_bits(watermark_message).to(self.device)

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        output_path = video_path.replace(".mp4", "_watermarked.mp4")
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            watermarked = _embed_frame(model, frame, bits, self.device)
            writer.write(watermarked)

        cap.release()
        writer.release()
        return output_path

    async def embed_watermark_video(
        self, video_data: bytes, watermark_message: str, job_id: str
    ) -> bytes:
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(video_data)
            input_path = f.name

        try:
            output_path = self.process_video_frames(input_path, watermark_message, job_id)
            with open(output_path, "rb") as f:
                return f.read()
        finally:
            try:
                os.unlink(input_path)
                if "output_path" in locals():
                    os.unlink(output_path)
            except Exception:
                pass

    async def process_video(self, job_id: str, s3_key: str, watermark_message: str) -> dict:
        result = {
            "job_id": job_id,
            "status": "processing",
            "input_key": s3_key,
            "output_key": None,
            "error": None,
            "started_at": datetime.utcnow().isoformat(),
        }
        try:
            video_data = self._download_video(s3_key)
            output_key = f"watermarked/{job_id}/{Path(s3_key).name}"
            watermarked_data = await self.embed_watermark_video(video_data, watermark_message, job_id)
            self._upload_video(watermarked_data, output_key)
            result.update({
                "status": "completed",
                "output_key": output_key,
                "completed_at": datetime.utcnow().isoformat(),
            })
        except ClientError as e:
            result.update({"status": "failed", "error": str(e)})
        except Exception as e:
            result.update({"status": "failed", "error": f"Processing error: {str(e)}"})
        return result

    def process_video_sync(self, job_id: str, s3_key: str, watermark_message: str) -> dict:
        return asyncio.run(self.process_video(job_id, s3_key, watermark_message))


async def run_worker():
    from backend.config import settings
    worker = WatermarkWorker(
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        aws_region=settings.AWS_REGION,
        input_bucket=settings.S3_UPLOAD_BUCKET,
        output_bucket=settings.S3_OUTPUT_BUCKET,
        trace_key_pem=settings.trace_key_pem,
    )
    try:
        model = worker._load_model()
        print(f"Model loaded: {type(model)}")
    except FileNotFoundError:
        print("Model not found - will use placeholder processing")
    bits = worker._message_to_bits("test_message", 256)
    print(f"Watermark bits shape: {bits.shape}")
    print("\nWorker ready!")


if __name__ == "__main__":
    asyncio.run(run_worker())
