"""
YeyoNet — SatelliteManager.
CRUD de satélites registrados, permisos, estados.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

import asyncpg

from .identity import _row_to_node
from .models import (
    NodeResources,
    NodeRole,
    NodeStatus,
    Permission,
    SatelliteMode,
    YeyoNetNode,
)

logger = logging.getLogger("yeyonet.satellites")

# Thresholds para determinar status por heartbeat
ONLINE_THRESHOLD = timedelta(minutes=5)
IDLE_THRESHOLD = timedelta(minutes=60)


class SatelliteManager:
    """Gestiona satélites registrados en la red."""

    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def register_satellite(
        self,
        name: str,
        mode: SatelliteMode,
        permissions: list[Permission],
        visibility_level: int = 1,
        ollama_host: str | None = None,
        ip_address: str | None = None,
    ) -> YeyoNetNode:
        """Registra un nuevo satélite y genera su auth_token."""
        node_id = str(uuid.uuid4())
        auth_token = str(uuid.uuid4())
        perms_json = json.dumps([p.value if isinstance(p, Permission) else p for p in permissions])

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO yeyonet_nodes
                    (id, name, role, mode, status, auth_token, permissions, visibility_level,
                     ollama_host, ip_address, last_seen_at)
                VALUES ($1, $2, 'satellite', $3, 'online', $4, $5::jsonb, $6, $7, $8, NOW())
                RETURNING *
                """,
                uuid.UUID(node_id),
                name,
                mode.value,
                auth_token,
                perms_json,
                visibility_level,
                ollama_host,
                ip_address,
            )

        node = _row_to_node(row)
        logger.info(f"[yeyonet] Satélite registrado: {name} ({node_id[:8]}...) modo={mode.value}")
        return node

    async def get_satellite(self, node_id: str) -> YeyoNetNode | None:
        """Obtiene un satélite por ID."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM yeyonet_nodes WHERE id = $1",
                uuid.UUID(node_id),
            )
        return _row_to_node(row) if row else None

    async def authenticate(self, auth_token: str) -> YeyoNetNode | None:
        """Autentica un nodo por su token. Retorna el nodo si válido."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM yeyonet_nodes WHERE auth_token = $1",
                auth_token,
            )
        if not row:
            return None
        return _row_to_node(row)

    async def list_satellites(self, include_offline: bool = True) -> list[YeyoNetNode]:
        """Lista todos los satélites (excluye el Central)."""
        async with self._pool.acquire() as conn:
            if include_offline:
                rows = await conn.fetch(
                    "SELECT * FROM yeyonet_nodes WHERE role = 'satellite' ORDER BY name"
                )
            else:
                rows = await conn.fetch(
                    "SELECT * FROM yeyonet_nodes WHERE role = 'satellite' AND status != 'offline' ORDER BY name"
                )
        return [_row_to_node(r) for r in rows]

    async def update_satellite(
        self,
        node_id: str,
        name: str | None = None,
        permissions: list[Permission] | None = None,
        visibility_level: int | None = None,
    ) -> YeyoNetNode | None:
        """Actualiza permisos/nombre de un satélite."""
        sets = []
        params = []
        idx = 1

        if name is not None:
            sets.append(f"name = ${idx}")
            params.append(name)
            idx += 1

        if permissions is not None:
            perms_json = json.dumps([p.value if isinstance(p, Permission) else p for p in permissions])
            sets.append(f"permissions = ${idx}::jsonb")
            params.append(perms_json)
            idx += 1

        if visibility_level is not None:
            sets.append(f"visibility_level = ${idx}")
            params.append(visibility_level)
            idx += 1

        if not sets:
            return await self.get_satellite(node_id)

        params.append(uuid.UUID(node_id))
        query = f"UPDATE yeyonet_nodes SET {', '.join(sets)} WHERE id = ${idx} RETURNING *"

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)

        if not row:
            return None

        logger.info(f"[yeyonet] Satélite {node_id[:8]}... actualizado: {sets}")
        return _row_to_node(row)

    async def remove_satellite(self, node_id: str) -> bool:
        """Desconecta y elimina un satélite."""
        node_uuid = uuid.UUID(node_id)
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "UPDATE yeyonet_invitations SET used_by_node_id = NULL WHERE used_by_node_id = $1",
                    node_uuid,
                )
                await conn.execute(
                    "UPDATE yeyonet_jobs SET requested_by = NULL WHERE requested_by = $1",
                    node_uuid,
                )
                await conn.execute(
                    """
                    UPDATE yeyonet_jobs
                    SET
                        assigned_to = NULL,
                        status = CASE WHEN status IN ('assigned', 'running') THEN 'queued' ELSE status END,
                        progress = CASE WHEN status IN ('assigned', 'running') THEN 0 ELSE progress END,
                        progress_detail = CASE
                            WHEN status IN ('assigned', 'running')
                                THEN 'Satellite removed; job returned to queue'
                            ELSE progress_detail
                        END
                    WHERE assigned_to = $1
                    """,
                    node_uuid,
                )
                await conn.execute(
                    "UPDATE yeyonet_job_results SET node_id = NULL WHERE node_id = $1",
                    node_uuid,
                )
                result = await conn.execute(
                    "DELETE FROM yeyonet_nodes WHERE id = $1 AND role = 'satellite'",
                    node_uuid,
                )
        deleted = result.split()[-1] != "0"
        if deleted:
            logger.info(f"[yeyonet] Satélite eliminado: {node_id[:8]}...")
        return deleted

    async def update_heartbeat(self, node_id: str, resources: NodeResources | None = None) -> None:
        """Actualiza timestamp de heartbeat y recursos."""
        async with self._pool.acquire() as conn:
            if resources:
                res_json = json.dumps(resources.model_dump())
                await conn.execute(
                    """
                    UPDATE yeyonet_nodes
                    SET last_seen_at = NOW(), status = 'online', resources = $1::jsonb
                    WHERE id = $2
                    """,
                    res_json,
                    uuid.UUID(node_id),
                )
            else:
                await conn.execute(
                    "UPDATE yeyonet_nodes SET last_seen_at = NOW(), status = 'online' WHERE id = $1",
                    uuid.UUID(node_id),
                )

    async def refresh_statuses(self) -> int:
        """
        Actualiza estados de todos los nodos según su last_seen_at.
        Llamar periódicamente (ej: cada 60s).
        Returns: número de nodos actualizados.
        """
        now = datetime.now(timezone.utc)
        idle_cutoff = now - ONLINE_THRESHOLD
        offline_cutoff = now - IDLE_THRESHOLD

        async with self._pool.acquire() as conn:
            # Online → Idle
            r1 = await conn.execute(
                """
                UPDATE yeyonet_nodes SET status = 'idle'
                WHERE status = 'online' AND last_seen_at < $1 AND role = 'satellite'
                """,
                idle_cutoff,
            )
            # Idle → Offline
            r2 = await conn.execute(
                """
                UPDATE yeyonet_nodes SET status = 'offline'
                WHERE status IN ('online', 'idle') AND last_seen_at < $1 AND role = 'satellite'
                """,
                offline_cutoff,
            )

        count = int(r1.split()[-1]) + int(r2.split()[-1])
        if count > 0:
            logger.info(f"[yeyonet] Status refresh: {count} nodos actualizados")
        return count

    async def get_network_stats(self) -> dict:
        """Estadísticas agregadas de la red."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT status, COUNT(*) as count FROM yeyonet_nodes WHERE role = 'satellite' GROUP BY status"
            )
            total_resources = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) as total_nodes,
                    COUNT(*) FILTER (WHERE status = 'online') as online_nodes
                FROM yeyonet_nodes WHERE role = 'satellite'
                """
            )

        status_counts = {row["status"]: row["count"] for row in rows}
        return {
            "total_satellites": total_resources["total_nodes"] if total_resources else 0,
            "online": status_counts.get("online", 0),
            "idle": status_counts.get("idle", 0),
            "offline": status_counts.get("offline", 0),
        }
