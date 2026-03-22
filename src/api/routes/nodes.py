"""
YeyoOS — Node API Endpoints
Micro-fase 5.17 — Capa 5: Órganos

REST API para gestión de nodos del sistema.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from src.nodes.registry import NodeRegistry, NodeNotFoundError
from src.nodes.base import NodeBase


router = APIRouter(prefix="/api/v1/nodes", tags=["nodes"])

# Nodos activos en memoria
_active_nodes: dict[str, NodeBase] = {}


class OpenNodeRequest(BaseModel):
    config: Optional[dict] = None


class ProcessNodeRequest(BaseModel):
    data: dict


@router.get("/")
async def list_node_types() -> dict:
    types = NodeRegistry.list_types()
    return {
        "types": [
            {"type": t, **NodeRegistry.get_info(t)}
            for t in types
        ],
        "count": len(types),
    }


@router.get("/active")
async def list_active_nodes() -> dict:
    nodes_info = []
    for node_id, node in _active_nodes.items():
        status = await node.get_status()
        nodes_info.append(status)
    return {"nodes": nodes_info, "count": len(nodes_info)}


@router.post("/{node_type}/open")
async def open_node(node_type: str, request: OpenNodeRequest = OpenNodeRequest()) -> dict:
    try:
        node = NodeRegistry.create(node_type)
    except NodeNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    try:
        await node.open()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error inicializando nodo: {e}")

    _active_nodes[node.id] = node

    return {
        "node_id": node.id,
        "type": node_type,
        "status": node.status.value,
    }


@router.delete("/{node_id}/close")
async def close_node(node_id: str) -> dict:
    if node_id not in _active_nodes:
        raise HTTPException(status_code=404, detail=f"Nodo '{node_id}' no encontrado")

    node = _active_nodes[node_id]
    try:
        await node.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cerrando nodo: {e}")

    del _active_nodes[node_id]
    return {"node_id": node_id, "status": "closed"}


@router.get("/{node_id}/status")
async def get_node_status(node_id: str) -> dict:
    if node_id not in _active_nodes:
        raise HTTPException(status_code=404, detail=f"Nodo '{node_id}' no encontrado")
    node = _active_nodes[node_id]
    return await node.get_status()


@router.post("/{node_id}/process")
async def process_node_data(node_id: str, request: ProcessNodeRequest) -> dict:
    if node_id not in _active_nodes:
        raise HTTPException(status_code=404, detail=f"Nodo '{node_id}' no encontrado")

    node = _active_nodes[node_id]
    try:
        result = await node.process(request.data)
        return {"node_id": node_id, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando: {e}")


@router.get("/{node_id}/ui")
async def get_node_ui(node_id: str) -> dict:
    if node_id not in _active_nodes:
        raise HTTPException(status_code=404, detail=f"Nodo '{node_id}' no encontrado")
    node = _active_nodes[node_id]
    return await node.render_ui()
