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
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.used,memory.free,temperature.gpu,utilization.gpu",
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
        except Exception:
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
