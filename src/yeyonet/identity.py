"""
YeyoNet — Identidad del nodo.
Cada instancia de YeyoOS tiene un node_id UUID persistente.
"""
from __future__ import annotations

import logging
import uuid

import asyncpg

from .models import NodeRole, YeyoNetNode

logger = logging.getLogger("yeyonet.identity")


class NodeIdentity:
    """Gestiona la identidad de este nodo en la red YeyoNet."""

    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool
        self._node_id: str | None = None
        self._role: NodeRole = NodeRole.CENTRAL

    @property
    def node_id(self) -> str:
        if not self._node_id:
            raise RuntimeError("NodeIdentity no inicializado. Llama a initialize() primero.")
        return self._node_id

    @property
    def role(self) -> NodeRole:
        return self._role

    async def initialize(self, role: NodeRole = NodeRole.CENTRAL, name: str = "Central") -> str:
        """
        Inicializa o recupera la identidad de este nodo.
        Si ya existe un nodo Central en DB, lo reutiliza.
        Si no, crea uno nuevo.
        """
        async with self._pool.acquire() as conn:
            # Buscar nodo existente con este rol
            row = await conn.fetchrow(
                "SELECT id, name, role FROM yeyonet_nodes WHERE role = $1 LIMIT 1",
                role.value,
            )

            if row:
                self._node_id = str(row["id"])
                self._role = NodeRole(row["role"])
                logger.info(f"[yeyonet] Identidad recuperada: {row['name']} ({self._node_id[:8]}...)")
                return self._node_id

            # Crear nuevo nodo
            node_id = str(uuid.uuid4())
            auth_token = str(uuid.uuid4())

            await conn.execute(
                """
                INSERT INTO yeyonet_nodes (id, name, role, mode, status, auth_token, permissions, visibility_level)
                VALUES ($1, $2, $3, 'completo', 'online', $4, '["chat","grafos","memoria","control"]', 4)
                """,
                uuid.UUID(node_id),
                name,
                role.value,
                auth_token,
            )

            self._node_id = node_id
            self._role = role
            logger.info(f"[yeyonet] Nueva identidad creada: {name} ({node_id[:8]}...) rol={role.value}")
            return node_id

    async def get_node(self) -> YeyoNetNode | None:
        """Obtiene el nodo actual completo."""
        if not self._node_id:
            return None

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM yeyonet_nodes WHERE id = $1",
                uuid.UUID(self._node_id),
            )
            if not row:
                return None
            return _row_to_node(row)

    async def update_status(self, status: str) -> None:
        """Actualiza el status de este nodo."""
        if not self._node_id:
            return
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE yeyonet_nodes SET status = $1, last_seen_at = NOW() WHERE id = $2",
                status,
                uuid.UUID(self._node_id),
            )


def _row_to_node(row: asyncpg.Record) -> YeyoNetNode:
    """Convierte un row de DB a modelo YeyoNetNode."""
    import json
    perms = row["permissions"]
    if isinstance(perms, str):
        perms = json.loads(perms)
    resources = row["resources"]
    if isinstance(resources, str):
        resources = json.loads(resources)

    return YeyoNetNode(
        id=str(row["id"]),
        name=row["name"],
        role=row["role"],
        mode=row["mode"],
        status=row["status"],
        auth_token=row["auth_token"],
        permissions=perms,
        visibility_level=row["visibility_level"],
        resources=resources or {},
        ollama_host=row.get("ollama_host"),
        ip_address=row.get("ip_address"),
        last_seen_at=row.get("last_seen_at"),
        created_at=row["created_at"],
    )
