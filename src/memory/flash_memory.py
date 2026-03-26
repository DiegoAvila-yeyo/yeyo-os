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
from typing import Optional

import asyncpg

from .models import Memory

logger = logging.getLogger("yeyoos.memory")


class FlashMemory:
    """
    Implementación concreta de MemoriaProvider con asyncpg.
    Flash Memory es el sistema de memoria persistente de YeyoOS.
    Las memorias NUNCA se eliminan — solo se mueven entre tiers.
    """

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

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

        logger.info(f"Memoria almacenada: {row['id']} tipo={type} tier={row['tier']}")
        return self._row_to_memory(row)

    async def recall(self, query: str, limit: int = 5) -> list[Memory]:
        """
        Recupera memorias relevantes por acceso frecuente y reciente.
        Combina access_count y accessed_at para relevancia.
        """
        async with self.pool.acquire() as conn:
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
        """Obtiene una memoria por su ID. Actualiza accessed_at."""
        mid = memory_id if isinstance(memory_id, uuid.UUID) else uuid.UUID(memory_id)
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
        return self._row_to_memory(row)

    async def search_semantic(
        self,
        embedding: list[float],
        threshold: float = 0.5,
        limit: int = 5,
        sources: list[str] | None = None,
    ) -> list[Memory]:
        """
        Búsqueda semántica usando pgvector con cosine similarity.
        Solo retorna memorias cuya similitud >= threshold.
        sources: lista de fuentes a incluir (ej: ['chat_extraction']). None = todas.
        Fallback: retorna memorias recientes si pgvector no está disponible.
        """
        vector_str = "[" + ",".join(str(x) for x in embedding) + "]"
        try:
            async with self.pool.acquire() as conn:
                if sources:
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
        return self._row_to_memory(row)

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
        return self._row_to_memory(row)

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
