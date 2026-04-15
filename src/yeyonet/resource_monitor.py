"""
YeyoNet — ResourceMonitor.
Detecta y reporta recursos del sistema (CPU, RAM, GPU).
"""
from __future__ import annotations

import asyncio
import logging
import platform
import shutil

from .models import NodeResources

logger = logging.getLogger("yeyonet.resources")

REPORT_INTERVAL = 30.0  # segundos


class ResourceMonitor:
    """Monitorea recursos locales del nodo."""

    def __init__(self):
        self._running = False
        self._task: asyncio.Task | None = None
        self._callback = None
        self._last_resources: NodeResources = NodeResources()

    @property
    def last_resources(self) -> NodeResources:
        return self._last_resources

    def set_callback(self, callback) -> None:
        """Callback que se llama cada vez que hay un reporte nuevo."""
        self._callback = callback

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("[resources] Monitor iniciado")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def snapshot(self) -> NodeResources:
        """Toma una instantánea de los recursos actuales."""
        resources = NodeResources()

        try:
            import psutil
            resources.cpu_percent = psutil.cpu_percent(interval=0.5)
            mem = psutil.virtual_memory()
            resources.ram_free_gb = round(mem.available / (1024 ** 3), 1)
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"[resources] Error psutil: {e}")

        # GPU detection
        try:
            resources.gpu_name, resources.gpu_vram_mb, resources.gpu_usage_percent = _detect_gpu()
        except Exception:
            pass

        # Ollama models
        try:
            resources.ollama_models = await _detect_ollama_models()
        except Exception:
            pass

        self._last_resources = resources
        return resources

    async def _monitor_loop(self) -> None:
        while self._running:
            try:
                resources = await self.snapshot()
                if self._callback:
                    await self._callback(resources.model_dump())
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.error(f"[resources] Monitor error: {e}")
            await asyncio.sleep(REPORT_INTERVAL)


def _detect_gpu() -> tuple[str | None, int, float]:
    """Detecta GPU. Retorna (nombre, vram_mb, usage_percent)."""
    system = platform.system()

    # macOS — Apple Silicon (MPS)
    if system == "Darwin":
        try:
            import subprocess
            result = subprocess.run(
                ["system_profiler", "SPDisplaysDataType"],
                capture_output=True, text=True, timeout=5,
            )
            if "Apple" in result.stdout:
                for line in result.stdout.split("\n"):
                    if "Chipset Model" in line:
                        name = line.split(":")[-1].strip()
                        return name, 0, 0.0  # MPS shares unified memory
        except Exception:
            pass

    # Linux/Windows — NVIDIA
    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,utilization.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(",")
            if len(parts) >= 3:
                return parts[0].strip(), int(parts[1].strip()), float(parts[2].strip())
    except Exception:
        pass

    return None, 0, 0.0


async def _detect_ollama_models() -> list[str]:
    """Detecta modelos cargados en Ollama local."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get("http://localhost:11434/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                return [m["name"] for m in data.get("models", [])]
    except Exception:
        pass
    return []
