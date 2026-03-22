"""
YeyoOS — Image-to-Image Transformation
Micro-fase 5.3 — Capa 5: Órganos

Transforma imágenes existentes con prompts de texto.
Usa SD 1.5 img2img pipeline.
"""

import uuid
import base64
from io import BytesIO
from datetime import datetime, timezone
from dataclasses import dataclass, field

from src.nodes.image.service import (
    ImageGenerationNode, SAFE_RESOLUTIONS, SD_VRAM_REQUIRED,
)


@dataclass
class Img2ImgResult:
    """Resultado de transformación img2img."""
    id: str
    original_prompt: str
    transform_prompt: str
    strength: float
    image_data: bytes
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class Img2ImgService:
    """Servicio de transformación imagen a imagen."""

    def __init__(self, image_node: ImageGenerationNode):
        self._image_node = image_node
        self._pipeline = None

    async def transform(
        self,
        source_image: bytes,
        prompt: str,
        strength: float = 0.75,
        resolution: str = "512x512",
    ) -> dict:
        """
        Transforma una imagen existente con un prompt.
        strength: 0.0 (sin cambios) a 1.0 (completamente nueva).
        """
        if resolution not in SAFE_RESOLUTIONS:
            return {"error": f"Resolución no soportada: {resolution}"}

        strength = max(0.1, min(1.0, strength))

        gpu_granted = await self._image_node.request_gpu(
            vram_mb=SD_VRAM_REQUIRED, priority=2,
        )
        if not gpu_granted:
            return {"error": "GPU no disponible"}

        try:
            result_bytes = await self._run_img2img(
                source_image=source_image,
                prompt=prompt,
                strength=strength,
            )

            result = Img2ImgResult(
                id=f"img2img-{uuid.uuid4().hex[:8]}",
                original_prompt="(source image)",
                transform_prompt=prompt,
                strength=strength,
                image_data=result_bytes,
            )

            return {
                "image_id": result.id,
                "prompt": prompt,
                "strength": strength,
                "image_base64": base64.b64encode(result_bytes).decode("utf-8"),
            }
        except Exception as e:
            return {"error": f"Error en img2img: {str(e)}"}
        finally:
            await self._image_node.release_gpu()
            self._pipeline = None

    async def _run_img2img(
        self, source_image: bytes, prompt: str, strength: float
    ) -> bytes:
        """Ejecuta pipeline img2img de SD 1.5."""
        from diffusers import StableDiffusionImg2ImgPipeline
        from PIL import Image
        import torch

        if self._pipeline is None:
            self._pipeline = StableDiffusionImg2ImgPipeline.from_pretrained(
                "runwayml/stable-diffusion-v1-5",
                torch_dtype=torch.float16,
                safety_checker=None,
            ).to("cuda")
            self._pipeline.enable_attention_slicing()

        source = Image.open(BytesIO(source_image)).convert("RGB")
        source = source.resize((512, 512))

        with torch.no_grad():
            result = self._pipeline(
                prompt=prompt,
                image=source,
                strength=strength,
                num_inference_steps=20,
                guidance_scale=7.5,
            )

        buffer = BytesIO()
        result.images[0].save(buffer, format="PNG")
        return buffer.getvalue()
