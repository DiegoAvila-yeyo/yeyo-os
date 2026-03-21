## ═══════════════════════════════════════
## MICRO-FASE 5.2 — Image Node (Generation)
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 5.2-1 [VSCODE] — Nodo de generación de imágenes con Stable Diffusion 1.5

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 5.2 de Capa 5 (Órganos): crear el Image Node para generación de imágenes con Stable Diffusion 1.5.

CONTEXTO:
- Micro-fases 5.0-5.1 completadas: NodeBase, Chat Node
- SD 1.5 via diffusers library (o Ollama si soporta)
- VRAM: ~2500MB — NO PUEDE correr simultáneamente con Ollama 3B (3GB total)
- CRÍTICO: Cuando se genera imagen, Ollama DEBE ser descargado primero (GPU scheduler)
- GPU Scheduler P1 (prioridad alta) cuando usuario inicia generación
- Prompt enhancement: usar Ollama para mejorar el prompt ANTES de generar
- Resolución máxima: 512x512 para 3GB VRAM
- Frontend: Next.js 14 + Tailwind + Zustand
- Hardware: GTX 1060 3GB VRAM, 16GB RAM

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear estructura de directorios:
   mkdir -p src/nodes/image
   mkdir -p tests/unit/nodes/image
   mkdir -p frontend/src/components/nodes/image

2. Crear archivo src/nodes/image/__init__.py:

   Ruta: ~/yeyo-os/src/nodes/image/__init__.py
   Contenido:
   from .service import ImageGenerationNode

3. Crear archivo src/nodes/image/service.py:

   Ruta: ~/yeyo-os/src/nodes/image/service.py
   Contenido:

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
   from pathlib import Path

   from src.nodes.base import NodeBase, PrivilegeLevel


   # Resoluciones seguras para 3GB VRAM
   SAFE_RESOLUTIONS = {
       "256x256": (256, 256),
       "384x384": (384, 384),
       "512x512": (512, 512),
       "512x384": (512, 384),
       "384x512": (384, 512),
   }

   MAX_RESOLUTION = 512  # Máximo en cualquier dimensión
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
           pass  # SD se carga lazy en generate()

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
           """Usa Ollama para mejorar el prompt antes de generar."""
           from src.ia import IAProvider
           from src.ia.ollama_provider import OllamaProvider

           provider = OllamaProvider()
           response = await provider.generate(
               prompt=f"Enhance this image generation prompt. Make it more detailed and descriptive. "
                       f"Only return the enhanced prompt, nothing else.\n\nOriginal: {prompt}",
               system="You are an expert at writing Stable Diffusion prompts. "
                      "Add details about lighting, composition, style, and quality. "
                      "Keep it under 200 words.",
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
           FLUJO CRÍTICO:
           1. Enhance prompt con Ollama
           2. Solicitar GPU al scheduler (P1) — esto descarga Ollama de VRAM
           3. Cargar SD 1.5 en VRAM
           4. Generar imagen
           5. Liberar GPU — Ollama puede volver a cargarse
           """
           if self._is_generating:
               return {"error": "Ya hay una generación en curso"}

           # Validar resolución
           if resolution not in SAFE_RESOLUTIONS:
               return {"error": f"Resolución no soportada. Usar: {list(SAFE_RESOLUTIONS.keys())}"}

           width, height = SAFE_RESOLUTIONS[resolution]
           if width > MAX_RESOLUTION or height > MAX_RESOLUTION:
               return {"error": f"Resolución máxima: {MAX_RESOLUTION}x{MAX_RESOLUTION}"}

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
                   priority=1,  # P1 = máxima prioridad (usuario inició)
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

               # 6. Liberar GPU para que Ollama pueda volver
               await self.release_gpu()
               self._sd_pipeline = None  # Liberar modelo de memoria

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
               pipeline.enable_attention_slicing()  # Reduce VRAM usage
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

           with torch.no_grad():
               result = pipeline(
                   prompt=prompt,
                   width=width,
                   height=height,
                   num_inference_steps=20,
                   guidance_scale=7.5,
               )

           image = result.images[0]
           buffer = BytesIO()
           image.save(buffer, format="PNG")
           return buffer.getvalue()

4. Crear archivo frontend/src/components/nodes/image/ImageGenerationNode.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/nodes/image/ImageGenerationNode.tsx
   Contenido:

   /**
    * YeyoOS — Image Generation Node Frontend
    * Micro-fase 5.2 — Capa 5: Órganos
    */

   'use client';

   import React, { useState } from 'react';
   import NodeWrapper from '../NodeWrapper';

   interface GalleryItem {
     id: string;
     prompt: string;
     resolution: string;
     created_at: string;
   }

   interface ImageGenerationNodeProps {
     nodeId: string;
     styles: string[];
     resolutions: string[];
     gallery: GalleryItem[];
     isGenerating: boolean;
     onGenerate: (prompt: string, style: string, resolution: string) => void;
     onImageClick: (imageId: string) => void;
     onClose: (nodeId: string) => void;
   }

   export default function ImageGenerationNode({
     nodeId,
     styles,
     resolutions,
     gallery,
     isGenerating,
     onGenerate,
     onImageClick,
     onClose,
   }: ImageGenerationNodeProps) {
     const [prompt, setPrompt] = useState('');
     const [style, setStyle] = useState('none');
     const [resolution, setResolution] = useState('512x512');

     const handleGenerate = () => {
       if (!prompt.trim()) return;
       onGenerate(prompt.trim(), style, resolution);
     };

     return (
       <NodeWrapper nodeId={nodeId} title="Image Generation" icon="🎨" onClose={onClose}>
         <div className="flex flex-col h-full gap-3">
           {/* Prompt input */}
           <div className="space-y-2">
             <textarea
               value={prompt}
               onChange={(e) => setPrompt(e.target.value)}
               placeholder="Describe la imagen que quieres generar..."
               rows={3}
               className="w-full px-3 py-2 text-sm bg-gray-700 text-white
                          rounded-lg border border-gray-600 focus:border-purple-500
                          focus:outline-none resize-none"
             />
             <div className="flex gap-2">
               {/* Style selector */}
               <select
                 value={style}
                 onChange={(e) => setStyle(e.target.value)}
                 className="flex-1 px-2 py-1 text-sm bg-gray-700 text-white
                            rounded border border-gray-600"
               >
                 {styles.map((s) => (
                   <option key={s} value={s}>{s}</option>
                 ))}
               </select>

               {/* Resolution selector */}
               <select
                 value={resolution}
                 onChange={(e) => setResolution(e.target.value)}
                 className="flex-1 px-2 py-1 text-sm bg-gray-700 text-white
                            rounded border border-gray-600"
               >
                 {resolutions.map((r) => (
                   <option key={r} value={r}>{r}</option>
                 ))}
               </select>
             </div>
             <button
               onClick={handleGenerate}
               disabled={!prompt.trim() || isGenerating}
               className="w-full px-4 py-2 bg-purple-600 text-white rounded-lg
                          text-sm font-medium hover:bg-purple-500
                          disabled:opacity-50 disabled:cursor-not-allowed"
             >
               {isGenerating ? '⏳ Generando...' : '🎨 Generar Imagen'}
             </button>
           </div>

           {/* Gallery */}
           <div className="flex-1 overflow-y-auto">
             <h3 className="text-xs text-gray-400 mb-2">Galería</h3>
             <div className="grid grid-cols-2 gap-2">
               {gallery.map((item) => (
                 <div
                   key={item.id}
                   onClick={() => onImageClick(item.id)}
                   className="cursor-pointer rounded-lg border border-gray-600
                              hover:border-purple-500 overflow-hidden bg-gray-800"
                 >
                   <div className="aspect-square bg-gray-700 flex items-center
                                   justify-center text-2xl">
                     🖼️
                   </div>
                   <p className="text-xs text-gray-400 p-1 truncate">{item.prompt}</p>
                 </div>
               ))}
             </div>
           </div>
         </div>
       </NodeWrapper>
     );
   }

5. Crear archivo tests/unit/nodes/image/__init__.py (vacío):

   Ruta: ~/yeyo-os/tests/unit/nodes/image/__init__.py
   Contenido: (archivo vacío)

6. Crear archivo tests/unit/nodes/image/test_image_gen.py:

   Ruta: ~/yeyo-os/tests/unit/nodes/image/test_image_gen.py
   Contenido:

   """Tests para Image Generation Node — Micro-fase 5.2"""

   import pytest
   from unittest.mock import AsyncMock, patch, MagicMock
   from src.nodes.image.service import (
       ImageGenerationNode, SAFE_RESOLUTIONS, MAX_RESOLUTION,
       SD_VRAM_REQUIRED, STYLE_PRESETS,
   )


   class TestImageGenLifecycle:

       def test_node_name(self):
           node = ImageGenerationNode()
           assert node.name == "Image Generation"

       @pytest.mark.asyncio
       async def test_render_ui_has_styles_and_resolutions(self):
           node = ImageGenerationNode()
           ui = await node.render_ui()
           assert "styles" in ui["props"]
           assert "resolutions" in ui["props"]
           assert len(ui["props"]["styles"]) == len(STYLE_PRESETS)
           assert len(ui["props"]["resolutions"]) == len(SAFE_RESOLUTIONS)


   class TestImageGenResolution:

       def test_max_resolution_is_512(self):
           assert MAX_RESOLUTION == 512

       def test_all_resolutions_within_limit(self):
           for name, (w, h) in SAFE_RESOLUTIONS.items():
               assert w <= MAX_RESOLUTION, f"{name} width {w} > {MAX_RESOLUTION}"
               assert h <= MAX_RESOLUTION, f"{name} height {h} > {MAX_RESOLUTION}"

       @pytest.mark.asyncio
       async def test_invalid_resolution_rejected(self):
           node = ImageGenerationNode()
           result = await node._generate_image(
               prompt="test", resolution="1024x1024"
           )
           assert "error" in result


   class TestImageGenGPU:

       def test_sd_vram_required(self):
           assert SD_VRAM_REQUIRED == 2500

       @pytest.mark.asyncio
       async def test_gpu_released_after_generation(self):
           node = ImageGenerationNode()
           node.request_gpu = AsyncMock(return_value=True)
           node.release_gpu = AsyncMock()
           node._enhance_prompt = AsyncMock(return_value={
               "original_prompt": "test",
               "enhanced_prompt": "test enhanced",
           })
           node._load_sd_pipeline = AsyncMock(return_value=MagicMock())
           node._run_sd_inference = AsyncMock(return_value=b"fake_png_data")

           await node._generate_image(prompt="test cat")
           node.release_gpu.assert_called_once()

       @pytest.mark.asyncio
       async def test_gpu_released_on_error(self):
           node = ImageGenerationNode()
           node.request_gpu = AsyncMock(return_value=True)
           node.release_gpu = AsyncMock()
           node._enhance_prompt = AsyncMock(return_value={
               "original_prompt": "test",
               "enhanced_prompt": "test enhanced",
           })
           node._load_sd_pipeline = AsyncMock(side_effect=RuntimeError("boom"))

           result = await node._generate_image(prompt="test")
           assert "error" in result
           node.release_gpu.assert_called()


   class TestImageGenPromptEnhancement:

       @pytest.mark.asyncio
       async def test_enhance_prompt_calls_ollama(self):
           node = ImageGenerationNode()
           mock_provider = MagicMock()
           mock_provider.generate = AsyncMock(return_value=MagicMock(
               content="A beautiful cat sitting on a window"
           ))

           with patch("src.nodes.image.service.OllamaProvider", return_value=mock_provider):
               result = await node._enhance_prompt("cat")
               assert result["original_prompt"] == "cat"
               assert "beautiful" in result["enhanced_prompt"].lower() or len(result["enhanced_prompt"]) > 0

7. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/nodes/image/test_image_gen.py -v

VERIFICAR:
- [ ] ImageGenerationNode hereda de NodeBase
- [ ] GPU scheduler se solicita con P1 antes de generar
- [ ] GPU se libera SIEMPRE después de generar (incluso en error)
- [ ] Resolución limitada a 512x512 máximo
- [ ] Prompt enhancement funciona con Ollama
- [ ] Pipeline SD se descarga de VRAM después de generar
- [ ] Galería almacena imágenes generadas
- [ ] Frontend con prompt, selector de estilo/resolución, galería
- [ ] TODOS los tests pasan

SI FALLA:
- diffusers no instalado: tests usan mocks, no necesitan diffusers
- GPU scheduler mock: verificar que los tests mockean correctamente
- Import error: verificar __init__.py

NO HACER:
- No instalar diffusers en este prompt (se instala cuando se use realmente)
- No implementar img2img (eso es 5.3)
- No implementar MiniChat en la imagen (eso es 5.4)
- No usar GPU para minería JAMÁS

GATE: ImageGenerationNode genera imágenes con SD 1.5, GPU scheduler funciona, resolución limitada, prompt enhancement, galería, GPU liberada siempre, todos los tests pasan.
```
