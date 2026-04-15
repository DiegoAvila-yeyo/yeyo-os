"""
YeyoOS — Image Generation Node
Micro-fase 5.2 — Capa 5: Órganos

Generación de imágenes con Stable Diffusion 1.5.
CRÍTICO: GPU scheduler gestiona VRAM — Ollama se descarga cuando SD genera.
Resolución máxima 512x512 para GTX 1060 3GB.
"""

import uuid
import base64
from io import BytesIO
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass, field

from src.nodes.base import NodeBase, PrivilegeLevel


# Resoluciones seguras para 3GB VRAM
SAFE_RESOLUTIONS = {
    "256x256": (256, 256),
    "384x384": (384, 384),
    "512x512": (512, 512),
    "512x384": (512, 384),
    "384x512": (384, 512),
}

MAX_RESOLUTION = 512
SD_VRAM_REQUIRED = 2500  # MB de VRAM para SD 1.5

STYLE_PRESETS = {
    "none": "",
    "photorealistic": "photorealistic, 8k, detailed, sharp focus",
    "anime": "anime style, cel shading, vibrant colors",
    "oil_painting": "oil painting, impressionist, brush strokes, canvas texture",
    "pixel_art": "pixel art, retro, 16-bit, low resolution",
    "watercolor": "watercolor painting, soft colors, flowing, artistic",
    "cyberpunk": "cyberpunk, neon lights, futuristic, dark atmosphere",
    "minimalist": "minimalist, clean lines, simple shapes, white space",
}


@dataclass
class GeneratedImage:
    """Imagen generada."""
    id: str
    prompt: str
    enhanced_prompt: str
    style: str
    resolution: str
    image_data: bytes
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ImageGenerationNode(NodeBase):
    """
    Nodo de generación de imágenes — órgano creativo de YeyoOS.
    Stable Diffusion 1.5, prompt enhancement, gallery.
    CRÍTICO: GPU scheduler descarga Ollama antes de generar.
    """

    def __init__(self):
        super().__init__(
            name="Image Generation",
            version="1.0.0",
            privilege_level=PrivilegeLevel.SANDBOX,
            container_config={
                "memory_limit": "4g",
                "cpu_shares": 1024,
                "gpu_required": True,
            },
        )
        self._gallery: list[GeneratedImage] = []
        self._sd_pipeline = None
        self._is_generating: bool = False

    async def initialize(self) -> None:
        """Inicializa el nodo (NO carga SD hasta que se necesite — lazy load)."""
        pass

    async def render_ui(self) -> dict:
        """Retorna configuración del componente React."""
        return {
            "component": "ImageGenerationNode",
            "props": {
                "styles": list(STYLE_PRESETS.keys()),
                "resolutions": list(SAFE_RESOLUTIONS.keys()),
                "gallery": [
                    {
                        "id": img.id,
                        "prompt": img.prompt,
                        "resolution": img.resolution,
                        "created_at": img.created_at.isoformat(),
                    }
                    for img in self._gallery
                ],
                "isGenerating": self._is_generating,
            },
        }

    async def process(self, input_data: dict) -> dict:
        """Procesa solicitud de generación de imagen."""
        action = input_data.get("action", "generate")

        if action == "generate":
            return await self._generate_image(
                prompt=input_data.get("prompt", ""),
                style=input_data.get("style", "none"),
                resolution=input_data.get("resolution", "512x512"),
            )
        elif action == "enhance_prompt":
            return await self._enhance_prompt(input_data.get("prompt", ""))
        elif action == "get_gallery":
            return {"gallery": [img.id for img in self._gallery]}
        else:
            return {"error": f"Acción desconocida: {action}"}

    async def cleanup(self) -> None:
        """Libera recursos: pipeline SD, GPU."""
        self._sd_pipeline = None
        self._gallery.clear()
        await self.release_gpu()

    # ═══════════════════════════════════
    # MÉTODOS ESPECÍFICOS
    # ═══════════════════════════════════

    async def _enhance_prompt(self, prompt: str) -> dict:
        """Usa Ollama para mejorar el prompt. Inyecta conocimiento de imagen si hay memoria."""
        from src.ia.ollama_provider import OllamaProvider

        # Buscar contexto relevante de imagen:conocimiento + imagen:usuario
        memory_context = ""
        if self._memory_service:
            memory_context = await self._memory_service.get_image_context(prompt, limit=3)

        system = (
            "You are an expert at writing Stable Diffusion prompts. "
            "Add details about lighting, composition, style, and quality. "
            "Keep it under 200 words."
        )
        if memory_context:
            system += (
                "\n\n[Relevant knowledge — apply these principles]\n"
                + memory_context
            )

        provider = OllamaProvider()
        response = await provider.generate(
            prompt=f"Enhance this image generation prompt. Make it more detailed and descriptive. "
                    f"Only return the enhanced prompt, nothing else.\n\nOriginal: {prompt}",
            system=system,
            temperature=0.8,
        )
        return {
            "original_prompt": prompt,
            "enhanced_prompt": response.content.strip(),
        }

    async def _generate_image(
        self, prompt: str, style: str = "none", resolution: str = "512x512"
    ) -> dict:
        """
        Genera una imagen con Stable Diffusion 1.5.
        FLUJO: enhance prompt → request GPU → load SD → generate → release GPU
        """
        if self._is_generating:
            return {"error": "Ya hay una generación en curso"}

        if resolution not in SAFE_RESOLUTIONS:
            return {"error": f"Resolución no soportada. Usar: {list(SAFE_RESOLUTIONS.keys())}"}

        width, height = SAFE_RESOLUTIONS[resolution]

        self._is_generating = True
        try:
            # 1. Enhance prompt (mientras Ollama aún está en VRAM)
            enhanced = await self._enhance_prompt(prompt)
            final_prompt = enhanced["enhanced_prompt"]

            # Agregar estilo
            style_suffix = STYLE_PRESETS.get(style, "")
            if style_suffix:
                final_prompt = f"{final_prompt}, {style_suffix}"

            # 2. Solicitar GPU — CRÍTICO: esto descarga Ollama
            gpu_granted = await self.request_gpu(
                vram_mb=SD_VRAM_REQUIRED,
                priority=1,
            )
            if not gpu_granted:
                return {"error": "GPU no disponible. Intenta de nuevo en unos segundos."}

            # 3. Cargar SD pipeline (lazy)
            if self._sd_pipeline is None:
                self._sd_pipeline = await self._load_sd_pipeline()

            # 4. Generar imagen
            image_data = await self._run_sd_inference(
                pipeline=self._sd_pipeline,
                prompt=final_prompt,
                width=width,
                height=height,
            )

            # 5. Guardar en galería
            generated = GeneratedImage(
                id=f"img-{uuid.uuid4().hex[:8]}",
                prompt=prompt,
                enhanced_prompt=final_prompt,
                style=style,
                resolution=resolution,
                image_data=image_data,
            )
            self._gallery.append(generated)

            # 6. Guardar en memoria — la IA aprende de lo que generas
            if self._memory_service:
                try:
                    await self._memory_service.store_result(
                        content=f"Prompt: {prompt} | Estilo: {style} | Prompt mejorado: {final_prompt}",
                        namespace="imagen:usuario",
                        memory_type="preference",
                        source="image_generation",
                        metadata={"prompt": prompt, "style": style, "resolution": resolution,
                                  "enhanced_prompt": final_prompt, "image_id": generated.id},
                    )
                except Exception:
                    pass  # No bloquear generación por error de memoria

            # 7. Liberar GPU para que Ollama pueda volver
            await self.release_gpu()
            self._sd_pipeline = None

            return {
                "image_id": generated.id,
                "prompt": prompt,
                "enhanced_prompt": final_prompt,
                "resolution": resolution,
                "image_base64": base64.b64encode(image_data).decode("utf-8"),
            }

        except Exception as e:
            await self.release_gpu()
            self._sd_pipeline = None
            return {"error": f"Error generando imagen: {str(e)}"}
        finally:
            self._is_generating = False

    async def _load_sd_pipeline(self):
        """Carga el pipeline de Stable Diffusion 1.5."""
        try:
            from diffusers import StableDiffusionPipeline
            import torch

            pipeline = StableDiffusionPipeline.from_pretrained(
                "runwayml/stable-diffusion-v1-5",
                torch_dtype=torch.float16,
                safety_checker=None,
            )
            pipeline = pipeline.to("cuda")
            pipeline.enable_attention_slicing()
            pipeline.enable_vae_slicing()
            return pipeline
        except ImportError:
            raise RuntimeError(
                "diffusers no instalado. Ejecutar: pip install diffusers transformers accelerate"
            )

    async def _run_sd_inference(
        self, pipeline, prompt: str, width: int, height: int
    ) -> bytes:
        """Ejecuta inferencia de SD y retorna bytes de imagen PNG."""
        import torch
        from src.core.thermal_guard import get_thermal_guard

        thermal = get_thermal_guard()
        num_steps = 20

        def _thermal_callback(pipe, step_index, timestep, callback_kwargs):
            thermal.check_and_wait_async_safe(step=step_index + 1, total=num_steps)
            return callback_kwargs

        with torch.no_grad():
            result = pipeline(
                prompt=prompt,
                width=width,
                height=height,
                num_inference_steps=num_steps,
                guidance_scale=7.5,
                callback_on_step_end=_thermal_callback,
            )

        image = result.images[0]
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()
