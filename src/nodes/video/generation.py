"""
YeyoOS — AI Video Generation Service
Multi-provider: Replicate + FAL.ai + Local GPU (fallback)

Genera videos de 4-8 segundos a partir de una imagen usando IA.
Maximiza free tiers alternando entre providers.
"""

import os
import uuid
import base64
import asyncio
import logging
import tempfile
import httpx
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("yeyoos.video.generation")

_OUTPUT_DIR = Path.home() / ".cache" / "yeyoos" / "generated_videos"
_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class GenerationStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProviderName(str, Enum):
    REPLICATE = "replicate"
    FAL = "fal"
    LOCAL = "local"


@dataclass
class VideoGenerationJob:
    """Trabajo de generación de video con IA."""
    id: str
    provider: str
    prompt: str
    status: GenerationStatus = GenerationStatus.PENDING
    progress: float = 0.0
    output_path: Optional[str] = None
    output_url: Optional[str] = None
    duration_seconds: float = 0.0
    width: int = 0
    height: int = 0
    error: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    metadata: dict = field(default_factory=dict)


class VideoProvider(ABC):
    """Base class for video generation providers."""

    @abstractmethod
    async def generate(
        self,
        image_path: str,
        prompt: str,
        duration: float,
        **kwargs,
    ) -> VideoGenerationJob:
        ...

    @abstractmethod
    def is_available(self) -> bool:
        ...

    @abstractmethod
    def name(self) -> str:
        ...


class ReplicateProvider(VideoProvider):
    """
    Replicate API — Stable Video Diffusion, Kling, LTX-Video.
    Free tier: ~$5 credit for new accounts.
    """

    MODEL_ID = "stability-ai/stable-video-diffusion:3f0457e4619daac51203dedb472816fd4af51f3149fa7a9e0b5ffcf1b8172438"

    def __init__(self):
        self.api_token = os.getenv("REPLICATE_API_TOKEN", "")
        self.base_url = "https://api.replicate.com/v1"

    def name(self) -> str:
        return ProviderName.REPLICATE

    def is_available(self) -> bool:
        return bool(self.api_token)

    async def generate(
        self,
        image_path: str,
        prompt: str,
        duration: float = 4.0,
        **kwargs,
    ) -> VideoGenerationJob:
        job = VideoGenerationJob(
            id=f"vgen-rep-{uuid.uuid4().hex[:8]}",
            provider=self.name(),
            prompt=prompt,
        )

        try:
            image_b64 = self._image_to_data_uri(image_path)

            async with httpx.AsyncClient(timeout=300) as client:
                # Create prediction
                response = await client.post(
                    f"{self.base_url}/predictions",
                    headers={
                        "Authorization": f"Bearer {self.api_token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "version": self.MODEL_ID.split(":")[-1],
                        "input": {
                            "input_image": image_b64,
                            "motion_bucket_id": 127,
                            "fps": 8,
                            "cond_aug": 0.02,
                            "decoding_t": 14,
                            "seed": 0,
                        },
                    },
                )
                response.raise_for_status()
                prediction = response.json()
                prediction_id = prediction["id"]
                job.status = GenerationStatus.PROCESSING

                # Poll for completion
                output_url = await self._poll_prediction(client, prediction_id)

                if output_url:
                    output_path = await self._download_video(client, output_url, job.id)
                    job.status = GenerationStatus.COMPLETED
                    job.output_path = str(output_path)
                    job.output_url = output_url
                    job.completed_at = datetime.now(timezone.utc)
                    logger.info(f"Replicate video generated: {output_path}")
                else:
                    job.status = GenerationStatus.FAILED
                    job.error = "Prediction failed or timed out"

        except httpx.HTTPStatusError as e:
            job.status = GenerationStatus.FAILED
            job.error = f"Replicate API error: {e.response.status_code} - {e.response.text[:200]}"
            logger.error(job.error)
        except Exception as e:
            job.status = GenerationStatus.FAILED
            job.error = f"Replicate error: {str(e)}"
            logger.error(job.error)

        return job

    async def _poll_prediction(self, client: httpx.AsyncClient, prediction_id: str) -> Optional[str]:
        """Poll Replicate prediction until complete (max 5 min)."""
        for _ in range(60):  # 60 × 5s = 5 minutes max
            response = await client.get(
                f"{self.base_url}/predictions/{prediction_id}",
                headers={"Authorization": f"Bearer {self.api_token}"},
            )
            data = response.json()
            status = data.get("status")

            if status == "succeeded":
                output = data.get("output")
                if isinstance(output, list) and output:
                    return output[0]
                elif isinstance(output, str):
                    return output
                return None
            elif status in ("failed", "canceled"):
                logger.error(f"Replicate prediction {status}: {data.get('error')}")
                return None

            await asyncio.sleep(5)

        logger.error("Replicate prediction timed out after 5 minutes")
        return None

    async def _download_video(self, client: httpx.AsyncClient, url: str, job_id: str) -> Path:
        """Download generated video to local cache."""
        response = await client.get(url)
        response.raise_for_status()

        output_path = _OUTPUT_DIR / f"{job_id}.mp4"
        output_path.write_bytes(response.content)
        return output_path

    def _image_to_data_uri(self, image_path: str) -> str:
        """Convert image file to data URI for API."""
        with open(image_path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")

        ext = Path(image_path).suffix.lower()
        mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}.get(ext, "image/png")
        return f"data:{mime};base64,{data}"


class FalProvider(VideoProvider):
    """
    FAL.ai API — Fast inference, multiple video models.
    Free tier: limited requests per day.
    """

    def __init__(self):
        self.api_key = os.getenv("FAL_KEY", "")
        self.base_url = "https://queue.fal.run"

    def name(self) -> str:
        return ProviderName.FAL

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def generate(
        self,
        image_path: str,
        prompt: str,
        duration: float = 4.0,
        **kwargs,
    ) -> VideoGenerationJob:
        job = VideoGenerationJob(
            id=f"vgen-fal-{uuid.uuid4().hex[:8]}",
            provider=self.name(),
            prompt=prompt,
        )

        try:
            image_b64 = self._image_to_base64(image_path)

            async with httpx.AsyncClient(timeout=300) as client:
                # Submit to FAL queue (using stable-video model)
                response = await client.post(
                    f"{self.base_url}/fal-ai/stable-video",
                    headers={
                        "Authorization": f"Key {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "image_url": f"data:image/png;base64,{image_b64}",
                        "motion_bucket_id": 127,
                        "fps": 8,
                        "cond_aug": 0.02,
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    video_url = data.get("video", {}).get("url", "")

                    if video_url:
                        output_path = await self._download_video(client, video_url, job.id)
                        job.status = GenerationStatus.COMPLETED
                        job.output_path = str(output_path)
                        job.output_url = video_url
                        job.completed_at = datetime.now(timezone.utc)
                        logger.info(f"FAL video generated: {output_path}")
                    else:
                        job.status = GenerationStatus.FAILED
                        job.error = "No video URL in FAL response"
                elif response.status_code == 202:
                    # Queued — need to poll
                    data = response.json()
                    request_id = data.get("request_id", "")
                    result = await self._poll_result(client, request_id)

                    if result:
                        video_url = result.get("video", {}).get("url", "")
                        if video_url:
                            output_path = await self._download_video(client, video_url, job.id)
                            job.status = GenerationStatus.COMPLETED
                            job.output_path = str(output_path)
                            job.output_url = video_url
                            job.completed_at = datetime.now(timezone.utc)
                        else:
                            job.status = GenerationStatus.FAILED
                            job.error = "No video URL in FAL result"
                    else:
                        job.status = GenerationStatus.FAILED
                        job.error = "FAL generation timed out"
                else:
                    job.status = GenerationStatus.FAILED
                    job.error = f"FAL API error: {response.status_code}"

        except Exception as e:
            job.status = GenerationStatus.FAILED
            job.error = f"FAL error: {str(e)}"
            logger.error(job.error)

        return job

    async def _poll_result(self, client: httpx.AsyncClient, request_id: str) -> Optional[dict]:
        """Poll FAL queue for result."""
        for _ in range(60):
            response = await client.get(
                f"{self.base_url}/fal-ai/stable-video/requests/{request_id}/status",
                headers={"Authorization": f"Key {self.api_key}"},
            )
            data = response.json()
            status = data.get("status")

            if status == "COMPLETED":
                result_resp = await client.get(
                    f"{self.base_url}/fal-ai/stable-video/requests/{request_id}",
                    headers={"Authorization": f"Key {self.api_key}"},
                )
                return result_resp.json()
            elif status in ("FAILED",):
                return None

            await asyncio.sleep(5)
        return None

    async def _download_video(self, client: httpx.AsyncClient, url: str, job_id: str) -> Path:
        response = await client.get(url)
        response.raise_for_status()
        output_path = _OUTPUT_DIR / f"{job_id}.mp4"
        output_path.write_bytes(response.content)
        return output_path

    def _image_to_base64(self, image_path: str) -> str:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")


class LocalGPUProvider(VideoProvider):
    """
    Local GPU provider — Uses Stable Video Diffusion with diffusers.
    Only for machines with NVIDIA GPU (Desktop with GTX 1060).
    Falls back to CPU slideshow if no GPU available.
    """

    def __init__(self):
        self._has_cuda = self._check_cuda()

    def name(self) -> str:
        return ProviderName.LOCAL

    def is_available(self) -> bool:
        return self._has_cuda

    def _check_cuda(self) -> bool:
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    async def generate(
        self,
        image_path: str,
        prompt: str,
        duration: float = 4.0,
        **kwargs,
    ) -> VideoGenerationJob:
        job = VideoGenerationJob(
            id=f"vgen-local-{uuid.uuid4().hex[:8]}",
            provider=self.name(),
            prompt=prompt,
        )

        try:
            import torch
            from PIL import Image

            image = Image.open(image_path).convert("RGB").resize((512, 512))

            loop = asyncio.get_event_loop()
            output_path = await loop.run_in_executor(
                None, self._run_svd_inference, image, job.id
            )

            job.status = GenerationStatus.COMPLETED
            job.output_path = str(output_path)
            job.completed_at = datetime.now(timezone.utc)
            logger.info(f"Local GPU video generated: {output_path}")

        except Exception as e:
            job.status = GenerationStatus.FAILED
            job.error = f"Local GPU error: {str(e)}"
            logger.error(job.error)

        return job

    def _run_svd_inference(self, image, job_id: str) -> Path:
        """Run SVD inference on local GPU (blocking, runs in executor)."""
        import torch
        from diffusers import StableVideoDiffusionPipeline
        from diffusers.utils import export_to_video

        pipe = StableVideoDiffusionPipeline.from_pretrained(
            "stabilityai/stable-video-diffusion-img2vid",
            torch_dtype=torch.float16,
            variant="fp16",
        )
        pipe = pipe.to("cuda")
        pipe.enable_model_cpu_offload()

        with torch.no_grad():
            frames = pipe(
                image,
                decode_chunk_size=8,
                num_frames=25,
                motion_bucket_id=127,
            ).frames[0]

        output_path = _OUTPUT_DIR / f"{job_id}.mp4"
        export_to_video(frames, str(output_path), fps=8)

        del pipe
        torch.cuda.empty_cache()

        return output_path


class VideoGenerationService:
    """
    Multi-provider video generation service.
    Automatically selects the best available provider.
    Priority: FAL (fastest) → Replicate (most models) → Local GPU.
    """

    def __init__(self):
        self._providers: list[VideoProvider] = []
        self._jobs: dict[str, VideoGenerationJob] = {}
        self._init_providers()

    def _init_providers(self):
        """Initialize all available providers."""
        fal = FalProvider()
        if fal.is_available():
            self._providers.append(fal)
            logger.info("✅ FAL.ai provider available")

        replicate = ReplicateProvider()
        if replicate.is_available():
            self._providers.append(replicate)
            logger.info("✅ Replicate provider available")

        local = LocalGPUProvider()
        if local.is_available():
            self._providers.append(local)
            logger.info("✅ Local GPU provider available")

        if not self._providers:
            logger.warning("⚠️ No video generation providers available. Set REPLICATE_API_TOKEN or FAL_KEY in .env")

    @property
    def available_providers(self) -> list[str]:
        return [p.name() for p in self._providers]

    async def generate_video(
        self,
        image_path: str,
        prompt: str = "",
        duration: float = 4.0,
        preferred_provider: Optional[str] = None,
        **kwargs,
    ) -> VideoGenerationJob:
        """
        Generate a video from an image using the best available provider.

        Args:
            image_path: Path to source image
            prompt: Text description of desired video motion
            duration: Target duration in seconds (4-8s typical)
            preferred_provider: Force a specific provider (replicate/fal/local)

        Returns:
            VideoGenerationJob with status and output path
        """
        if not Path(image_path).exists():
            return VideoGenerationJob(
                id=f"vgen-err-{uuid.uuid4().hex[:8]}",
                provider="none",
                prompt=prompt,
                status=GenerationStatus.FAILED,
                error=f"Image not found: {image_path}",
            )

        # Select provider
        provider = self._select_provider(preferred_provider)
        if not provider:
            return VideoGenerationJob(
                id=f"vgen-err-{uuid.uuid4().hex[:8]}",
                provider="none",
                prompt=prompt,
                status=GenerationStatus.FAILED,
                error="No video generation providers available. Set REPLICATE_API_TOKEN or FAL_KEY in .env",
            )

        logger.info(f"Generating video with {provider.name()}: prompt='{prompt[:50]}...'")

        # Generate
        job = await provider.generate(
            image_path=image_path,
            prompt=prompt,
            duration=duration,
            **kwargs,
        )

        # Store job
        self._jobs[job.id] = job

        # If primary provider failed, try fallback
        if job.status == GenerationStatus.FAILED and len(self._providers) > 1:
            fallback = self._get_fallback_provider(provider)
            if fallback:
                logger.info(f"Primary provider failed, trying fallback: {fallback.name()}")
                job = await fallback.generate(
                    image_path=image_path,
                    prompt=prompt,
                    duration=duration,
                    **kwargs,
                )
                self._jobs[job.id] = job

        return job

    async def generate_slideshow(
        self,
        image_paths: list[str],
        duration_per_image: float = 3.0,
        fps: float = 24.0,
        transition: str = "fade",
        audio_path: Optional[str] = None,
    ) -> VideoGenerationJob:
        """
        Generate a slideshow video from multiple images using FFmpeg/moviepy.
        No API key required — runs locally with moviepy.

        Args:
            image_paths: List of image file paths
            duration_per_image: Seconds each image is shown
            fps: Output frames per second
            transition: Transition type (none/fade)
            audio_path: Optional audio file to overlay
        """
        from src.media.video_composer import get_video_service

        job = VideoGenerationJob(
            id=f"vgen-slide-{uuid.uuid4().hex[:8]}",
            provider="local_ffmpeg",
            prompt=f"Slideshow: {len(image_paths)} images",
        )

        try:
            service = get_video_service()
            result = await service.images_to_video(
                image_paths=image_paths,
                fps=fps,
                duration_per_image=duration_per_image,
                audio_path=audio_path,
                transition=transition,
            )

            if result.success:
                job.status = GenerationStatus.COMPLETED
                job.output_path = result.file_path
                job.duration_seconds = result.duration_seconds
                job.width = result.width
                job.height = result.height
                job.completed_at = datetime.now(timezone.utc)
            else:
                job.status = GenerationStatus.FAILED
                job.error = result.error

        except Exception as e:
            job.status = GenerationStatus.FAILED
            job.error = str(e)

        self._jobs[job.id] = job
        return job

    def get_job(self, job_id: str) -> Optional[VideoGenerationJob]:
        return self._jobs.get(job_id)

    def get_all_jobs(self) -> list[VideoGenerationJob]:
        return list(self._jobs.values())

    def _select_provider(self, preferred: Optional[str] = None) -> Optional[VideoProvider]:
        if preferred:
            for p in self._providers:
                if p.name() == preferred:
                    return p

        return self._providers[0] if self._providers else None

    def _get_fallback_provider(self, failed: VideoProvider) -> Optional[VideoProvider]:
        for p in self._providers:
            if p.name() != failed.name():
                return p
        return None


# Singleton
_generation_service: Optional[VideoGenerationService] = None


def get_generation_service() -> VideoGenerationService:
    global _generation_service
    if _generation_service is None:
        _generation_service = VideoGenerationService()
    return _generation_service
