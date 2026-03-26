"""
YeyoOS — API Routes: Media (Imagen y Video)

Endpoints:
  POST /api/v1/media/image/generate   — genera imagen con Stable Diffusion
  POST /api/v1/media/video/compose    — compone video desde imágenes
  POST /api/v1/media/video/add-audio  — agrega audio a un video
  POST /api/v1/media/video/concat     — concatena videos
  GET  /api/v1/media/image/status     — estado del modelo (cargado / dispositivo)
  POST /api/v1/media/image/unload     — libera el modelo de memoria RAM
"""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from src.media.image_generator import get_image_service, ImageGenConfig, get_generation_progress
from src.media.video_composer import get_video_service

logger = logging.getLogger("yeyoos.api.media")

router = APIRouter(prefix="/api/v1/media", tags=["media"])


# ─── Schemas ─────────────────────────────────────────────────────────────────

class ImageGenerateRequest(BaseModel):
    prompt: str = Field(..., description="Descripción de la imagen a generar")
    negative_prompt: str = Field(default="", description="Qué evitar en la imagen")
    steps: int = Field(default=20, ge=1, le=100, description="Pasos de inferencia (más = mejor calidad, más lento)")
    guidance_scale: float = Field(default=7.5, ge=1.0, le=20.0)
    width: int = Field(default=512, ge=256, le=1024)
    height: int = Field(default=512, ge=256, le=1024)
    seed: int | None = Field(default=None, description="Semilla para reproducibilidad")


class ImageGenerateResponse(BaseModel):
    success: bool
    image_b64: str = ""   # PNG en base64 (data:image/png;base64,...)
    width: int = 0
    height: int = 0
    model: str = ""
    device: str = ""
    steps_used: int = 0
    error: str = ""


class VideoComposeRequest(BaseModel):
    image_paths: list[str] = Field(..., description="Rutas absolutas a las imágenes")
    fps: float = Field(default=24.0, ge=1.0, le=60.0)
    duration_per_image: float | None = Field(default=None, description="Segundos por imagen (None = 1/fps)")
    audio_path: str | None = Field(default=None, description="Ruta a archivo de audio (opcional)")
    transition: str = Field(default="none", description="'none' o 'fade'")


class VideoAddAudioRequest(BaseModel):
    video_path: str
    audio_path: str


class VideoConcatRequest(BaseModel):
    video_paths: list[str]


class VideoResponse(BaseModel):
    success: bool
    file_path: str = ""
    duration_seconds: float = 0.0
    width: int = 0
    height: int = 0
    fps: float = 0.0
    error: str = ""


# ─── Imagen ──────────────────────────────────────────────────────────────────

@router.post("/image/generate", response_model=ImageGenerateResponse)
async def generate_image(request: ImageGenerateRequest):
    """
    Genera una imagen usando Stable Diffusion en MPS (Apple Silicon).
    Primera llamada es más lenta porque carga el modelo (~2.5GB) en memoria.
    """
    service = get_image_service()
    result = await service.generate(
        prompt=request.prompt,
        negative_prompt=request.negative_prompt,
        steps=request.steps,
        guidance_scale=request.guidance_scale,
        width=request.width,
        height=request.height,
        seed=request.seed,
    )

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    return ImageGenerateResponse(
        success=True,
        image_b64=f"data:image/png;base64,{result.image_b64}",
        width=result.width,
        height=result.height,
        model=result.model,
        device=result.device,
        steps_used=result.steps_used,
    )


@router.get("/image/progress")
async def image_generation_progress():
    """
    Progreso en tiempo real de la generación actual.
    El frontend hace polling cada ~1 segundo mientras genera.
    Retorna: { active, step, total_steps, percent }
    """
    return get_generation_progress()


@router.get("/image/status")
async def image_model_status():
    """Estado del modelo de generación de imágenes."""
    service = get_image_service()
    return {
        "loaded": service.is_loaded,
        "device": service.device,
        "model": service.config.model_id,
    }


@router.post("/image/unload")
async def unload_image_model():
    """Libera el modelo SD de la RAM (útil cuando se necesita memoria para otras tareas)."""
    service = get_image_service()
    service.unload()
    return {"unloaded": True}


# ─── Video ───────────────────────────────────────────────────────────────────

@router.post("/video/compose", response_model=VideoResponse)
async def compose_video(request: VideoComposeRequest):
    """
    Compone un video MP4 a partir de una lista de imágenes.
    Opcionalmente agrega audio y aplica transiciones.
    """
    service = get_video_service()
    result = await service.images_to_video(
        image_paths=request.image_paths,
        fps=request.fps,
        duration_per_image=request.duration_per_image,
        audio_path=request.audio_path,
        transition=request.transition,
    )

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    return VideoResponse(
        success=True,
        file_path=result.file_path,
        duration_seconds=result.duration_seconds,
        width=result.width,
        height=result.height,
        fps=result.fps,
    )


@router.post("/video/add-audio", response_model=VideoResponse)
async def add_audio_to_video(request: VideoAddAudioRequest):
    """Agrega o reemplaza el audio de un video existente."""
    service = get_video_service()
    result = await service.add_audio_to_video(
        video_path=request.video_path,
        audio_path=request.audio_path,
    )

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    return VideoResponse(
        success=True,
        file_path=result.file_path,
        duration_seconds=result.duration_seconds,
        width=result.width,
        height=result.height,
    )


@router.post("/video/concat", response_model=VideoResponse)
async def concat_videos(request: VideoConcatRequest):
    """Concatena múltiples videos en uno solo."""
    service = get_video_service()
    result = await service.concatenate_videos(video_paths=request.video_paths)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    return VideoResponse(
        success=True,
        file_path=result.file_path,
        duration_seconds=result.duration_seconds,
        width=result.width,
        height=result.height,
    )


@router.get("/video/download/{filename}")
async def download_video(filename: str):
    """Descarga un video generado por su nombre de archivo."""
    from src.media.video_composer import _OUTPUT_DIR
    # Sanitizar: no permitir path traversal
    safe_name = Path(filename).name
    if safe_name != filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Nombre de archivo inválido")

    file_path = _OUTPUT_DIR / safe_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Video no encontrado")

    return FileResponse(
        path=str(file_path),
        media_type="video/mp4",
        filename=safe_name,
    )
