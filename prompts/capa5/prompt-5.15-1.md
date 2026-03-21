## ═══════════════════════════════════════
## MICRO-FASE 5.15 — Mining Node
## Tipo: VSCODE | Prompts: 1 | Complejidad: Simple
## ═══════════════════════════════════════

### PROMPT 5.15-1 [VSCODE] — Dashboard de minería ASIC (GPU NUNCA para minería)

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 5.15 de Capa 5 (Órganos): crear el Mining Node como dashboard de monitoreo de dispositivos ASIC.

CONTEXTO:
- Micro-fases 5.0-5.14 completadas
- REGLA ABSOLUTA: GPU NUNCA se usa para minería — exclusivamente para IA
- Mining Node es SOLO un dashboard de monitoreo de ASICs conectados
- Muestra: dispositivos ASIC, hashrate, ganancias estimadas
- NO controla minería directamente (solo monitoreo)
- Frontend: Next.js 14 + Tailwind + Zustand
- Hardware: GTX 1060 3GB VRAM (SOLO PARA IA, NO MINERÍA)

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear estructura:
   mkdir -p src/nodes/mining
   mkdir -p tests/unit/nodes/mining
   mkdir -p frontend/src/components/nodes/mining

2. Crear archivo src/nodes/mining/__init__.py:

   Ruta: ~/yeyo-os/src/nodes/mining/__init__.py
   Contenido:
   from .service import MiningNode

3. Crear archivo src/nodes/mining/service.py:

   Ruta: ~/yeyo-os/src/nodes/mining/service.py
   Contenido:

   """
   YeyoOS — Mining Node (ASIC Dashboard ONLY)
   Micro-fase 5.15 — Capa 5: Órganos

   ██████████████████████████████████████████████████████
   ██  GPU NUNCA PARA MINERÍA — EXCLUSIVAMENTE PARA IA  ██
   ██████████████████████████████████████████████████████

   Este nodo es SOLO un dashboard de monitoreo de ASICs.
   NO controla minería. NO usa GPU. SOLO monitoreo.
   """

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

       # Bloqueo explícito de minería GPU
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
           """Inicializa dashboard de monitoreo."""
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
                   "gpu_mining_blocked": True,  # Siempre True
               },
           }

       async def process(self, input_data: dict) -> dict:
           action = input_data.get("action", "")

           if action == "gpu_mine":
               # BLOQUEO ABSOLUTO
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
           return False  # Siempre False para mining

       # ═══════════════════════════════════
       # MÉTODOS DE MONITOREO ASIC
       # ═══════════════════════════════════

       def _add_device(self, data: dict) -> dict:
           """Registra un dispositivo ASIC para monitoreo."""
           import uuid
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

           # Estimación simple (Bitcoin ~$0.05/TH/s/day, variable)
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

4. Crear archivo frontend/src/components/nodes/mining/MiningNode.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/nodes/mining/MiningNode.tsx
   Contenido:

   /**
    * YeyoOS — Mining Node Frontend
    * Micro-fase 5.15 — Capa 5: Órganos
    *
    * ⚠️ GPU NUNCA PARA MINERÍA — EXCLUSIVAMENTE PARA IA ⚠️
    */

   'use client';

   import React from 'react';
   import NodeWrapper from '../NodeWrapper';

   interface ASICDevice {
     id: string;
     name: string;
     model: string;
     status: string;
     hashrate: number;
     temperature: number;
     power_watts: number;
   }

   interface MiningNodeProps {
     nodeId: string;
     devices: ASICDevice[];
     stats: {
       total_hashrate: number;
       estimated_daily_usd: number;
       devices_online: number;
       devices_total: number;
     };
     onAddDevice: () => void;
     onRefresh: () => void;
     onClose: (nodeId: string) => void;
   }

   export default function MiningNode({
     nodeId, devices, stats, onAddDevice, onRefresh, onClose,
   }: MiningNodeProps) {
     return (
       <NodeWrapper nodeId={nodeId} title="Mining (ASIC)" icon="⛏️" onClose={onClose}>
         <div className="flex flex-col h-full gap-3">
           {/* GPU Warning */}
           <div className="px-3 py-2 bg-red-900/30 border border-red-700 rounded-lg">
             <p className="text-xs text-red-400 font-medium">
               ⚠️ GPU exclusiva para IA — Minería solo via ASIC
             </p>
           </div>

           {/* Stats */}
           <div className="grid grid-cols-2 gap-2">
             <div className="px-3 py-2 bg-gray-800 rounded-lg">
               <p className="text-[10px] text-gray-500">Hashrate Total</p>
               <p className="text-sm font-bold text-green-400">{stats.total_hashrate} TH/s</p>
             </div>
             <div className="px-3 py-2 bg-gray-800 rounded-lg">
               <p className="text-[10px] text-gray-500">Estimado Diario</p>
               <p className="text-sm font-bold text-yellow-400">${stats.estimated_daily_usd}</p>
             </div>
             <div className="px-3 py-2 bg-gray-800 rounded-lg">
               <p className="text-[10px] text-gray-500">Dispositivos</p>
               <p className="text-sm font-bold text-blue-400">
                 {stats.devices_online}/{stats.devices_total}
               </p>
             </div>
           </div>

           {/* Devices */}
           <div className="flex-1 overflow-y-auto space-y-2">
             {devices.length === 0 ? (
               <p className="text-xs text-gray-500 text-center py-4">
                 No hay dispositivos ASIC conectados
               </p>
             ) : (
               devices.map((device) => (
                 <div key={device.id} className="px-3 py-2 bg-gray-800 rounded-lg
                                                  border border-gray-700">
                   <div className="flex justify-between">
                     <span className="text-xs text-white font-medium">{device.name}</span>
                     <span className={`text-xs ${
                       device.status === 'online' ? 'text-green-400' : 'text-red-400'
                     }`}>
                       {device.status}
                     </span>
                   </div>
                   <div className="flex gap-4 mt-1 text-[10px] text-gray-500">
                     <span>{device.hashrate} TH/s</span>
                     <span>{device.temperature}°C</span>
                     <span>{device.power_watts}W</span>
                   </div>
                 </div>
               ))
             )}
           </div>

           {/* Controls */}
           <div className="flex gap-2 shrink-0">
             <button onClick={onAddDevice}
               className="flex-1 px-3 py-1 text-xs bg-gray-700 text-gray-300
                          rounded hover:bg-gray-600">
               + Añadir ASIC
             </button>
             <button onClick={onRefresh}
               className="px-3 py-1 text-xs bg-blue-600 text-white rounded">
               🔄
             </button>
           </div>
         </div>
       </NodeWrapper>
     );
   }

5. Crear tests/unit/nodes/mining/__init__.py (vacío):

   Ruta: ~/yeyo-os/tests/unit/nodes/mining/__init__.py
   Contenido: (archivo vacío)

6. Crear archivo tests/unit/nodes/mining/test_mining_node.py:

   Ruta: ~/yeyo-os/tests/unit/nodes/mining/test_mining_node.py
   Contenido:

   """Tests para Mining Node — Micro-fase 5.15"""

   import pytest
   from src.nodes.mining.service import MiningNode


   class TestGPUMiningBlocked:
       """Tests CRÍTICOS: GPU NUNCA para minería."""

       def test_gpu_mining_blocked_flag(self):
           """GPU mining debe estar bloqueado SIEMPRE."""
           assert MiningNode.GPU_MINING_BLOCKED is True

       @pytest.mark.asyncio
       async def test_gpu_request_always_denied(self):
           """Mining Node NUNCA puede solicitar GPU."""
           node = MiningNode()
           result = await node.request_gpu(vram_mb=1024, priority=1)
           assert result is False

       @pytest.mark.asyncio
       async def test_gpu_mine_action_blocked(self):
           """Intentar minar con GPU retorna error."""
           node = MiningNode()
           result = await node.process({"action": "gpu_mine"})
           assert "error" in result
           assert result["gpu_mining_blocked"] is True

       def test_container_config_no_gpu(self):
           """Container config debe tener gpu_required=False."""
           node = MiningNode()
           assert node.container_config.get("gpu_required") is False


   class TestASICMonitoring:

       @pytest.mark.asyncio
       async def test_add_device(self):
           node = MiningNode()
           result = node._add_device({"name": "Antminer S19", "model": "S19 Pro"})
           assert "device_id" in result
           assert len(node._devices) == 1

       @pytest.mark.asyncio
       async def test_remove_device(self):
           node = MiningNode()
           result = node._add_device({"name": "ASIC 1"})
           remove_result = node._remove_device(result["device_id"])
           assert "removed" in remove_result
           assert len(node._devices) == 0

       def test_calculate_stats(self):
           node = MiningNode()
           node._add_device({"name": "ASIC 1"})
           stats = node._calculate_stats()
           assert stats.devices_total == 1
           assert stats.devices_online == 0  # Default is offline

       @pytest.mark.asyncio
       async def test_render_ui_shows_gpu_blocked(self):
           node = MiningNode()
           ui = await node.render_ui()
           assert ui["props"]["gpu_mining_blocked"] is True

7. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/nodes/mining/test_mining_node.py -v

VERIFICAR:
- [ ] GPU_MINING_BLOCKED es SIEMPRE True
- [ ] request_gpu() SIEMPRE retorna False para Mining Node
- [ ] Acción "gpu_mine" retorna error con mensaje claro
- [ ] Container config tiene gpu_required=False
- [ ] Dashboard muestra dispositivos ASIC
- [ ] Stats se calculan correctamente
- [ ] Frontend muestra warning de GPU exclusiva para IA
- [ ] TODOS los tests pasan

SI FALLA:
- Import error: verificar __init__.py

NO HACER:
- NUNCA permitir minería con GPU
- NUNCA remover el bloqueo de GPU mining
- No implementar control de minería (solo monitoreo)
- No conectar con pools de minería

GATE: Mining Node es dashboard ASIC only, GPU mining bloqueado en TODAS las formas posibles, monitoreo de dispositivos funciona, todos los tests pasan.
```
