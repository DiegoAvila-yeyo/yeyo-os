"""
YeyoOS — Generador de Imágenes
Usa Stable Diffusion con aceleración MPS en Apple Silicon (M1/M2/M3).
Fallback a CPU si MPS no está disponible.

Modelo por defecto: stabilityai/stable-diffusion-2-1-base (~2.5GB)
Optimizaciones para 8GB RAM:
  - float16 en MPS
  - attention_slicing activado
  - lazy loading (carga el modelo solo cuando se necesita)
"""

import io
import base64
import logging
import threading
from pathlib import Path
from dataclasses import dataclass, field

from src.core.thermal_guard import get_thermal_guard, ThermalAbortError

logger = logging.getLogger("yeyoos.media.image")

# Progreso global de la generación actual
_generation_progress: dict = {
    "active": False,
    "step": 0,
    "total_steps": 0,
    "percent": 0,
}


def get_generation_progress() -> dict:
    return dict(_generation_progress)


def _reset_progress() -> None:
    _generation_progress.update({"active": False, "step": 0, "total_steps": 0, "percent": 0})


def _update_progress(step: int, total: int) -> None:
    _generation_progress.update({
        "active": True,
        "step": step,
        "total_steps": total,
        "percent": round((step / total) * 100) if total > 0 else 0,
    })


@dataclass
class ImageGenConfig:
    model_id: str = "runwayml/stable-diffusion-v1-5"
    # Alternativas:
    # "stabilityai/stable-diffusion-2-1-base"  (~2.5GB, requiere HF auth)
    # "CompVis/stable-diffusion-v1-4"   (~2GB)
    steps: int = 10
    guidance_scale: float = 7.5
    width: int = 512
    height: int = 512
    cache_dir: str = str(Path.home() / ".cache" / "yeyoos" / "models")


@dataclass
class ImageResult:
    success: bool
    image_b64: str = ""        # PNG en base64
    width: int = 0
    height: int = 0
    model: str = ""
    device: str = ""
    error: str = ""
    steps_used: int = 0


class ImageGeneratorService:
    """
    Servicio de generación de imágenes con Stable Diffusion.
    El pipeline se carga al primer uso (lazy) para no bloquear el startup.
    """

    def __init__(self, config: ImageGenConfig | None = None):
        self.config = config or ImageGenConfig()
        self._pipeline = None
        self._device: str | None = None
        self._pipeline_lock = threading.Lock()  # serializes all MPS/pipeline operations
    def _get_device(self) -> str:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def _load_pipeline(self) -> None:
        """Carga el pipeline de Stable Diffusion. Se llama una sola vez."""
        with self._pipeline_lock:
            if self._pipeline is not None:
                return

            import torch
            from diffusers import StableDiffusionPipeline

            self._device = self._get_device()
            logger.info(f"Cargando modelo SD '{self.config.model_id}' en {self._device}...")

            # CUDA: float16 es seguro y 2-3x más rápido.
            # MPS (Apple Silicon): float16 produce NaN → usar float32.
            # CPU: float32 siempre.
            if self._device == "cuda":
                dtype = torch.float16
            else:
                dtype = torch.float32

            pipe = StableDiffusionPipeline.from_pretrained(
                self.config.model_id,
                torch_dtype=dtype,
                cache_dir=self.config.cache_dir,
                safety_checker=None,  # deshabilitado para uso local
                requires_safety_checker=False,
            )
            pipe = pipe.to(self._device)

            # Optimizaciones de memoria (crítico para GPUs con ≤4GB VRAM como GTX 1060 3GB)
            pipe.enable_attention_slicing(1)   # slicing máximo → menos VRAM por paso
            pipe.enable_vae_slicing()          # decodifica VAE en trozos → -500MB VRAM
            if hasattr(pipe, "enable_vae_tiling"):
                pipe.enable_vae_tiling()       # tiles en VAE para resoluciones altas

            self._pipeline = pipe
            logger.info(f"Modelo cargado en {self._device} ✅")

    async def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        steps: int | None = None,
        guidance_scale: float | None = None,
        width: int | None = None,
        height: int | None = None,
        seed: int | None = None,
    ) -> ImageResult:
        """
        Genera una imagen a partir de un prompt de texto.
        Retorna la imagen en base64 (PNG).
        """
        try:
            import asyncio
            import torch
            from PIL import Image

            # Carga lazy del modelo
            if self._pipeline is None:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._load_pipeline)

            steps = steps or self.config.steps
            guidance_scale = guidance_scale or self.config.guidance_scale
            w = width or self.config.width
            h = height or self.config.height

            # Generador con semilla opcional para reproducibilidad
            generator = None
            if seed is not None:
                generator = torch.Generator(device=self._device).manual_seed(seed)

            logger.info(f"Generando imagen: '{prompt[:60]}...' [{w}x{h}, {steps} steps]")

            loop = asyncio.get_event_loop()
            _update_progress(0, steps)

            thermal = get_thermal_guard()
            thermal.reset_abort()
            thermal.start_background_monitor()

            def _sd_callback(pipe, step_index, timestep, callback_kwargs):
                _update_progress(step_index + 1, steps)
                thermal.check_and_wait_async_safe(step=step_index + 1, total=steps)
                return callback_kwargs

            def _run_inference():
                with self._pipeline_lock:
                    return self._pipeline(
                        prompt=prompt,
                        negative_prompt=negative_prompt or None,
                        num_inference_steps=steps,
                        guidance_scale=guidance_scale,
                        width=w,
                        height=h,
                        generator=generator,
                        callback_on_step_end=_sd_callback,
                    ).images[0]

            try:
                image: Image.Image = await loop.run_in_executor(None, _run_inference)
            except ThermalAbortError as e:
                logger.critical(f"🔥 Generación abortada por temperatura crítica: {e}")
                _reset_progress()
                thermal.stop_background_monitor()
                return ImageResult(success=False, error=f"Temperatura crítica: {e}")
            finally:
                thermal.stop_background_monitor()

            _reset_progress()

            # Fix MPS NaN→0 issue: clamp pixel values to valid range
            import numpy as np
            arr = np.array(image, dtype=np.float32)
            arr = np.clip(arr, 0, 255).astype(np.uint8)
            image = Image.fromarray(arr)

            # Convertir a base64
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            img_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

            logger.info("Imagen generada ✅")
            return ImageResult(
                success=True,
                image_b64=img_b64,
                width=w,
                height=h,
                model=self.config.model_id,
                device=self._device or "unknown",
                steps_used=steps,
            )

        except Exception as e:
            logger.error(f"Error generando imagen: {e}")
            _reset_progress()
            return ImageResult(success=False, error=str(e))

    def unload(self) -> None:
        """Libera el modelo de memoria (útil cuando se necesita RAM para otras tareas)."""
        if self._pipeline is not None:
            import torch
            del self._pipeline
            self._pipeline = None
            if torch.backends.mps.is_available():
                torch.mps.empty_cache()
            logger.info("Modelo SD descargado de memoria")

    @property
    def is_loaded(self) -> bool:
        return self._pipeline is not None

    @property
    def device(self) -> str:
        return self._device or self._get_device()


# Instancia global (singleton lazy)
_image_service: ImageGeneratorService | None = None


def get_image_service() -> ImageGeneratorService:
    global _image_service
    if _image_service is None:
        _image_service = ImageGeneratorService()
    return _image_service
