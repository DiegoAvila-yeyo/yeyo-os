"""
YeyoOS — Automation Node (Pipeline Visual)
Micro-fase 5.10 — Capa 5: Órganos

Constructor visual de pipelines con React Flow.
Usa Pipeline Engine de Capa 4.7.
"""

import uuid
from typing import Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.nodes.base import NodeBase, PrivilegeLevel


@dataclass
class VisualNode:
    """Nodo visual en el canvas de React Flow."""
    id: str
    type: str  # "input" | "process" | "output"
    label: str
    node_type: str  # tipo de nodo YeyoOS (chat, image, video, code, etc.)
    config: dict = field(default_factory=dict)
    position: dict = field(default_factory=lambda: {"x": 0, "y": 0})


@dataclass
class VisualEdge:
    """Conexión entre nodos visuales."""
    id: str
    source: str
    target: str
    label: str = ""


class AutomationNode(NodeBase):
    """
    Nodo de Automatización — órgano de workflows de YeyoOS.
    Constructor visual de pipelines con React Flow.
    """

    def __init__(self):
        super().__init__(
            name="Automation",
            version="1.0.0",
            privilege_level=PrivilegeLevel.USER,
            container_config={"memory_limit": "512m", "cpu_shares": 512},
        )
        self._visual_nodes: dict[str, VisualNode] = {}
        self._visual_edges: dict[str, VisualEdge] = {}
        self._saved_pipelines: dict[str, dict] = {}

    async def initialize(self) -> None:
        pass

    async def render_ui(self) -> dict:
        return {
            "component": "AutomationNode",
            "props": {
                "nodes": [
                    {"id": n.id, "type": n.type, "label": n.label,
                     "nodeType": n.node_type, "position": n.position}
                    for n in self._visual_nodes.values()
                ],
                "edges": [
                    {"id": e.id, "source": e.source, "target": e.target,
                     "label": e.label}
                    for e in self._visual_edges.values()
                ],
                "savedPipelines": list(self._saved_pipelines.keys()),
            },
        }

    async def process(self, input_data: dict) -> dict:
        action = input_data.get("action", "")

        if action == "add_node":
            return self._add_visual_node(input_data)
        elif action == "add_edge":
            return self._add_visual_edge(input_data)
        elif action == "remove_node":
            return self._remove_visual_node(input_data.get("node_id", ""))
        elif action == "remove_edge":
            return self._remove_visual_edge(input_data.get("edge_id", ""))
        elif action == "validate":
            return await self._validate_pipeline()
        elif action == "execute":
            return await self._execute_pipeline(input_data.get("input_data"))
        elif action == "save":
            return self._save_pipeline(input_data.get("name", ""))
        else:
            return {"error": f"Acción desconocida: {action}"}

    async def cleanup(self) -> None:
        self._visual_nodes.clear()
        self._visual_edges.clear()

    # ═══════════════════════════════════
    # MÉTODOS DEL CANVAS VISUAL
    # ═══════════════════════════════════

    def _add_visual_node(self, data: dict) -> dict:
        node = VisualNode(
            id=f"vnode-{uuid.uuid4().hex[:8]}",
            type=data.get("type", "process"),
            label=data.get("label", "Nuevo paso"),
            node_type=data.get("node_type", "generic"),
            config=data.get("config", {}),
            position=data.get("position", {"x": 100, "y": 100}),
        )
        self._visual_nodes[node.id] = node
        return {"node_id": node.id, "label": node.label}

    def _add_visual_edge(self, data: dict) -> dict:
        source = data.get("source", "")
        target = data.get("target", "")

        if source not in self._visual_nodes or target not in self._visual_nodes:
            return {"error": "Nodo origen o destino no existe"}

        if source == target:
            return {"error": "No se puede conectar un nodo consigo mismo"}

        edge = VisualEdge(
            id=f"vedge-{uuid.uuid4().hex[:8]}",
            source=source,
            target=target,
            label=data.get("label", ""),
        )
        self._visual_edges[edge.id] = edge
        return {"edge_id": edge.id, "source": source, "target": target}

    def _remove_visual_node(self, node_id: str) -> dict:
        if node_id not in self._visual_nodes:
            return {"error": "Nodo no encontrado"}
        del self._visual_nodes[node_id]
        edges_to_remove = [
            eid for eid, e in self._visual_edges.items()
            if e.source == node_id or e.target == node_id
        ]
        for eid in edges_to_remove:
            del self._visual_edges[eid]
        return {"removed": node_id, "edges_removed": len(edges_to_remove)}

    def _remove_visual_edge(self, edge_id: str) -> dict:
        if edge_id not in self._visual_edges:
            return {"error": "Edge no encontrado"}
        del self._visual_edges[edge_id]
        return {"removed": edge_id}

    async def _validate_pipeline(self) -> dict:
        """Valida el pipeline visual — detección de ciclos (DAG)."""
        if not self._visual_nodes:
            return {"valid": False, "error": "Pipeline vacío"}

        # Build adjacency list and detect cycles via DFS
        adj: dict[str, list[str]] = {nid: [] for nid in self._visual_nodes}
        for edge in self._visual_edges.values():
            adj[edge.source].append(edge.target)

        WHITE, GRAY, BLACK = 0, 1, 2
        color = {nid: WHITE for nid in self._visual_nodes}

        def has_cycle(node: str) -> bool:
            color[node] = GRAY
            for neighbor in adj[node]:
                if color[neighbor] == GRAY:
                    return True
                if color[neighbor] == WHITE and has_cycle(neighbor):
                    return True
            color[node] = BLACK
            return False

        for nid in self._visual_nodes:
            if color[nid] == WHITE:
                if has_cycle(nid):
                    return {"valid": False, "error": "Pipeline contiene ciclos"}

        return {
            "valid": True,
            "nodes": len(self._visual_nodes),
            "edges": len(self._visual_edges),
        }

    async def _execute_pipeline(self, input_data: Optional[dict] = None) -> dict:
        """Ejecuta el pipeline visual. Consulta memorias previas para contexto."""
        validation = await self._validate_pipeline()
        if not validation.get("valid"):
            return {"error": f"Pipeline inválido: {validation.get('error')}"}

        # Consultar memorias de automatizaciones previas
        if self._memory_service:
            try:
                labels = [n.label for n in self._visual_nodes.values()]
                query = " ".join(labels)
                context = await self._memory_service.get_automation_context(query, limit=3)
                if context:
                    logger.debug(f"Contexto de memoria para pipeline: {context[:100]}")
            except Exception:
                pass

        # Build execution order via topological sort
        in_degree: dict[str, int] = {nid: 0 for nid in self._visual_nodes}
        adj: dict[str, list[str]] = {nid: [] for nid in self._visual_nodes}
        for edge in self._visual_edges.values():
            adj[edge.source].append(edge.target)
            in_degree[edge.target] += 1

        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        execution_order = []
        while queue:
            nid = queue.pop(0)
            execution_order.append(nid)
            for neighbor in adj[nid]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        execution_labels = [
            self._visual_nodes[nid].label for nid in execution_order
        ]

        # Guardar pipeline ejecutado en memoria
        if self._memory_service and execution_labels:
            try:
                workflow = " → ".join(execution_labels)
                await self._memory_service.store_result(
                    content=f"Pipeline ejecutado: {workflow}",
                    namespace="automatizacion:usuario",
                    memory_type="skill",
                    source="automation_execution",
                    metadata={"steps": execution_labels,
                              "steps_count": len(execution_labels)},
                )
            except Exception:
                pass

        return {
            "status": "completed",
            "execution_order": execution_labels,
            "steps_executed": len(execution_order),
        }

    def _save_pipeline(self, name: str) -> dict:
        if not name.strip():
            return {"error": "Nombre requerido"}
        self._saved_pipelines[name] = {
            "nodes": [
                {"id": n.id, "type": n.type, "label": n.label,
                 "node_type": n.node_type, "position": n.position}
                for n in self._visual_nodes.values()
            ],
            "edges": [
                {"id": e.id, "source": e.source, "target": e.target}
                for e in self._visual_edges.values()
            ],
        }
        return {"saved": name}
