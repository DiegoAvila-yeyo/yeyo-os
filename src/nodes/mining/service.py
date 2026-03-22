"""
YeyoOS — Mining Node (ASIC Dashboard ONLY)
Micro-fase 5.15 — Capa 5: Órganos

██████████████████████████████████████████████████████
██  GPU NUNCA PARA MINERÍA — EXCLUSIVAMENTE PARA IA  ██
██████████████████████████████████████████████████████

Este nodo es SOLO un dashboard de monitoreo de ASICs.
NO controla minería. NO usa GPU. SOLO monitoreo.
"""

import uuid
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.nodes.base import NodeBase, PrivilegeLevel


@dataclass
class ASICDevice:
    """Dispositivo ASIC conectado."""
    id: str
    name: str
    model: str
    status: str = "offline"  # online | offline | error
    hashrate: float = 0.0  # TH/s
    temperature: int = 0  # °C
    power_watts: int = 0
    uptime_hours: float = 0.0
    last_seen: Optional[datetime] = None


@dataclass
class MiningStats:
    """Estadísticas de minería."""
    total_hashrate: float = 0.0  # TH/s
    estimated_daily_usd: float = 0.0
    estimated_monthly_usd: float = 0.0
    power_cost_daily_usd: float = 0.0
    devices_online: int = 0
    devices_total: int = 0


class MiningNode(NodeBase):
    """
    Nodo de Minería — dashboard ASIC ONLY.

    ⚠️  GPU NUNCA PARA MINERÍA ⚠️
    La GPU (GTX 1060 3GB) es exclusivamente para IA (Ollama, SD, LLaVA).
    Este nodo SOLO monitorea dispositivos ASIC conectados.
    NO tiene capacidad de minar, solo de observar.
    """

    GPU_MINING_BLOCKED = True
    _BLOCK_REASON = "GPU reservada exclusivamente para IA. Minería solo via ASIC."

    def __init__(self):
        super().__init__(
            name="Mining",
            version="1.0.0",
            privilege_level=PrivilegeLevel.USER,
            container_config={
                "memory_limit": "256m",
                "cpu_shares": 128,
                "gpu_required": False,  # NUNCA GPU
            },
        )
        self._devices: dict[str, ASICDevice] = {}
        self._power_cost_kwh: float = 0.10  # USD per kWh

    async def initialize(self) -> None:
        pass

    async def render_ui(self) -> dict:
        stats = self._calculate_stats()
        return {
            "component": "MiningNode",
            "props": {
                "devices": [
                    {"id": d.id, "name": d.name, "model": d.model,
                     "status": d.status, "hashrate": d.hashrate,
                     "temperature": d.temperature, "power_watts": d.power_watts}
                    for d in self._devices.values()
                ],
                "stats": {
                    "total_hashrate": stats.total_hashrate,
                    "estimated_daily_usd": stats.estimated_daily_usd,
                    "devices_online": stats.devices_online,
                    "devices_total": stats.devices_total,
                },
                "gpu_mining_blocked": True,
            },
        }

    async def process(self, input_data: dict) -> dict:
        action = input_data.get("action", "")

        if action == "gpu_mine":
            return {
                "error": self._BLOCK_REASON,
                "gpu_mining_blocked": True,
                "suggestion": "Conecta un ASIC para minería. La GPU es solo para IA.",
            }
        elif action == "add_device":
            return self._add_device(input_data)
        elif action == "remove_device":
            return self._remove_device(input_data.get("device_id", ""))
        elif action == "get_stats":
            return self._calculate_stats().__dict__
        elif action == "refresh":
            return await self._refresh_devices()
        else:
            return {"error": f"Acción desconocida: {action}"}

    async def cleanup(self) -> None:
        self._devices.clear()

    # ═══════════════════════════════════
    # GPU MINING BLOCK (redundant on purpose)
    # ═══════════════════════════════════

    async def request_gpu(self, vram_mb: int, priority: int = 5) -> bool:
        """OVERRIDE: Mining Node NUNCA puede solicitar GPU."""
        return False

    # ═══════════════════════════════════
    # MÉTODOS DE MONITOREO ASIC
    # ═══════════════════════════════════

    def _add_device(self, data: dict) -> dict:
        """Registra un dispositivo ASIC para monitoreo."""
        device = ASICDevice(
            id=f"asic-{uuid.uuid4().hex[:8]}",
            name=data.get("name", "ASIC Device"),
            model=data.get("model", "Unknown"),
            status="offline",
        )
        self._devices[device.id] = device
        return {"device_id": device.id, "name": device.name}

    def _remove_device(self, device_id: str) -> dict:
        if device_id not in self._devices:
            return {"error": "Dispositivo no encontrado"}
        del self._devices[device_id]
        return {"removed": device_id}

    def _calculate_stats(self) -> MiningStats:
        """Calcula estadísticas agregadas."""
        online_devices = [d for d in self._devices.values() if d.status == "online"]
        total_hashrate = sum(d.hashrate for d in online_devices)
        total_power = sum(d.power_watts for d in online_devices)

        estimated_daily = total_hashrate * 0.05
        power_cost_daily = (total_power * 24 / 1000) * self._power_cost_kwh

        return MiningStats(
            total_hashrate=total_hashrate,
            estimated_daily_usd=round(estimated_daily, 2),
            estimated_monthly_usd=round(estimated_daily * 30, 2),
            power_cost_daily_usd=round(power_cost_daily, 2),
            devices_online=len(online_devices),
            devices_total=len(self._devices),
        )

    async def _refresh_devices(self) -> dict:
        """Refresca estado de dispositivos (placeholder)."""
        return {
            "devices": len(self._devices),
            "refreshed": True,
        }
