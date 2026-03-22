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
        self._health_records[node.id] = NodeHealthStatus(
            node_id=node.id,
            node_name=node.name,
            status=node.status.value,
            last_check=datetime.now(timezone.utc),
        )

    def unregister_node(self, node_id: str) -> None:
        self._health_records.pop(node_id, None)

    async def check_node(self, node: NodeBase) -> NodeHealthStatus:
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
        results = []
        for node_id, node in active_nodes.items():
            status = await self.check_node(node)
            results.append(status)
        return results

    def get_health_report(self) -> dict:
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
        self._running = True
        while self._running:
            nodes = active_nodes_getter()
            await self.check_all(nodes)
            await asyncio.sleep(HEALTH_CHECK_INTERVAL)

    def stop_monitoring(self) -> None:
        self._running = False
