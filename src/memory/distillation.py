"""
YeyoOS — ColdDistillation (Destilación de Memorias COLD)
Micro-fase 2.11 — Capa 2: Cerebro

Compacta memorias similares en un hecho canónico usando LLM.
Reglas:
- Solo opera sobre memorias tier COLD (las archivadas)
- Agrupa por namespace y similitud semántica
- Crea una memoria canónica con campo derived_from=[ids originales]
- Las originales NO se borran (regla sagrada), solo reciben tag "derived"
- Se ejecuta on-demand o programado cada N horas
"""

import json
import logging
from datetime import datetime
from typing import Optional

from .flash_memory import FlashMemory
from .models import Memory, MemoryTier

logger = logging.getLogger("yeyoos.distillation")

# Máximo de memorias a compactar en una pasada
MAX_MEMORIES_PER_PASS = 50
# Máximo de memorias por grupo antes de destilar
MAX_PER_GROUP = 5
# Similitud mínima para considerar que dos memorias son "del mismo tema"
SIMILARITY_THRESHOLD = 0.75


class ColdDistillation:
    """
    Destilador de memorias COLD: agrupa, compacta vía LLM y registra
    la fuente como campo derived_from en la memoria canónica.
    """

    def __init__(self, flash_memory: FlashMemory, ia_provider):
        self.memory = flash_memory
        self.ia = ia_provider

    async def distill_all(self) -> dict:
        """
        Ejecuta una pasada completa de destilación sobre memorias COLD
        que aún no han sido derivadas. Retorna estadísticas.
        """
        stats = {"groups_found": 0, "distilled": 0, "skipped": 0, "errors": 0}

        async with self.memory.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, content, type, tier, access_count, embedding,
                       checksum, metadata, source, namespace, created_at, accessed_at
                FROM flash_memories
                WHERE tier = 'COLD'
                  AND (metadata->>'derived') IS NULL
                  AND embedding IS NOT NULL
                  AND (metadata->>'invalid') IS NULL
                ORDER BY created_at DESC
                LIMIT $1
                """,
                MAX_MEMORIES_PER_PASS,
            )

        if not rows:
            logger.info("ColdDistillation: no hay memorias COLD para destilar")
            return stats

        # Agrupar por namespace
        groups: dict[str, list[dict]] = {}
        for row in rows:
            ns = row["namespace"] or "sin_namespace"
            if ns not in groups:
                groups[ns] = []
            if len(groups[ns]) < MAX_PER_GROUP:
                groups[ns].append(row)

        stats["groups_found"] = len(groups)

        for ns, mems in groups.items():
            if len(mems) < 2:
                stats["skipped"] += 1
                continue

            try:
                memory_ids = [str(m["id"]) for m in mems]
                contents = [m["content"] for m in mems]
                emb = mems[0]["embedding"]  # usar embedding del primero como representativo

                # Pedir al LLM que compacte
                compacted = await self._compact_via_llm(contents, ns)
                if not compacted:
                    stats["skipped"] += 1
                    continue

                # Guardar la memoria canónica
                canonical = await self._store_canonical(
                    conn,
                    content=compacted,
                    namespace=ns,
                    source_ids=memory_ids,
                    embedding=emb,
                )

                # Marcar originales como derivadas (no se borran)
                await conn.execute(
                    """
                    UPDATE flash_memories
                    SET metadata = metadata || jsonb_build_object(
                        'derived', true,
                        'derived_into', $1::text,
                        'derived_at', NOW()::text
                    ),
                        updated_at = NOW()
                    WHERE id = ANY($2::uuid[])
                    """,
                    canonical["id"],
                    memory_ids,
                )

                stats["distilled"] += 1
                logger.info(
                    "Destilación: %d memorias → 1 canónica (%s) en %s",
                    len(memory_ids), canonical["id"][:8], ns,
                )

            except Exception as e:
                logger.error("Error destilando grupo en %s: %s", ns, e)
                stats["errors"] += 1

        logger.info(
            "ColdDistillation: %d grupos, %d destiladas, %d saltadas, %d errores",
            stats["groups_found"], stats["distilled"],
            stats["skipped"], stats["errors"],
        )
        return stats

    async def distill_namespace(self, namespace: str) -> dict:
        """
        Destila solo un namespace específico.
        Útil para ejecución dirigida después de una sesión larga.
        """
        stats = {"distilled": 0, "skipped": 0, "errors": 0}

        async with self.memory.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, content, type, tier, access_count, embedding,
                       checksum, metadata, source, namespace, created_at, accessed_at
                FROM flash_memories
                WHERE tier = 'COLD'
                  AND namespace = $1
                  AND (metadata->>'derived') IS NULL
                  AND embedding IS NOT NULL
                  AND (metadata->>'invalid') IS NULL
                ORDER BY created_at DESC
                LIMIT $2
                """,
                namespace,
                MAX_PER_GROUP,
            )

        if len(rows) < 2:
            return stats

        try:
            memory_ids = [str(r["id"]) for r in rows]
            contents = [r["content"] for r in rows]
            emb = rows[0]["embedding"]

            compacted = await self._compact_via_llm(contents, namespace)
            if not compacted:
                stats["skipped"] = 1
                return stats

            async with self.memory.pool.acquire() as conn:
                canonical = await self._store_canonical(
                    conn, compacted, namespace, memory_ids, emb,
                )
                await conn.execute(
                    """
                    UPDATE flash_memories
                    SET metadata = metadata || jsonb_build_object(
                        'derived', true,
                        'derived_into', $1::text,
                        'derived_at', NOW()::text
                    ),
                        updated_at = NOW()
                    WHERE id = ANY($2::uuid[])
                    """,
                    canonical["id"],
                    memory_ids,
                )

            stats["distilled"] = 1

        except Exception as e:
            logger.error("Error destilando %s: %s", namespace, e)
            stats["errors"] = 1

        return stats

    async def _compact_via_llm(self, contents: list[str], namespace: str) -> Optional[str]:
        """
        Usa el LLM para compactar N contenidos similares en 1 hecho canónico.
        Retorna el texto compactado o None si falla.
        """
        from src.ia.interfaces import IAMessage

        system_prompt = (
            "Eres un destilador de conocimiento. Tu tarea es compactar "
            "múltiples entradas similares en UN solo hecho canónico. "
            "Conserva los datos clave, elimina redundancias, y mantén "
            "el contexto del namespace. No añadas información nueva.\n\n"
            f"Namespace: {namespace}"
        )

        contents_text = "\n---\n".join(
            f"[{i+1}] {c}" for i, c in enumerate(contents)
        )

        user_prompt = (
            "Compacta estas entradas similares en UN solo párrafo canónico:\n\n"
            f"{contents_text}\n\n"
            "Responde SOLO con el texto compactado, sin explicaciones."
        )

        messages = [
            IAMessage(role="system", content=system_prompt),
            IAMessage(role="user", content=user_prompt),
        ]

        response = await self.ia.chat(
            messages=messages,
            temperature=0.3,  # baja temperatura = más determinista
        )

        if not response or not response.content:
            logger.warning("LLM no retornó contenido para destilación")
            return None

        return response.content.strip()

    async def _store_canonical(
        self, conn, content: str, namespace: str,
        source_ids: list[str], embedding,
    ) -> dict:
        """
        Guarda la memoria canónica con el campo derived_from apuntando
        a las originales y embedding como representativo del grupo.
        """
        import uuid
        import asyncio

        metadata = {
            "derived_from": source_ids,
            "derived_count": len(source_ids),
            "distilled_at": datetime.utcnow().isoformat(),
            "namespace": namespace,
            "source": "cold_distillation",
        }

        vector_str = "[" + ",".join(str(x) for x in embedding) + "]"

        row = await conn.fetchrow(
            """
            INSERT INTO flash_memories
                (content, type, tier, namespace, source, metadata, embedding, importance, tags)
            VALUES ($1, 'fact', 'WARM', $2, 'cold_distillation', $3::jsonb, $4::vector, 0.7, $5)
            RETURNING id, created_at
            """,
            content,
            namespace,
            json.dumps(metadata),
            vector_str,
            ["derived", "canonical", namespace.replace(":", "_")],
        )

        return {"id": str(row["id"]), "created_at": str(row["created_at"])}
