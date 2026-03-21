## ═══════════════════════════════════════
## MICRO-FASE 5.3 — Image Node (img2img + Analysis)
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 5.3-1 [VSCODE] — Transformación img2img y análisis con LLaVA

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 5.3 de Capa 5 (Órganos): añadir img2img (transformar imágenes existentes) y análisis de imágenes con LLaVA al Image Node.

CONTEXTO:
- Micro-fase 5.2 completada: ImageGenerationNode con SD 1.5, prompt enhancement, galería
- img2img: modificar imágenes existentes con prompts de texto
- LLaVA: modelo de visión para describir/analizar imágenes
- LLaVA via Ollama: llava:7b ideal pero necesita VRAM cuidadosa
- Plan B: usar llava:3b o descripción por texto si VRAM insuficiente
- VRAM total: 3GB — gestión cuidadosa obligatoria
- Hardware: GTX 1060 3GB VRAM, 16GB RAM

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/nodes/image/img2img.py:

   Ruta: ~/yeyo-os/src/nodes/image/img2img.py
   Contenido:

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
   from typing import Optional
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
           FLUJO: solicitar GPU → cargar img2img → transformar → liberar GPU.
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


2. Crear archivo src/nodes/image/analysis.py:

   Ruta: ~/yeyo-os/src/nodes/image/analysis.py
   Contenido:

   """
   YeyoOS — Image Analysis with LLaVA
   Micro-fase 5.3 — Capa 5: Órganos

   Análisis de imágenes usando LLaVA (modelo de visión) via Ollama.
   Plan B: llava:3b si VRAM insuficiente para 7b.
   """

   import base64
   import httpx
   from typing import Optional


   # Modelos de visión en orden de preferencia
   VISION_MODELS = [
       {"name": "llava:7b", "vram_mb": 2800},
       {"name": "llava:3b", "vram_mb": 1500},
   ]

   OLLAMA_BASE_URL = "http://localhost:11434"


   class ImageAnalysisService:
       """Servicio de análisis de imágenes con LLaVA."""

       def __init__(self, ollama_url: str = OLLAMA_BASE_URL):
           self._ollama_url = ollama_url
           self._active_model: Optional[str] = None

       async def analyze(
           self, image_data: bytes, question: str = "Describe esta imagen en detalle."
       ) -> dict:
           """
           Analiza una imagen con LLaVA.
           Intenta llava:7b primero, fallback a llava:3b.
           """
           image_b64 = base64.b64encode(image_data).decode("utf-8")

           for model_info in VISION_MODELS:
               model_name = model_info["name"]
               try:
                   result = await self._query_llava(
                       model=model_name,
                       image_b64=image_b64,
                       prompt=question,
                   )
                   self._active_model = model_name
                   return {
                       "description": result,
                       "model_used": model_name,
                       "question": question,
                   }
               except Exception:
                   continue

           return {
               "error": "No se pudo analizar la imagen. Ningún modelo de visión disponible.",
               "fallback": "text_only",
           }

       async def _query_llava(
           self, model: str, image_b64: str, prompt: str
       ) -> str:
           """Consulta LLaVA via Ollama API."""
           async with httpx.AsyncClient(timeout=120.0) as client:
               response = await client.post(
                   f"{self._ollama_url}/api/generate",
                   json={
                       "model": model,
                       "prompt": prompt,
                       "images": [image_b64],
                       "stream": False,
                   },
               )
               response.raise_for_status()
               data = response.json()
               return data.get("response", "")

       async def get_available_model(self) -> Optional[str]:
           """Retorna el modelo de visión disponible."""
           async with httpx.AsyncClient(timeout=10.0) as client:
               try:
                   response = await client.get(f"{self._ollama_url}/api/tags")
                   response.raise_for_status()
                   models = [m["name"] for m in response.json().get("models", [])]
                   for model_info in VISION_MODELS:
                       if model_info["name"] in models:
                           return model_info["name"]
               except Exception:
                   pass
           return None

3. Actualizar src/nodes/image/__init__.py:

   Ruta: ~/yeyo-os/src/nodes/image/__init__.py
   Contenido:
   from .service import ImageGenerationNode
   from .img2img import Img2ImgService
   from .analysis import ImageAnalysisService

4. Crear archivo tests/unit/nodes/image/test_img2img.py:

   Ruta: ~/yeyo-os/tests/unit/nodes/image/test_img2img.py
   Contenido:

   """Tests para img2img + Analysis — Micro-fase 5.3"""

   import pytest
   from unittest.mock import AsyncMock, patch, MagicMock
   from src.nodes.image.img2img import Img2ImgService
   from src.nodes.image.analysis import ImageAnalysisService, VISION_MODELS


   class TestImg2Img:

       @pytest.mark.asyncio
       async def test_transform_invalid_resolution_rejected(self):
           mock_node = MagicMock()
           service = Img2ImgService(mock_node)
           result = await service.transform(
               source_image=b"fake", prompt="test", resolution="2048x2048"
           )
           assert "error" in result

       @pytest.mark.asyncio
       async def test_strength_clamped(self):
           mock_node = MagicMock()
           mock_node.request_gpu = AsyncMock(return_value=True)
           mock_node.release_gpu = AsyncMock()
           service = Img2ImgService(mock_node)
           service._run_img2img = AsyncMock(return_value=b"result_png")
           result = await service.transform(
               source_image=b"fake", prompt="test", strength=2.0
           )
           assert "error" not in result

       @pytest.mark.asyncio
       async def test_gpu_released_after_transform(self):
           mock_node = MagicMock()
           mock_node.request_gpu = AsyncMock(return_value=True)
           mock_node.release_gpu = AsyncMock()
           service = Img2ImgService(mock_node)
           service._run_img2img = AsyncMock(return_value=b"result_png")
           await service.transform(source_image=b"fake", prompt="test")
           mock_node.release_gpu.assert_called_once()

       @pytest.mark.asyncio
       async def test_gpu_released_on_error(self):
           mock_node = MagicMock()
           mock_node.request_gpu = AsyncMock(return_value=True)
           mock_node.release_gpu = AsyncMock()
           service = Img2ImgService(mock_node)
           service._run_img2img = AsyncMock(side_effect=RuntimeError("fail"))
           result = await service.transform(source_image=b"fake", prompt="test")
           assert "error" in result
           mock_node.release_gpu.assert_called_once()


   class TestImageAnalysis:

       def test_vision_models_exist(self):
           assert len(VISION_MODELS) >= 2
           names = [m["name"] for m in VISION_MODELS]
           assert "llava:7b" in names
           assert "llava:3b" in names

       @pytest.mark.asyncio
       async def test_analyze_with_fallback(self):
           service = ImageAnalysisService()
           service._query_llava = AsyncMock(
               side_effect=[Exception("7b fail"), "A beautiful landscape"]
           )
           result = await service.analyze(b"fake_image", "Describe this")
           assert result["model_used"] == "llava:3b"
           assert "landscape" in result["description"]

       @pytest.mark.asyncio
       async def test_analyze_all_models_fail(self):
           service = ImageAnalysisService()
           service._query_llava = AsyncMock(side_effect=Exception("all fail"))
           result = await service.analyze(b"fake_image")
           assert "error" in result
           assert result["fallback"] == "text_only"

       @pytest.mark.asyncio
       async def test_analyze_first_model_success(self):
           service = ImageAnalysisService()
           service._query_llava = AsyncMock(return_value="A cat sitting on a chair")
           result = await service.analyze(b"fake_image")
           assert result["model_used"] == "llava:7b"

5. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/nodes/image/test_img2img.py -v

VERIFICAR:
- [ ] img2img transforma imágenes con prompts
- [ ] LLaVA analiza imágenes con fallback (7b → 3b → error graceful)
- [ ] GPU se libera SIEMPRE (incluso en error)
- [ ] Strength clamped entre 0.1 y 1.0
- [ ] VRAM gestionada correctamente — modelos en orden de preferencia
- [ ] TODOS los tests pasan

SI FALLA:
- Import error: verificar __init__.py actualizado
- httpx: `pip install httpx` (si no está)
- Mocks: verificar que _query_llava se mockea correctamente

NO HACER:
- No instalar diffusers ni llava realmente (tests usan mocks)
- No implementar MiniChat (eso es 5.4)
- No conectar con GPU scheduler real

GATE: img2img transforma imágenes, LLaVA analiza con fallback, VRAM gestionada, GPU liberada siempre, todos los tests pasan.
```
