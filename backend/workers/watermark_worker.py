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
    h, w = frame_bgr.shape[:2]
    # BGR -> RGB float [0,1], shape (1, 3, H, W)
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    tensor = torch.from_numpy(rgb).permute(2, 0, 1).unsqueeze(0).to(device)

    msg = bits.unsqueeze(0).to(device)

    with torch.no_grad():
        out = model(tensor, msg)

    # Back to BGR uint8
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
        model_path: Optional[str] = None,
        device: Optional[str] = None,
    ):
        self.s3 = boto3.client(
            "s3",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region,
        )
        self.input_bucket = input_bucket
        self.output_bucket = output_bucket
        self.model_path = model_path or MODEL_PATH
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

    def _download(self, s3_key: str) -> bytes:
        return self.s3.get_object(Bucket=self.input_bucket, Key=s3_key)["Body"].read()

    def _upload(self, data: bytes, s3_key: str):
        self.s3.put_object(Bucket=self.output_bucket, Key=s3_key, Body=data, ContentType="video/mp4")

    def _process_bytes(self, video_bytes: bytes, watermark_message: str, job_id: str) -> bytes:
        model = _load_model(self.model_path, self.device)
        bits = _message_to_bits(f"TRACE|{watermark_message}|{job_id}")

        with tempfile.TemporaryDirectory() as tmp:
            in_path = os.path.join(tmp, "input.mp4")
            out_path = os.path.join(tmp, "output.mp4")

            with open(in_path, "wb") as f:
                f.write(video_bytes)

            cap = cv2.VideoCapture(in_path)
            fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(out_path, fourcc, fps, (width, height))

            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                watermarked = _embed_frame(model, frame, bits, self.device)
                writer.write(watermarked)

            cap.release()
            writer.release()

            with open(out_path, "rb") as f:
                return f.read()

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
            video_data = self._download(s3_key)
            watermarked = self._process_bytes(video_data, watermark_message, job_id)
            output_key = f"watermarked/{job_id}/{Path(s3_key).name}"
            self._upload(watermarked, output_key)
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
