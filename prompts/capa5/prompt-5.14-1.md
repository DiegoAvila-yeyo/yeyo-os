## ═══════════════════════════════════════
## MICRO-FASE 5.14 — Config Node
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 5.14-1 [VSCODE] — UI de configuración del sistema

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 5.14 de Capa 5 (Órganos): crear el Config Node para configuración del sistema.

CONTEXTO:
- Micro-fases 5.0-5.13 completadas
- Secciones: Models (Ollama), GPU (scheduler stats), Memory (tier stats), Security (permisos), Backups, About
- Monitor GPU en tiempo real (barra de uso VRAM)
- Descarga/cambio de modelos Ollama
- Settings se guardan en config persistente
- Frontend: Next.js 14 + Tailwind + Zustand
- Backend: Python 3.11 + FastAPI + Ollama qwen2.5:3b
- Hardware: GTX 1060 3GB VRAM, 16GB RAM

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear estructura:
   mkdir -p src/nodes/config
   mkdir -p tests/unit/nodes/config
   mkdir -p frontend/src/components/nodes/config

2. Crear archivo src/nodes/config/__init__.py:

   Ruta: ~/yeyo-os/src/nodes/config/__init__.py
   Contenido:
   from .service import ConfigNode

3. Crear archivo src/nodes/config/service.py:

   Ruta: ~/yeyo-os/src/nodes/config/service.py
   Contenido:

   """
   YeyoOS — Config Node
   Micro-fase 5.14 — Capa 5: Órganos

   UI de configuración del sistema: modelos, GPU, memoria, seguridad, backups.
   """

   import httpx
   from typing import Optional
   from dataclasses import dataclass
   from datetime import datetime, timezone

   from src.nodes.base import NodeBase, PrivilegeLevel


   OLLAMA_BASE_URL = "http://localhost:11434"

   CONFIG_SECTIONS = [
       "models", "gpu", "memory", "security", "backups", "about",
   ]


   @dataclass
   class GPUStats:
       """Estadísticas de la GPU."""
       name: str
       total_vram_mb: int
       used_vram_mb: int
       free_vram_mb: int
       temperature: Optional[int] = None
       utilization: Optional[int] = None


   @dataclass
   class ModelInfo:
       """Información de un modelo Ollama."""
       name: str
       size: str
       modified_at: str
       is_active: bool = False


   class ConfigNode(NodeBase):
       """
       Nodo de Configuración — órgano de administración de YeyoOS.
       Modelos, GPU, memoria, seguridad, backups, about.
       """

       def __init__(self):
           super().__init__(
               name="Config",
               version="1.0.0",
               privilege_level=PrivilegeLevel.ADMIN,
               container_config={"memory_limit": "256m", "cpu_shares": 256},
           )
           self._settings: dict = {}

       async def initialize(self) -> None:
           pass

       async def render_ui(self) -> dict:
           return {
               "component": "ConfigNode",
               "props": {
                   "sections": CONFIG_SECTIONS,
                   "currentSettings": self._settings,
               },
           }

       async def process(self, input_data: dict) -> dict:
           action = input_data.get("action", "")

           if action == "get_models":
               return await self._get_models()
           elif action == "pull_model":
               return await self._pull_model(input_data.get("model_name", ""))
           elif action == "delete_model":
               return await self._delete_model(input_data.get("model_name", ""))
           elif action == "get_gpu_stats":
               return await self._get_gpu_stats()
           elif action == "get_memory_stats":
               return await self._get_memory_stats()
           elif action == "update_setting":
               return self._update_setting(
                   input_data.get("key", ""), input_data.get("value")
               )
           elif action == "get_about":
               return self._get_about()
           else:
               return {"error": f"Acción desconocida: {action}"}

       async def cleanup(self) -> None:
           pass

       # ═══════════════════════════════════
       # MODELOS OLLAMA
       # ═══════════════════════════════════

       async def _get_models(self) -> dict:
           """Lista modelos Ollama instalados."""
           try:
               async with httpx.AsyncClient(timeout=10.0) as client:
                   response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
                   response.raise_for_status()
                   data = response.json()
                   models = [
                       {
                           "name": m["name"],
                           "size": self._format_size(m.get("size", 0)),
                           "modified_at": m.get("modified_at", ""),
                       }
                       for m in data.get("models", [])
                   ]
                   return {"models": models}
           except Exception as e:
               return {"error": f"Error conectando con Ollama: {e}"}

       async def _pull_model(self, model_name: str) -> dict:
           """Descarga un modelo de Ollama."""
           if not model_name.strip():
               return {"error": "Nombre de modelo requerido"}
           try:
               async with httpx.AsyncClient(timeout=600.0) as client:
                   response = await client.post(
                       f"{OLLAMA_BASE_URL}/api/pull",
                       json={"name": model_name, "stream": False},
                   )
                   return {"model": model_name, "status": "downloaded"}
           except Exception as e:
               return {"error": f"Error descargando modelo: {e}"}

       async def _delete_model(self, model_name: str) -> dict:
           """Elimina un modelo de Ollama."""
           if not model_name.strip():
               return {"error": "Nombre de modelo requerido"}
           try:
               async with httpx.AsyncClient(timeout=30.0) as client:
                   response = await client.delete(
                       f"{OLLAMA_BASE_URL}/api/delete",
                       json={"name": model_name},
                   )
                   return {"model": model_name, "status": "deleted"}
           except Exception as e:
               return {"error": f"Error eliminando modelo: {e}"}

       # ═══════════════════════════════════
       # GPU STATS
       # ═══════════════════════════════════

       async def _get_gpu_stats(self) -> dict:
           """Obtiene estadísticas de la GPU."""
           import asyncio
           try:
               process = await asyncio.create_subprocess_exec(
                   "nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free,temperature.gpu,utilization.gpu",
                   "--format=csv,noheader,nounits",
                   stdout=asyncio.subprocess.PIPE,
                   stderr=asyncio.subprocess.PIPE,
               )
               stdout, _ = await process.communicate()
               parts = stdout.decode().strip().split(", ")
               if len(parts) >= 4:
                   return {
                       "name": parts[0],
                       "total_vram_mb": int(parts[1]),
                       "used_vram_mb": int(parts[2]),
                       "free_vram_mb": int(parts[3]),
                       "temperature": int(parts[4]) if len(parts) > 4 else None,
                       "utilization": int(parts[5]) if len(parts) > 5 else None,
                   }
           except Exception as e:
               pass
           return {"error": "GPU stats no disponibles"}

       async def _get_memory_stats(self) -> dict:
           """Obtiene estadísticas de memoria del sistema."""
           try:
               import psutil
               vm = psutil.virtual_memory()
               return {
                   "total_mb": vm.total // (1024 * 1024),
                   "used_mb": vm.used // (1024 * 1024),
                   "free_mb": vm.available // (1024 * 1024),
                   "percent": vm.percent,
               }
           except ImportError:
               return {"error": "psutil no instalado"}

       # ═══════════════════════════════════
       # SETTINGS
       # ═══════════════════════════════════

       def _update_setting(self, key: str, value) -> dict:
           """Actualiza un setting."""
           if not key.strip():
               return {"error": "Key requerido"}
           self._settings[key] = value
           return {"key": key, "value": value, "updated": True}

       def _get_about(self) -> dict:
           return {
               "name": "YeyoOS",
               "version": "0.5.0",
               "capa": "5 — Órganos",
               "hardware": "GTX 1060 3GB VRAM, 16GB RAM",
               "model": "qwen2.5:3b",
               "author": "Yeyo",
           }

       @staticmethod
       def _format_size(bytes_size: int) -> str:
           for unit in ["B", "KB", "MB", "GB"]:
               if bytes_size < 1024:
                   return f"{bytes_size:.1f} {unit}"
               bytes_size /= 1024
           return f"{bytes_size:.1f} TB"

4. Crear archivo frontend/src/components/nodes/config/ConfigNode.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/nodes/config/ConfigNode.tsx
   Contenido:

   /**
    * YeyoOS — Config Node Frontend
    * Micro-fase 5.14 — Capa 5: Órganos
    */

   'use client';

   import React, { useState } from 'react';
   import NodeWrapper from '../NodeWrapper';

   interface ConfigNodeProps {
     nodeId: string;
     sections: string[];
     gpuStats?: { name: string; total_vram_mb: number; used_vram_mb: number; free_vram_mb: number };
     models?: { name: string; size: string }[];
     onGetModels: () => void;
     onPullModel: (name: string) => void;
     onGetGPUStats: () => void;
     onUpdateSetting: (key: string, value: any) => void;
     onClose: (nodeId: string) => void;
   }

   export default function ConfigNode({
     nodeId, sections, gpuStats, models,
     onGetModels, onPullModel, onGetGPUStats, onUpdateSetting, onClose,
   }: ConfigNodeProps) {
     const [activeSection, setActiveSection] = useState('about');
     const [modelInput, setModelInput] = useState('');

     const vramPercent = gpuStats
       ? (gpuStats.used_vram_mb / gpuStats.total_vram_mb) * 100
       : 0;

     return (
       <NodeWrapper nodeId={nodeId} title="Config" icon="⚙️" onClose={onClose}>
         <div className="flex h-full">
           {/* Sidebar */}
           <div className="w-40 bg-gray-800 border-r border-gray-700 p-2 space-y-1 shrink-0">
             {sections.map((section) => (
               <button
                 key={section}
                 onClick={() => setActiveSection(section)}
                 className={`w-full px-2 py-1 text-xs text-left rounded
                   ${activeSection === section
                     ? 'bg-gray-600 text-white'
                     : 'text-gray-400 hover:text-white hover:bg-gray-700'}`}
               >
                 {section.charAt(0).toUpperCase() + section.slice(1)}
               </button>
             ))}
           </div>

           {/* Content */}
           <div className="flex-1 p-3 space-y-3">
             {activeSection === 'gpu' && gpuStats && (
               <div>
                 <h3 className="text-sm font-medium text-white mb-2">GPU Monitor</h3>
                 <p className="text-xs text-gray-400">{gpuStats.name}</p>
                 <div className="mt-2">
                   <div className="flex justify-between text-xs text-gray-400 mb-1">
                     <span>VRAM</span>
                     <span>{gpuStats.used_vram_mb}MB / {gpuStats.total_vram_mb}MB</span>
                   </div>
                   <div className="w-full bg-gray-700 rounded-full h-3">
                     <div
                       className={`h-3 rounded-full transition-all ${
                         vramPercent > 80 ? 'bg-red-500' :
                         vramPercent > 50 ? 'bg-yellow-500' : 'bg-green-500'
                       }`}
                       style={{ width: `${vramPercent}%` }}
                     />
                   </div>
                 </div>
               </div>
             )}

             {activeSection === 'models' && (
               <div>
                 <h3 className="text-sm font-medium text-white mb-2">Modelos Ollama</h3>
                 <div className="flex gap-2 mb-3">
                   <input
                     type="text"
                     value={modelInput}
                     onChange={(e) => setModelInput(e.target.value)}
                     placeholder="ej: qwen2.5:3b"
                     className="flex-1 px-2 py-1 text-xs bg-gray-700 text-white
                                rounded border border-gray-600"
                   />
                   <button onClick={() => { onPullModel(modelInput); setModelInput(''); }}
                     className="px-2 py-1 text-xs bg-green-600 text-white rounded">
                     Descargar
                   </button>
                 </div>
                 {models?.map((m) => (
                   <div key={m.name} className="flex justify-between px-2 py-1 text-xs
                                                 bg-gray-800 rounded mb-1">
                     <span className="text-gray-300">{m.name}</span>
                     <span className="text-gray-500">{m.size}</span>
                   </div>
                 ))}
               </div>
             )}

             {activeSection === 'about' && (
               <div className="text-xs text-gray-400 space-y-1">
                 <h3 className="text-sm font-medium text-white mb-2">About YeyoOS</h3>
                 <p>Version: 0.5.0</p>
                 <p>Capa: 5 — Órganos</p>
                 <p>Hardware: GTX 1060 3GB VRAM, 16GB RAM</p>
                 <p>Modelo: qwen2.5:3b</p>
                 <p>Autor: Yeyo</p>
               </div>
             )}
           </div>
         </div>
       </NodeWrapper>
     );
   }

5. Crear tests/unit/nodes/config/__init__.py (vacío):

   Ruta: ~/yeyo-os/tests/unit/nodes/config/__init__.py
   Contenido: (archivo vacío)

6. Crear archivo tests/unit/nodes/config/test_config_node.py:

   Ruta: ~/yeyo-os/tests/unit/nodes/config/test_config_node.py
   Contenido:

   """Tests para Config Node — Micro-fase 5.14"""

   import pytest
   from unittest.mock import AsyncMock, patch, MagicMock
   from src.nodes.config.service import ConfigNode, CONFIG_SECTIONS


   class TestConfigSections:

       def test_all_sections_defined(self):
           expected = {"models", "gpu", "memory", "security", "backups", "about"}
           assert set(CONFIG_SECTIONS) == expected

       @pytest.mark.asyncio
       async def test_render_ui_has_sections(self):
           node = ConfigNode()
           ui = await node.render_ui()
           assert "sections" in ui["props"]


   class TestConfigSettings:

       def test_update_setting(self):
           node = ConfigNode()
           result = node._update_setting("theme", "dark")
           assert result["updated"] is True
           assert node._settings["theme"] == "dark"

       def test_update_empty_key_rejected(self):
           node = ConfigNode()
           result = node._update_setting("", "value")
           assert "error" in result


   class TestConfigAbout:

       def test_about_info(self):
           node = ConfigNode()
           about = node._get_about()
           assert about["name"] == "YeyoOS"
           assert "GTX 1060" in about["hardware"]


   class TestConfigModels:

       @pytest.mark.asyncio
       async def test_get_models_calls_ollama(self):
           node = ConfigNode()
           mock_response = MagicMock()
           mock_response.json.return_value = {
               "models": [{"name": "qwen2.5:3b", "size": 2000000000, "modified_at": ""}]
           }
           mock_response.raise_for_status = MagicMock()

           with patch("httpx.AsyncClient") as mock_client:
               mock_instance = MagicMock()
               mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
               mock_instance.__aexit__ = AsyncMock(return_value=False)
               mock_instance.get = AsyncMock(return_value=mock_response)
               mock_client.return_value = mock_instance

               result = await node._get_models()
               assert "models" in result

       @pytest.mark.asyncio
       async def test_pull_empty_name_rejected(self):
           node = ConfigNode()
           result = await node._pull_model("")
           assert "error" in result

   class TestConfigFormatSize:

       def test_format_bytes(self):
           assert ConfigNode._format_size(500) == "500.0 B"

       def test_format_mb(self):
           result = ConfigNode._format_size(1024 * 1024 * 500)
           assert "MB" in result

       def test_format_gb(self):
           result = ConfigNode._format_size(1024 * 1024 * 1024 * 2)
           assert "GB" in result

7. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/nodes/config/test_config_node.py -v

VERIFICAR:
- [ ] Todas las secciones definidas: models, gpu, memory, security, backups, about
- [ ] GPU stats display con barra VRAM
- [ ] Model download/switch funciona
- [ ] Settings se guardan
- [ ] About muestra info correcta del sistema
- [ ] Frontend con sidebar de secciones y contenido
- [ ] TODOS los tests pasan

SI FALLA:
- httpx: `pip install httpx`
- psutil: `pip install psutil`
- nvidia-smi: puede no estar disponible, tests usan mock

NO HACER:
- No implementar backup real aún (solo placeholder de sección)
- No acceder a security settings sin privilegio ADMIN
- No eliminar modelo qwen2.5:3b (es el modelo base)

GATE: ConfigNode con todas las secciones, GPU monitor, model management, settings persistentes, about info, todos los tests pasan.
```
