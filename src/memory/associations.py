"""
YeyoOS — AssociationEngine (Motor de Asociaciones)
Micro-fase 2.10 — Capa 2: Cerebro

Crea y gestiona conexiones entre memorias relacionadas,
formando una red neuronal-like de conocimiento.
Las asociaciones se basan en similitud semántica.
"""

import json
import logging
from typing import Optional

import asyncpg

from .models import Memory
from .flash_memory import FlashMemory
from src.ia.embeddings import EmbeddingService

logger = logging.getLogger("yeyoos.associations")

# Umbral mínimo de similitud para crear asociación automática
AUTO_ASSOCIATION_THRESHOLD = 0.6
# Máximo de asociaciones automáticas por memoria nueva
MAX_AUTO_ASSOCIATIONS = 5


class AssociationEngine:
    """
    Motor de asociaciones entre memorias.
    Crea una red de conexiones basada en similitud semántica
    para enriquecer el contexto de las respuestas.
    """

    def __init__(
        self,
        flash_memory: FlashMemory,
        embeddings: EmbeddingService,
    ):
        self.memory = flash_memory
        self.embeddings = embeddings

    async def create_association(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        strength: float = 1.0,
    ) -> dict:
        """
        Crea una asociación entre dos memorias.
        strength debe estar entre 0.0 y 1.0.
        """
        import uuid as uuid_mod

        if source_id == target_id:
            raise ValueError("No se puede crear asociación consigo mismo")
        if not (0.0 <= strength <= 1.0):
            raise ValueError("strength debe estar entre 0.0 y 1.0")

        src_id = uuid_mod.UUID(source_id) if isinstance(source_id, str) else source_id
        tgt_id = uuid_mod.UUID(target_id) if isinstance(target_id, str) else target_id

        async with self.memory.pool.acquire() as conn:
            try:
                row = await conn.fetchrow(
                    """
                    INSERT INTO memory_associations
                        (source_id, target_id, relation_type, strength)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (source_id, target_id, relation_type)
                    DO UPDATE SET strength = GREATEST(
                        memory_associations.strength, EXCLUDED.strength
                    )
                    RETURNING id, source_id, target_id, relation_type, strength, created_at
                    """,
                    src_id,
                    tgt_id,
                    relation_type,
                    strength,
                )

                # Registrar en audit log
                await conn.execute(
                    """
                    INSERT INTO memory_audit_log (memory_id, action, details)
                    VALUES ($1, 'ASSOCIATE', $2)
                    """,
                    src_id,
                    json.dumps({
                        "target_id": str(tgt_id),
                        "relation_type": relation_type,
                        "strength": strength,
                    }),
                )

            except asyncpg.CheckViolationError as e:
                raise ValueError(f"Constraint violation: {e}")

        logger.info(
            f"Asociación creada: {source_id} --[{relation_type}:{strength}]--> {target_id}"
        )
        return {
            "id": str(row["id"]),
            "source_id": str(row["source_id"]),
            "target_id": str(row["target_id"]),
            "relation_type": row["relation_type"],
            "strength": row["strength"],
        }

    async def find_related(
        self,
        memory_id: str,
        limit: int = 5,
    ) -> list[Memory]:
        """
        Encuentra memorias relacionadas a una memoria dada.
        Busca en ambas direcciones de la asociación.
        """
        import uuid as uuid_mod
        mid = uuid_mod.UUID(memory_id) if isinstance(memory_id, str) else memory_id

        async with self.memory.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT DISTINCT m.id, m.content, m.type, m.tier, m.checksum,
                       m.access_count, m.metadata, m.source,
                       m.created_at, m.accessed_at, m.updated_at,
                       a.strength, a.relation_type
                FROM memory_associations a
                JOIN flash_memories m ON (
                    (a.target_id = m.id AND a.source_id = $1) OR
                    (a.source_id = m.id AND a.target_id = $1)
                )
                WHERE m.id != $1
                ORDER BY a.strength DESC
                LIMIT $2
                """,
                mid,
                limit,
            )

        return [self.memory._row_to_memory(row) for row in rows]

    async def auto_associate(self, new_memory: Memory) -> list[dict]:
        """
        Cuando se almacena una nueva memoria, busca memorias similares
        y crea asociaciones automáticamente.
        Usa embeddings para calcular similitud.
        """
        associations_created = []

        try:
            # Generar embedding de la nueva memoria
            new_embedding = self.embeddings.generate(new_memory.content)

            # Buscar memorias con embedding similar
            similar = await self.memory.search_semantic(
                embedding=new_embedding,
                threshold=AUTO_ASSOCIATION_THRESHOLD,
                limit=MAX_AUTO_ASSOCIATIONS + 1,  # +1 por si se incluye a sí misma
            )

            for mem in similar:
                if mem.id == new_memory.id:
                    continue

                # Calcular strength como la similitud
                if mem.embedding:
                    strength = self.embeddings.similarity(new_embedding, mem.embedding)
                else:
                    strength = AUTO_ASSOCIATION_THRESHOLD

                # Determinar tipo de relación
                relation_type = self._infer_relation_type(new_memory, mem)

                try:
                    assoc = await self.create_association(
                        source_id=new_memory.id,
                        target_id=mem.id,
                        relation_type=relation_type,
                        strength=min(1.0, max(0.0, strength)),
                    )
                    associations_created.append(assoc)
                except (ValueError, Exception) as e:
                    logger.warning(f"Error creando auto-asociación: {e}")

            if associations_created:
                logger.info(
                    f"Auto-asociaciones creadas: {len(associations_created)} "
                    f"para memoria {new_memory.id}"
                )

        except Exception as e:
            logger.error(f"Error en auto_associate: {e}")

        return associations_created

    async def get_association_graph(
        self,
        memory_id: str,
        depth: int = 2,
    ) -> dict:
        """
        Obtiene el grafo de asociaciones hasta cierta profundidad.
        Retorna nodos y aristas para visualización.
        """
        import uuid as uuid_mod
        try:
            mid = uuid_mod.UUID(memory_id) if isinstance(memory_id, str) else memory_id
        except (ValueError, AttributeError):
            mid = memory_id

        visited = set()
        nodes = []
        edges = []

        await self._traverse_graph(mid, depth, visited, nodes, edges)

        return {
            "root": memory_id,
            "depth": depth,
            "nodes": nodes,
            "edges": edges,
            "total_nodes": len(nodes),
            "total_edges": len(edges),
        }

    async def _traverse_graph(
        self,
        memory_id,
        depth: int,
        visited: set,
        nodes: list,
        edges: list,
    ):
        """Recorre el grafo de asociaciones recursivamente."""
        if depth <= 0 or str(memory_id) in visited:
            return

        visited.add(str(memory_id))

        # Obtener la memoria
        mem = await self.memory.get_by_id(str(memory_id))
        if mem:
            nodes.append({
                "id": mem.id,
                "content": mem.content[:100],
                "type": mem.type,
                "tier": mem.tier,
            })

        # Obtener asociaciones
        import uuid as uuid_mod
        try:
            mid = uuid_mod.UUID(str(memory_id)) if isinstance(memory_id, str) else memory_id
        except (ValueError, AttributeError):
            mid = memory_id

        async with self.memory.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT source_id, target_id, relation_type, strength
                FROM memory_associations
                WHERE source_id = $1 OR target_id = $1
                """,
                mid,
            )

        for row in rows:
            edge = {
                "source": str(row["source_id"]),
                "target": str(row["target_id"]),
                "relation": row["relation_type"],
                "strength": row["strength"],
            }
            edges.append(edge)

            # Determinar el nodo vecino
            neighbor = (
                row["target_id"]
                if str(row["source_id"]) == str(memory_id)
                else row["source_id"]
            )
            await self._traverse_graph(
                neighbor, depth - 1, visited, nodes, edges
            )

    @staticmethod
    def _infer_relation_type(memory1: Memory, memory2: Memory) -> str:
        """Infiere el tipo de relación entre dos memorias basándose en sus tipos."""
        types = {memory1.type, memory2.type}

        if "correction" in types:
            return "corrects"
        if types == {"preference"}:
            return "similar_preference"
        if types == {"fact"}:
            return "related_fact"
        if "skill" in types:
            return "related_skill"
        return "semantic_similar"
