"""
YeyoOS — FlashMemory (Adaptador Hexagonal para MemoriaProvider)
Micro-fase 2.1 — Capa 2: Cerebro

Implementación concreta del sistema de memoria persistente.
REGLA SAGRADA: Las memorias NUNCA se borran.
No existe método delete(). No existirá jamás.
"""

import json
import uuid
import logging
from typing import Optional, TYPE_CHECKING

import asyncpg

from .models import Memory
from .pipeline_events import pipeline_buffer

if TYPE_CHECKING:
    from .cache import MemoryCache

logger = logging.getLogger("yeyoos.memory")


class FlashMemory:
    """
    Implementación concreta de MemoriaProvider con asyncpg.
    Flash Memory es el sistema de memoria persistente de YeyoOS.
    Las memorias NUNCA se eliminan — solo se mueven entre tiers.

    Arquitectura de 3 capas:
      🔴 HOT  → Redis (<1ms)      — inyectado vía self.cache
      🟡 WARM → PostgreSQL (10ms) — memorias activas
      🔵 COLD → PostgreSQL (50ms) — memorias archivadas
    """

    # Umbral de accesos para auto-promover a HOT durante recall
    _HOT_AUTO_PROMOTE_THRESHOLD = 5

    def __init__(self, pool: asyncpg.Pool, cache: Optional["MemoryCache"] = None):
        self.pool = pool
        self.cache = cache  # capa HOT — opcional, degrada grácilmente sin Redis
        self._on_store_callbacks: list = []  # Cloud sync hooks

    def set_cache(self, cache: "MemoryCache") -> None:
        """Inyecta el cache Redis después de la construcción."""
        self.cache = cache

    def on_store(self, callback) -> None:
        """Registra un callback async que se ejecuta tras cada store(). Para cloud sync."""
        self._on_store_callbacks.append(callback)

    @classmethod
    async def create(cls, database_url: str) -> "FlashMemory":
        """Factory method para crear FlashMemory con connection pool."""
        pool = await asyncpg.create_pool(
            database_url,
            min_size=2,
            max_size=10,
        )
        return cls(pool)

    async def store(
        self,
        content: str,
        type: str,
        metadata: Optional[dict] = None,
        embedding: Optional[list[float]] = None,
        source: str = "user",
        namespace: str = "chat:usuario",
    ) -> Memory:
        """
        Almacena una nueva memoria en Flash Memory.
        El checksum SHA-256 se genera automáticamente por trigger.
        """
        if metadata is None:
            metadata = {}

        async with self.pool.acquire() as conn:
            if embedding:
                # Format as pgvector literal: '[0.1,0.2,...]'
                vector_str = "[" + ",".join(str(x) for x in embedding) + "]"
                row = await conn.fetchrow(
                    """
                    INSERT INTO flash_memories (content, type, metadata, embedding, source, namespace)
                    VALUES ($1, $2, $3, $4::vector, $5, $6)
                    RETURNING id, content, type, tier, checksum, access_count,
                              metadata, source, namespace, created_at, accessed_at, updated_at
                    """,
                    content,
                    type,
                    json.dumps(metadata),
                    vector_str,
                    source,
                    namespace,
                )
            else:
                row = await conn.fetchrow(
                    """
                    INSERT INTO flash_memories (content, type, metadata, source, namespace)
                    VALUES ($1, $2, $3, $4, $5)
                    RETURNING id, content, type, tier, checksum, access_count,
                              metadata, source, namespace, created_at, accessed_at, updated_at
                    """,
                    content,
                    type,
                    json.dumps(metadata),
                    source,
                    namespace,
                )

            await conn.execute(
                """
                INSERT INTO memory_audit_log (memory_id, action, details)
                VALUES ($1, 'CREATE', $2)
                """,
                row["id"],
                json.dumps({"type": type, "source": source}),
            )

        # Emitir pipeline event
        _pipeline_source = source if source in ["chat", "code_dojo", "image", "automation"] else "automation"
        _is_skill = type in ["skill", "fact"]
        pipeline_buffer.emit(
            pipeline_id=pipeline_buffer.new_pipeline(_pipeline_source),
            step="STORED" if _is_skill else "RECEIVED",
            status="ok",
            detail=f"{type} en {namespace}",
            metadata={
                "memory_id": str(row["id"]),
                "type": type,
                "namespace": namespace,
                "source": source,
                "tier": row["tier"],
            },
        )

        logger.info(f"Memoria almacenada: {row['id']} tipo={type} tier={row['tier']}")
        memory = self._row_to_memory(row)

        # Notify cloud sync hooks (fire-and-forget)
        for cb in self._on_store_callbacks:
            try:
                import asyncio
                asyncio.create_task(cb(self._row_to_dict(row)))
            except Exception:
                pass

        return memory

    async def recall(self, query: str, limit: int = 5) -> list[Memory]:
        """
        Recupera memorias relevantes. Estrategia 3 capas:
          1. HOT desde Redis (sub-ms)
          2. WARM/COLD desde PostgreSQL para completar el límite
        """
        _pipe_id = pipeline_buffer.new_pipeline("automation")
        pipeline_buffer.emit(
            pipeline_id=_pipe_id,
            step="CONTEXT_LOAD",
            status="ok",
            detail=f"Buscando: {query[:80]}",
            metadata={"query": query[:120]},
        )

        results: list[Memory] = []

        # 1. Intentar HOT desde Redis
        if self.cache:
            hot_ids = await self.cache.get_hot_memories(limit=limit)
            if hot_ids:
                cached = await self.cache.get_multiple(hot_ids)
                results.extend(cached)
                logger.debug(f"recall: {len(cached)} hits desde Redis HOT")

        # 2. Completar desde PostgreSQL si faltan
        remaining = limit - len(results)
        if remaining > 0:
            exclude_ids = [m.id for m in results]
            async with self.pool.acquire() as conn:
                if exclude_ids:
                    rows = await conn.fetch(
                        """
                        SELECT id, content, type, tier, checksum, access_count,
                               metadata, source, namespace, created_at, accessed_at, updated_at
                        FROM flash_memories
                        WHERE tier != 'COLD'
                          AND (metadata->>'invalid') IS NULL
                          AND id != ALL($2::uuid[])
                        ORDER BY access_count DESC, accessed_at DESC
                        LIMIT $1
                        """,
                        remaining,
                        [uuid.UUID(eid) for eid in exclude_ids],
                    )
                else:
                    rows = await conn.fetch(
                        """
                        SELECT id, content, type, tier, checksum, access_count,
                               metadata, source, namespace, created_at, accessed_at, updated_at
                        FROM flash_memories
                        WHERE tier != 'COLD'
                          AND (metadata->>'invalid') IS NULL
                        ORDER BY access_count DESC, accessed_at DESC
                        LIMIT $1
                        """,
                        remaining,
                    )
                for row in rows:
                    await conn.execute(
                        "UPDATE flash_memories SET accessed_at = NOW(), access_count = access_count + 1 WHERE id = $1",
                        row["id"],
                    )
                pg_memories = [self._row_to_memory(row) for row in rows]

                # Auto-promover a HOT si superan el umbral
                if self.cache:
                    for mem in pg_memories:
                        if mem.access_count >= self._HOT_AUTO_PROMOTE_THRESHOLD and mem.tier != "HOT":
                            await self.cache.set(mem)

                results.extend(pg_memories)

        return results[:limit]

    async def recall_by_type(self, type: str, limit: int = 10) -> list[Memory]:
        """Recupera memorias filtradas por tipo."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, content, type, tier, checksum, access_count,
                       metadata, source, namespace, created_at, accessed_at, updated_at
                FROM flash_memories
                WHERE type = $1
                ORDER BY accessed_at DESC
                LIMIT $2
                """,
                type,
                limit,
            )
        return [self._row_to_memory(row) for row in rows]

    async def get_by_id(self, memory_id: str) -> Optional[Memory]:
        """Obtiene una memoria por su ID. Chequea Redis HOT primero, luego PostgreSQL."""
        mid = memory_id if isinstance(memory_id, uuid.UUID) else uuid.UUID(memory_id)

        # 1. Intentar desde cache HOT (Redis)
        if self.cache:
            cached = await self.cache.get(str(mid))
            if cached:
                logger.debug(f"Cache HIT get_by_id: {mid}")
                return cached

        # 2. Fallback a PostgreSQL
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE flash_memories
                SET accessed_at = NOW(), access_count = access_count + 1
                WHERE id = $1
                RETURNING id, content, type, tier, checksum, access_count,
                          metadata, source, namespace, created_at, accessed_at, updated_at
                """,
                mid,
            )
        if row is None:
            return None
        memory = self._row_to_memory(row)

        # 3. Si es HOT, cachear en Redis para la próxima consulta
        if memory.tier == "HOT" and self.cache:
            await self.cache.set(memory)

        return memory

    async def search_semantic(
        self,
        embedding: list[float],
        threshold: float = 0.5,
        limit: int = 5,
        namespaces: list[str] | None = None,
        sources: list[str] | None = None,  # deprecated: usar namespaces
    ) -> list[Memory]:
        """
        Búsqueda semántica usando pgvector con cosine similarity.
        Solo retorna memorias cuya similitud >= threshold.
        namespaces: lista de namespaces a incluir (ej: ['chat:usuario', 'codigo:usuario']). None = todos.
        sources: deprecated, ignorado si namespaces está presente.
        Fallback: retorna memorias recientes si pgvector no está disponible.
        """
        vector_str = "[" + ",".join(str(x) for x in embedding) + "]"
        try:
            async with self.pool.acquire() as conn:
                if namespaces:
                    rows = await conn.fetch(
                        """
                        SELECT id, content, type, tier, checksum, access_count,
                               metadata, source, namespace, created_at, accessed_at, updated_at,
                               1 - (embedding <=> $1::vector) AS similarity
                        FROM flash_memories
                        WHERE embedding IS NOT NULL
                          AND (metadata->>'invalid') IS NULL
                          AND namespace = ANY($4::text[])
                          AND 1 - (embedding <=> $1::vector) >= $2
                        ORDER BY embedding <=> $1::vector
                        LIMIT $3
                        """,
                        vector_str,
                        threshold,
                        limit,
                        namespaces,
                    )
                elif sources:
                    rows = await conn.fetch(
                        """
                        SELECT id, content, type, tier, checksum, access_count,
                               metadata, source, namespace, created_at, accessed_at, updated_at,
                               1 - (embedding <=> $1::vector) AS similarity
                        FROM flash_memories
                        WHERE embedding IS NOT NULL
                          AND (metadata->>'invalid') IS NULL
                          AND source = ANY($4::text[])
                          AND 1 - (embedding <=> $1::vector) >= $2
                        ORDER BY embedding <=> $1::vector
                        LIMIT $3
                        """,
                        vector_str,
                        threshold,
                        limit,
                        sources,
                    )
                else:
                    rows = await conn.fetch(
                        """
                        SELECT id, content, type, tier, checksum, access_count,
                               metadata, source, namespace, created_at, accessed_at, updated_at,
                               1 - (embedding <=> $1::vector) AS similarity
                        FROM flash_memories
                        WHERE embedding IS NOT NULL
                          AND (metadata->>'invalid') IS NULL
                          AND 1 - (embedding <=> $1::vector) >= $2
                        ORDER BY embedding <=> $1::vector
                        LIMIT $3
                        """,
                        vector_str,
                        threshold,
                        limit,
                    )
                for row in rows:
                    await conn.execute(
                        """
                        UPDATE flash_memories
                        SET accessed_at = NOW(), access_count = access_count + 1
                        WHERE id = $1
                        """,
                        row["id"],
                    )
            return [self._row_to_memory(row) for row in rows]
        except Exception as e:
            logger.warning(f"pgvector no disponible, usando fallback: {e}")
            return await self.recall("", limit=limit)

    async def promote_tier(self, memory_id: str) -> Memory:
        """
        Promueve una memoria al siguiente tier: COLD→WARM→HOT.
        HOT no se puede promover más.
        """
        mid = memory_id if isinstance(memory_id, uuid.UUID) else uuid.UUID(memory_id)

        async with self.pool.acquire() as conn:
            current = await conn.fetchrow(
                "SELECT tier FROM flash_memories WHERE id = $1", mid
            )
            if current is None:
                raise ValueError(f"Memoria no encontrada: {memory_id}")

            new_tier = {"COLD": "WARM", "WARM": "HOT", "HOT": "HOT"}[current["tier"]]

            row = await conn.fetchrow(
                """
                UPDATE flash_memories
                SET tier = $1, updated_at = NOW()
                WHERE id = $2
                RETURNING id, content, type, tier, checksum, access_count,
                          metadata, source, namespace, created_at, accessed_at, updated_at
                """,
                new_tier,
                mid,
            )

            await conn.execute(
                """
                INSERT INTO memory_audit_log (memory_id, action, details)
                VALUES ($1, 'PROMOTE', $2)
                """,
                mid,
                json.dumps({"from": current["tier"], "to": new_tier}),
            )

        logger.info(f"Memoria {memory_id} promovida: {current['tier']}→{new_tier}")
        memory = self._row_to_memory(row)

        # Sincronizar con Redis: HOT entra al cache
        if new_tier == "HOT" and self.cache:
            await self.cache.set(memory)
        return memory

    async def demote_tier(self, memory_id: str) -> Memory:
        """
        Degrada una memoria al tier inferior: HOT→WARM→COLD.
        COLD no se puede degradar más.
        """
        mid = memory_id if isinstance(memory_id, uuid.UUID) else uuid.UUID(memory_id)

        async with self.pool.acquire() as conn:
            current = await conn.fetchrow(
                "SELECT tier FROM flash_memories WHERE id = $1", mid
            )
            if current is None:
                raise ValueError(f"Memoria no encontrada: {memory_id}")

            new_tier = {"HOT": "WARM", "WARM": "COLD", "COLD": "COLD"}[current["tier"]]

            row = await conn.fetchrow(
                """
                UPDATE flash_memories
                SET tier = $1, updated_at = NOW()
                WHERE id = $2
                RETURNING id, content, type, tier, checksum, access_count,
                          metadata, source, namespace, created_at, accessed_at, updated_at
                """,
                new_tier,
                mid,
            )

            await conn.execute(
                """
                INSERT INTO memory_audit_log (memory_id, action, details)
                VALUES ($1, 'DEMOTE', $2)
                """,
                mid,
                json.dumps({"from": current["tier"], "to": new_tier}),
            )

        logger.info(f"Memoria {memory_id} degradada: {current['tier']}→{new_tier}")
        memory = self._row_to_memory(row)

        # Sincronizar con Redis: si salió de HOT, invalidar cache
        if current["tier"] == "HOT" and self.cache:
            await self.cache.invalidate(str(mid))
        return memory

    async def get_stats(self) -> dict:
        """Estadísticas del sistema de memoria."""
        async with self.pool.acquire() as conn:
            total = await conn.fetchval("SELECT COUNT(*) FROM flash_memories")
            tier_counts = await conn.fetch(
                "SELECT tier, COUNT(*) as count FROM flash_memories GROUP BY tier"
            )
            type_counts = await conn.fetch(
                "SELECT type, COUNT(*) as count FROM flash_memories GROUP BY type"
            )
            association_count = await conn.fetchval(
                "SELECT COUNT(*) FROM memory_associations"
            )

        return {
            "total_memories": total,
            "by_tier": {row["tier"]: row["count"] for row in tier_counts},
            "by_type": {row["type"]: row["count"] for row in type_counts},
            "total_associations": association_count,
        }

    async def health_check(self) -> bool:
        """Verifica que Flash Memory está operativo."""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                return result == 1
        except Exception:
            return False

    async def close(self):
        """Cierra el connection pool."""
        await self.pool.close()

    def _row_to_memory(self, row: asyncpg.Record) -> Memory:
        """Convierte un registro de asyncpg a modelo Memory."""
        metadata = row["metadata"]
        if isinstance(metadata, str):
            metadata = json.loads(metadata)

        return Memory(
            id=str(row["id"]),
            content=row["content"],
            type=row["type"],
            tier=row["tier"],
            checksum=row["checksum"],
            access_count=row["access_count"],
            metadata=metadata if metadata else {},
            source=row["source"],
            namespace=row.get("namespace", "chat:usuario"),
            created_at=row["created_at"],
            accessed_at=row["accessed_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _row_to_dict(row: asyncpg.Record) -> dict:
        """Convierte un registro de asyncpg a dict para cloud sync."""
        metadata = row["metadata"]
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        return {
            "id": str(row["id"]),
            "content": row["content"],
            "type": row["type"],
            "tier": row["tier"],
            "checksum": row["checksum"],
            "access_count": row["access_count"],
            "metadata": metadata if metadata else {},
            "source": row["source"],
            "namespace": row.get("namespace", "general"),
            "created_at": row["created_at"],
            "accessed_at": row["accessed_at"],
            "updated_at": row["updated_at"],
        }
