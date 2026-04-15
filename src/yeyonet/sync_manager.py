"""
YeyoNet — SyncManager.
Sincroniza memorias entre Central y Satélites.
Sat→Central: memorias nuevas (según visibility level).
Central→Sat: LoRA weights y memorias compartidas.
Conflict resolution: newest wins (by timestamp).
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

import asyncpg

from .models import Permission, YeyoNetNode
from .protocol import MessageType, NetMessage

logger = logging.getLogger("yeyonet.sync")

# Batch size for sync operations
SYNC_BATCH_SIZE = 50
SYNC_INTERVAL = 300  # 5 minutes


class SyncManager:
    """
    Coordina la sincronización de memorias entre nodos.
    Central: recibe memorias de satélites, envía actualizaciones.
    """

    def __init__(self, pool: asyncpg.Pool, relay=None):
        self._pool = pool
        self._relay = relay
        self._running = False
        self._sync_task: asyncio.Task | None = None
        self._offline_queues: dict[str, list[dict]] = {}  # node_id → pending memories

    def set_relay(self, relay) -> None:
        self._relay = relay

    async def start(self) -> None:
        self._running = True
        self._sync_task = asyncio.create_task(self._periodic_sync())
        logger.info("[sync] SyncManager iniciado")

    async def stop(self) -> None:
        self._running = False
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass

    # ─── Receive memories from satellite ─────────────────────

    async def handle_memory_sync(self, msg: NetMessage, from_node_id: str) -> None:
        """
        Handler para MEMORY_SYNC desde un satélite.
        Recibe memorias y las almacena en el Central.
        """
        memories = msg.payload.get("memories", [])
        namespace = msg.payload.get("namespace", "")

        if not memories:
            await self._send_sync_ack(from_node_id, msg.msg_id, 0, [])
            return

        # Check satellite permissions
        node = await self._get_node(from_node_id)
        if not node:
            logger.warning(f"[sync] Nodo desconocido: {from_node_id[:8]}...")
            return

        has_memoria_perm = "memoria" in [
            p.value if hasattr(p, 'value') else p for p in node.permissions
        ]
        if node.visibility_level < 3 and not has_memoria_perm:
            logger.warning(f"[sync] Nodo {from_node_id[:8]}... sin permisos de memoria (vis={node.visibility_level})")
            await self._send_sync_ack(from_node_id, msg.msg_id, 0,
                                       ["Permission denied: requires visibility_level >= 3 or 'memoria' permission"])
            return

        synced = 0
        errors = []

        async with self._pool.acquire() as conn:
            for mem_data in memories:
                try:
                    result = await self._store_synced_memory(conn, mem_data, from_node_id)
                    if result:
                        synced += 1
                except Exception as e:
                    errors.append(f"Error storing memory: {str(e)[:100]}")

        logger.info(f"[sync] Recibidas {synced}/{len(memories)} memorias de {from_node_id[:8]}...")
        await self._send_sync_ack(from_node_id, msg.msg_id, synced, errors)

    async def _store_synced_memory(
        self, conn: asyncpg.Connection, mem_data: dict, from_node_id: str
    ) -> bool:
        """Almacena una memoria sincronizada. Deduplica por checksum."""
        content = mem_data.get("content", "")
        mem_type = mem_data.get("type", "fact")
        namespace = mem_data.get("namespace", "chat:usuario")
        checksum = mem_data.get("checksum", "")
        metadata = mem_data.get("metadata", {})
        source = f"sync:{from_node_id[:8]}"

        if not content:
            return False

        # Dedup: check if memory with same checksum exists
        if checksum:
            existing = await conn.fetchval(
                "SELECT id FROM flash_memories WHERE checksum = $1",
                checksum,
            )
            if existing:
                # Already exists — check if newer (conflict resolution)
                remote_ts = mem_data.get("updated_at") or mem_data.get("created_at")
                if remote_ts:
                    local_ts = await conn.fetchval(
                        "SELECT updated_at FROM flash_memories WHERE checksum = $1",
                        checksum,
                    )
                    if local_ts and isinstance(remote_ts, str):
                        remote_dt = datetime.fromisoformat(remote_ts)
                        if remote_dt.tzinfo is None:
                            remote_dt = remote_dt.replace(tzinfo=timezone.utc)
                        if local_ts.tzinfo is None:
                            local_ts = local_ts.replace(tzinfo=timezone.utc)
                        if remote_dt > local_ts:
                            # Remote is newer — update metadata
                            merged_meta = {**metadata, "synced_from": from_node_id}
                            await conn.execute(
                                "UPDATE flash_memories SET metadata = $1::jsonb WHERE checksum = $2",
                                json.dumps(merged_meta),
                                checksum,
                            )
                            return True
                return False  # Already exists and local is newer/equal

        # Store new memory
        metadata["synced_from"] = from_node_id
        metadata["synced_at"] = datetime.now(timezone.utc).isoformat()

        await conn.execute(
            """
            INSERT INTO flash_memories (content, type, namespace, metadata, source)
            VALUES ($1, $2, $3, $4::jsonb, $5)
            """,
            content,
            mem_type,
            namespace,
            json.dumps(metadata),
            source,
        )
        return True

    # ─── Send memories to satellite ──────────────────────────

    async def push_memories_to_satellite(
        self,
        node_id: str,
        namespaces: list[str] | None = None,
        since: datetime | None = None,
    ) -> int:
        """Envía memorias del Central a un satélite."""
        if not self._relay:
            return 0

        # Get node to check permissions
        node = await self._get_node(node_id)
        if not node:
            return 0

        # Build query for memories to share
        query = "SELECT id, content, type, namespace, checksum, metadata, source, created_at, updated_at FROM flash_memories WHERE 1=1"
        params = []
        idx = 1

        if namespaces:
            query += f" AND namespace = ANY(${idx}::text[])"
            params.append(namespaces)
            idx += 1

        if since:
            query += f" AND created_at > ${idx}"
            params.append(since)
            idx += 1

        # Don't send memories that were synced FROM this node
        query += f" AND (source IS NULL OR source NOT LIKE 'sync:' || ${idx})"
        params.append(node_id[:8])
        idx += 1

        query += f" ORDER BY created_at DESC LIMIT ${idx}"
        params.append(SYNC_BATCH_SIZE)

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        if not rows:
            return 0

        memories = []
        for row in rows:
            memories.append({
                "id": str(row["id"]),
                "content": row["content"],
                "type": row["type"],
                "namespace": row["namespace"],
                "checksum": row["checksum"],
                "metadata": row["metadata"] if isinstance(row["metadata"], dict) else json.loads(row["metadata"] or "{}"),
                "source": row["source"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
            })

        msg = NetMessage(
            type=MessageType.MEMORY_SYNC,
            from_node="central",
            to_node=node_id,
            payload={
                "memories": memories,
                "direction": "central_to_satellite",
                "count": len(memories),
            },
        )
        sent = await self._relay.send_to_node(node_id, msg)
        if sent:
            logger.info(f"[sync] Enviadas {len(memories)} memorias a {node_id[:8]}...")
        return len(memories) if sent else 0

    # ─── Offline queue ───────────────────────────────────────

    def queue_offline(self, node_id: str, memory_data: dict) -> None:
        """Encola una memoria para sincronizar cuando el nodo se reconecte."""
        if node_id not in self._offline_queues:
            self._offline_queues[node_id] = []
        self._offline_queues[node_id].append(memory_data)

    async def flush_offline_queue(self, node_id: str) -> int:
        """Procesa la cola offline de un nodo que acaba de reconectar."""
        queue = self._offline_queues.pop(node_id, [])
        if not queue:
            return 0

        logger.info(f"[sync] Flushing {len(queue)} memorias offline para {node_id[:8]}...")

        synced = 0
        async with self._pool.acquire() as conn:
            for mem_data in queue:
                try:
                    if await self._store_synced_memory(conn, mem_data, node_id):
                        synced += 1
                except Exception as e:
                    logger.error(f"[sync] Error flushing offline memory: {e}")
                    # Re-queue failed items
                    self.queue_offline(node_id, mem_data)

        logger.info(f"[sync] Flushed {synced}/{len(queue)} offline memories for {node_id[:8]}...")
        return synced

    def get_offline_queue_size(self, node_id: str | None = None) -> int | dict:
        """Tamaño de la cola offline."""
        if node_id:
            return len(self._offline_queues.get(node_id, []))
        return {nid: len(q) for nid, q in self._offline_queues.items()}

    # ─── Training corpus sharing ─────────────────────────────

    async def get_shared_training_corpus(
        self,
        min_score: float = 8.0,
        language: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """
        Obtiene corpus de entrenamiento aprobado para compartir.
        Solo memorias marcadas como training_approved.
        """
        async with self._pool.acquire() as conn:
            if language:
                rows = await conn.fetch(
                    """
                    SELECT fm.id, fm.content, fm.type, fm.namespace, fm.metadata
                    FROM flash_memories fm
                    JOIN memory_training_corpus mtc ON fm.id = mtc.memory_id
                    WHERE mtc.promoted = TRUE
                    AND (fm.metadata->>'score_critico')::float >= $1
                    AND fm.metadata->>'language' = $2
                    ORDER BY fm.created_at DESC
                    LIMIT $3
                    """,
                    min_score,
                    language,
                    limit,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT fm.id, fm.content, fm.type, fm.namespace, fm.metadata
                    FROM flash_memories fm
                    JOIN memory_training_corpus mtc ON fm.id = mtc.memory_id
                    WHERE mtc.promoted = TRUE
                    AND (fm.metadata->>'score_critico')::float >= $1
                    ORDER BY fm.created_at DESC
                    LIMIT $2
                    """,
                    min_score,
                    limit,
                )

        return [
            {
                "id": str(r["id"]),
                "content": r["content"],
                "type": r["type"],
                "namespace": r["namespace"],
                "metadata": r["metadata"] if isinstance(r["metadata"], dict) else json.loads(r["metadata"] or "{}"),
            }
            for r in rows
        ]

    async def share_training_corpus(self, node_id: str, language: str | None = None, min_score: float = 8.0) -> int:
        """Envía corpus de entrenamiento a un satélite."""
        corpus = await self.get_shared_training_corpus(min_score=min_score, language=language)
        if not corpus or not self._relay:
            return 0

        msg = NetMessage(
            type=MessageType.MEMORY_SYNC,
            from_node="central",
            to_node=node_id,
            payload={
                "type": "training_corpus",
                "corpus": corpus,
                "count": len(corpus),
                "min_score": min_score,
            },
        )
        sent = await self._relay.send_to_node(node_id, msg)
        if sent:
            logger.info(f"[sync] Training corpus ({len(corpus)} items) enviado a {node_id[:8]}...")
        return len(corpus) if sent else 0

    # ─── Sync stats ──────────────────────────────────────────

    async def get_sync_stats(self) -> dict:
        """Estadísticas de sincronización."""
        async with self._pool.acquire() as conn:
            synced_count = await conn.fetchval(
                "SELECT COUNT(*) FROM flash_memories WHERE source LIKE 'sync:%'"
            ) or 0
            total_memories = await conn.fetchval(
                "SELECT COUNT(*) FROM flash_memories"
            ) or 0

        offline_total = sum(len(q) for q in self._offline_queues.values())
        return {
            "total_memories": total_memories,
            "synced_memories": synced_count,
            "offline_queue_size": offline_total,
            "offline_queues": {nid: len(q) for nid, q in self._offline_queues.items()} if self._offline_queues else {},
        }

    # ─── Internal helpers ────────────────────────────────────

    async def _get_node(self, node_id: str) -> YeyoNetNode | None:
        from .identity import _row_to_node
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM yeyonet_nodes WHERE id = $1",
                uuid.UUID(node_id),
            )
        return _row_to_node(row) if row else None

    async def _send_sync_ack(self, node_id: str, reply_to: str, synced: int, errors: list) -> None:
        if self._relay:
            ack = NetMessage(
                type=MessageType.MEMORY_SYNC_ACK,
                from_node="central",
                to_node=node_id,
                reply_to=reply_to,
                payload={"synced": synced, "errors": errors},
            )
            await self._relay.send_to_node(node_id, ack)

    async def _periodic_sync(self) -> None:
        """Periódicamente comparte memorias con satélites conectados."""
        while self._running:
            await asyncio.sleep(SYNC_INTERVAL)
            try:
                if not self._relay:
                    continue
                connected = self._relay.get_connected_ids()
                for node_id in connected:
                    node = await self._get_node(node_id)
                    if node and node.visibility_level >= 3:
                        await self.push_memories_to_satellite(node_id)
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.error(f"[sync] Periodic sync error: {e}")
