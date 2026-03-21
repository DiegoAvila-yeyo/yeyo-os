## ═══════════════════════════════════════
## MICRO-FASE 5.20 — Node Health Monitor
## Tipo: VSCODE | Prompts: 1 | Complejidad: Simple
## ═══════════════════════════════════════

### PROMPT 5.20-1 [VSCODE] — Monitor de salud de nodos con auto-restart

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 5.20 de Capa 5 (Órganos): crear el Node Health Monitor que monitorea la salud de todos los nodos activos.

CONTEXTO:
- Micro-fases 5.0-5.19 completadas: todos los nodos, registry, API, MiniChat
- Health Monitor: chequeo periódico de todos los nodos activos
- Auto-restart de nodos crasheados
- Máximo 3 intentos de restart, luego marcar como failed
- Reporta a Guardian (Capa 6, futuro)
- Backend: Python 3.11 + FastAPI

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/nodes/health_monitor.py:

   Ruta: ~/yeyo-os/src/nodes/health_monitor.py
   Contenido:

   """
   YeyoOS — Node Health Monitor
   Micro-fase 5.20 — Capa 5: Órganos

   Monitorea salud de todos los nodos activos.
   Auto-restart de nodos crasheados (máximo 3 intentos).
   """

   import asyncio
   from datetime import datetime, timezone
   from typing import Optional
   from dataclasses import dataclass, field

   from src.nodes.base import NodeBase, NodeStatus


   MAX_RESTART_ATTEMPTS = 3
   HEALTH_CHECK_INTERVAL = 30  # segundos


   @dataclass
   class NodeHealthStatus:
       """Estado de salud de un nodo."""
       node_id: str
       node_name: str
       status: str
       restart_count: int = 0
       last_check: Optional[datetime] = None
       last_error: Optional[str] = None
       is_healthy: bool = True


   class NodeHealthMonitor:
       """
       Monitor de salud de nodos activos.
       Chequeo periódico, auto-restart, máximo 3 intentos.
       """

       def __init__(self):
           self._health_records: dict[str, NodeHealthStatus] = {}
           self._monitor_task: Optional[asyncio.Task] = None
           self._running: bool = False

       def register_node(self, node: NodeBase) -> None:
           """Registra un nodo para monitoreo."""
           self._health_records[node.id] = NodeHealthStatus(
               node_id=node.id,
               node_name=node.name,
               status=node.status.value,
               last_check=datetime.now(timezone.utc),
           )

       def unregister_node(self, node_id: str) -> None:
           """Desregistra un nodo del monitoreo."""
           self._health_records.pop(node_id, None)

       async def check_node(self, node: NodeBase) -> NodeHealthStatus:
           """Verifica la salud de un nodo específico."""
           record = self._health_records.get(node.id)
           if record is None:
               self.register_node(node)
               record = self._health_records[node.id]

           record.last_check = datetime.now(timezone.utc)
           record.status = node.status.value

           if node.status == NodeStatus.ERROR:
               record.is_healthy = False
               record.last_error = "Node in ERROR state"

               if record.restart_count < MAX_RESTART_ATTEMPTS:
                   success = await self._attempt_restart(node, record)
                   if success:
                       record.is_healthy = True
                       record.last_error = None
               else:
                   record.status = "failed"
                   record.is_healthy = False
                   record.last_error = (
                       f"Max restart attempts ({MAX_RESTART_ATTEMPTS}) reached"
                   )
           elif node.status == NodeStatus.CLOSED:
               record.is_healthy = False
               record.status = "closed"
           else:
               record.is_healthy = True
               record.last_error = None

           return record

       async def _attempt_restart(
           self, node: NodeBase, record: NodeHealthStatus
       ) -> bool:
           """Intenta reiniciar un nodo crasheado."""
           record.restart_count += 1
           try:
               await node.close()
               await node.open()
               record.status = node.status.value
               return node.status == NodeStatus.READY
           except Exception as e:
               record.last_error = f"Restart attempt {record.restart_count} failed: {str(e)}"
               return False

       async def check_all(self, active_nodes: dict[str, NodeBase]) -> list[NodeHealthStatus]:
           """Verifica salud de todos los nodos activos."""
           results = []
           for node_id, node in active_nodes.items():
               status = await self.check_node(node)
               results.append(status)
           return results

       def get_health_report(self) -> dict:
           """Genera reporte de salud de todos los nodos."""
           total = len(self._health_records)
           healthy = sum(1 for r in self._health_records.values() if r.is_healthy)
           unhealthy = total - healthy

           return {
               "total_nodes": total,
               "healthy": healthy,
               "unhealthy": unhealthy,
               "nodes": [
                   {
                       "node_id": r.node_id,
                       "node_name": r.node_name,
                       "status": r.status,
                       "is_healthy": r.is_healthy,
                       "restart_count": r.restart_count,
                       "last_error": r.last_error,
                       "last_check": r.last_check.isoformat() if r.last_check else None,
                   }
                   for r in self._health_records.values()
               ],
           }

       async def start_monitoring(self, active_nodes_getter) -> None:
           """Inicia monitoreo periódico."""
           self._running = True
           while self._running:
               nodes = active_nodes_getter()
               await self.check_all(nodes)
               await asyncio.sleep(HEALTH_CHECK_INTERVAL)

       def stop_monitoring(self) -> None:
           """Detiene monitoreo."""
           self._running = False

2. Actualizar src/nodes/__init__.py:

   Ruta: ~/yeyo-os/src/nodes/__init__.py
   Contenido:
   from .base import NodeBase, NodeStatus, PrivilegeLevel
   from .registry import NodeRegistry, NodeNotFoundError
   from .health_monitor import NodeHealthMonitor

3. Crear archivo tests/unit/nodes/test_health_monitor.py:

   Ruta: ~/yeyo-os/tests/unit/nodes/test_health_monitor.py
   Contenido:

   """Tests para Node Health Monitor — Micro-fase 5.20"""

   import pytest
   from unittest.mock import AsyncMock, MagicMock
   from src.nodes.base import NodeBase, NodeStatus, PrivilegeLevel
   from src.nodes.health_monitor import (
       NodeHealthMonitor, MAX_RESTART_ATTEMPTS, NodeHealthStatus,
   )


   class FakeNode(NodeBase):
       async def initialize(self): pass
       async def render_ui(self) -> dict: return {}
       async def process(self, input_data: dict) -> dict: return {}
       async def cleanup(self): pass

       def __init__(self, status=NodeStatus.READY):
           super().__init__(name="Fake", version="1.0")
           self.status = status


   class TestHealthMonitorCheck:

       @pytest.mark.asyncio
       async def test_healthy_node_reports_ok(self):
           monitor = NodeHealthMonitor()
           node = FakeNode(status=NodeStatus.READY)
           result = await monitor.check_node(node)
           assert result.is_healthy is True
           assert result.status == "ready"

       @pytest.mark.asyncio
       async def test_crashed_node_detected(self):
           monitor = NodeHealthMonitor()
           node = FakeNode(status=NodeStatus.ERROR)
           node.close = AsyncMock()
           node.open = AsyncMock()
           result = await monitor.check_node(node)
           # Should attempt restart
           assert result.restart_count >= 1


   class TestHealthMonitorRestart:

       @pytest.mark.asyncio
       async def test_auto_restart_works(self):
           monitor = NodeHealthMonitor()
           node = FakeNode(status=NodeStatus.ERROR)
           node.close = AsyncMock()
           node.open = AsyncMock(side_effect=lambda: setattr(node, 'status', NodeStatus.READY))

           result = await monitor.check_node(node)
           assert result.restart_count == 1
           assert result.is_healthy is True

       @pytest.mark.asyncio
       async def test_max_restart_attempts_respected(self):
           monitor = NodeHealthMonitor()
           node = FakeNode(status=NodeStatus.ERROR)
           node.close = AsyncMock()
           node.open = AsyncMock()  # Doesn't fix the error

           # Simulate max attempts
           record = NodeHealthStatus(
               node_id=node.id, node_name=node.name,
               status="error", restart_count=MAX_RESTART_ATTEMPTS,
           )
           monitor._health_records[node.id] = record

           result = await monitor.check_node(node)
           assert result.status == "failed"
           assert result.is_healthy is False
           assert result.restart_count == MAX_RESTART_ATTEMPTS

       def test_max_restart_is_3(self):
           assert MAX_RESTART_ATTEMPTS == 3


   class TestHealthMonitorReport:

       @pytest.mark.asyncio
       async def test_health_report(self):
           monitor = NodeHealthMonitor()
           node1 = FakeNode(status=NodeStatus.READY)
           node2 = FakeNode(status=NodeStatus.READY)

           await monitor.check_node(node1)
           await monitor.check_node(node2)

           report = monitor.get_health_report()
           assert report["total_nodes"] == 2
           assert report["healthy"] == 2
           assert report["unhealthy"] == 0

       def test_register_and_unregister(self):
           monitor = NodeHealthMonitor()
           node = FakeNode()
           monitor.register_node(node)
           assert node.id in monitor._health_records

           monitor.unregister_node(node.id)
           assert node.id not in monitor._health_records

4. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/nodes/test_health_monitor.py -v

VERIFICAR:
- [ ] Nodo healthy reporta ok
- [ ] Nodo crasheado detectado
- [ ] Auto-restart funciona
- [ ] Máximo 3 intentos de restart respetado
- [ ] Nodo marcado como "failed" después de 3 intentos
- [ ] Health report muestra totales correctos
- [ ] Register/unregister funciona
- [ ] TODOS los tests pasan

SI FALLA:
- Import error: verificar __init__.py
- AsyncMock: verificar que close/open se mockean

NO HACER:
- No implementar Guardian (eso es Capa 6)
- No aumentar MAX_RESTART_ATTEMPTS más allá de 3
- No reiniciar nodos que el usuario cerró voluntariamente

GATE: Health Monitor detecta crasheos, auto-restart con máximo 3 intentos, report de salud, register/unregister, todos los tests pasan.
```
