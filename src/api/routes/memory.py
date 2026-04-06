"""
YeyoOS — Memory API Endpoints
Micro-fase 3.30 — Capa 3: Cuerpo

Endpoints REST para operaciones de Flash Memory:
- GET  /api/v1/memory/search — búsqueda semántica
- GET  /api/v1/memory/stats — estadísticas
- GET  /api/v1/memory/{id} — obtener memoria
- GET  /api/v1/memory/{id}/associations — asociaciones
- POST /api/v1/memory/manual — crear memoria manualmente
- PUT  /api/v1/memory/{id}/importance — ajustar importancia
- POST /api/v1/memory/{id}/feedback — dar feedback
- POST /api/v1/memory/{id}/promote-tier — promover tier
- POST /api/v1/memory/{id}/demote-tier — degradar tier
- DELETE /api/v1/memory/{id} — PROHIBIDO (405)

⚠️ NO existe endpoint DELETE. Las memorias NUNCA se borran.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

logger = logging.getLogger("yeyoos.api.memory")

router = APIRouter(prefix="/api/v1/memory", tags=["memory"])


# ========== Response Models ==========

class MemoryResponse(BaseModel):
    """Response de una memoria individual."""
    id: str
    content: str
    type: str
    tier: str
    checksum: str
    access_count: int
    metadata: dict = {}
    source: str = "user"
    created_at: Optional[str] = None
    accessed_at: Optional[str] = None


class MemorySearchResponse(BaseModel):
    """Response de búsqueda de memorias."""
    results: list[MemoryResponse]
    total: int
    query: str


class MemoryStatsResponse(BaseModel):
    """Response de estadísticas de memoria."""
    total_memories: int
    by_tier: dict
    by_type: dict
    total_associations: int


class AssociationResponse(BaseModel):
    """Response de una asociación."""
    id: str
    content: str
    type: str
    tier: str
    relation_type: Optional[str] = None
    strength: Optional[float] = None


# ========== Request Models ==========

class ManualMemoryRequest(BaseModel):
    """Request para crear una memoria manualmente."""
    content: str = Field(..., min_length=1, max_length=10000)
    type: str = Field(default="fact", pattern="^(conversation|preference|fact|correction|skill)$")
    namespace: str = Field(default="chat:usuario")
    tier: str = Field(default="WARM", pattern="^(HOT|WARM|COLD)$")
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    source: str = Field(default="manual")
    metadata: dict = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class FeedbackRequest(BaseModel):
    """Request para dar feedback a una memoria."""
    feedback_type: str = Field(..., pattern="^(positive|negative|correction|favorite|reject|training_approved)$")
    score: Optional[float] = Field(None, ge=0.0, le=1.0)
    comment: str = Field(default="")


class ImportanceRequest(BaseModel):
    """Request para ajustar importancia."""
    importance: float = Field(..., ge=0.0, le=1.0)


# ========== Dependency Injection ==========

async def get_flash_memory():
    """Placeholder — sobreescribir con dependency injection."""
    raise HTTPException(status_code=503, detail="Flash Memory not initialized")


async def get_embedding_service():
    """Placeholder — sobreescribir con dependency injection."""
    raise HTTPException(status_code=503, detail="Embedding service not initialized")


async def get_association_engine():
    """Placeholder — sobreescribir con dependency injection."""
    raise HTTPException(status_code=503, detail="Association engine not initialized")


async def get_memory_cache():
    """Placeholder — sobreescribir con dependency injection."""
    return None  # cache es opcional — no lanzar error


# ========== Endpoints ==========

@router.get("/search", response_model=MemorySearchResponse)
async def search_memories(
    q: str = Query(..., min_length=1, description="Texto de búsqueda"),
    limit: int = Query(5, ge=1, le=50),
    threshold: float = Query(0.5, ge=0.0, le=1.0),
    namespace: str | None = Query(None, description="Filtrar por namespace (ej: chat:usuario, codigo:usuario)"),
    flash_memory=Depends(get_flash_memory),
    embedding_service=Depends(get_embedding_service),
):
    """
    Búsqueda semántica en Flash Memory.
    Usa embeddings para encontrar memorias similares al query.
    Opcional: filtrar por namespace con ?namespace=chat:usuario
    """
    try:
        embedding = embedding_service.generate(q)
        memories = await flash_memory.search_semantic(
            embedding=embedding,
            threshold=threshold,
            limit=limit,
            namespaces=[namespace] if namespace else None,
        )

        results = [
            MemoryResponse(
                id=m.id,
                content=m.content,
                type=m.type,
                tier=m.tier,
                checksum=m.checksum,
                access_count=m.access_count,
                metadata=m.metadata,
                source=m.source,
                created_at=m.created_at.isoformat() if m.created_at else None,
                accessed_at=m.accessed_at.isoformat() if m.accessed_at else None,
            )
            for m in memories
        ]

        return MemorySearchResponse(
            results=results,
            total=len(results),
            query=q,
        )

    except Exception as e:
        logger.error(f"Error en búsqueda: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=MemoryStatsResponse)
async def get_memory_stats(
    flash_memory=Depends(get_flash_memory),
):
    """Estadísticas de Flash Memory: conteos por tier y tipo."""
    try:
        stats = await flash_memory.get_stats()
        return MemoryStatsResponse(**stats)
    except Exception as e:
        logger.error(f"Error en stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{memory_id}", response_model=MemoryResponse)
async def get_memory(
    memory_id: str,
    flash_memory=Depends(get_flash_memory),
):
    """Obtiene una memoria específica por ID."""
    try:
        memory = await flash_memory.get_by_id(memory_id)
        if memory is None:
            raise HTTPException(
                status_code=404,
                detail="Memoria no encontrada"
            )
        return MemoryResponse(
            id=memory.id,
            content=memory.content,
            type=memory.type,
            tier=memory.tier,
            checksum=memory.checksum,
            access_count=memory.access_count,
            metadata=memory.metadata,
            source=memory.source,
            created_at=memory.created_at.isoformat() if memory.created_at else None,
            accessed_at=memory.accessed_at.isoformat() if memory.accessed_at else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo memoria: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{memory_id}/associations")
async def get_memory_associations(
    memory_id: str,
    limit: int = Query(5, ge=1, le=50),
    association_engine=Depends(get_association_engine),
):
    """Obtiene memorias asociadas a una memoria específica."""
    try:
        related = await association_engine.find_related(
            memory_id=memory_id,
            limit=limit,
        )
        return [
            AssociationResponse(
                id=m.id,
                content=m.content,
                type=m.type,
                tier=m.tier,
            )
            for m in related
        ]
    except Exception as e:
        logger.error(f"Error en asociaciones: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{memory_id}")
async def delete_memory_forbidden(memory_id: str):
    """
    ⚠️ PROHIBIDO: Las memorias NUNCA se borran en YeyoOS.
    Flash Memory es sagrada. Nada se elimina.
    """
    raise HTTPException(
        status_code=405,
        detail=(
            "DELETE PROHIBIDO: Las memorias de YeyoOS NUNCA se borran. "
            "Flash Memory es sagrada. Si necesitas que una memoria sea "
            "menos relevante, será degradada automáticamente a tier COLD."
        ),
    )


# ========== Write Endpoints ==========

@router.post("/manual")
async def create_manual_memory(
    request: ManualMemoryRequest,
    flash_memory=Depends(get_flash_memory),
    embedding_service=Depends(get_embedding_service),
):
    """
    Crear una memoria manualmente desde el Memory Editor.
    El usuario elige namespace, tipo, tier e importancia.
    """
    try:
        import asyncio
        import json as _json

        # Generar embedding
        embedding = None
        try:
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(None, embedding_service.generate, request.content)
        except Exception as e:
            logger.warning(f"Embedding falló para memoria manual: {e}")

        async with flash_memory.pool.acquire() as conn:
            metadata = {**request.metadata, "tags": request.tags}
            if embedding:
                vector_str = "[" + ",".join(str(x) for x in embedding) + "]"
                row = await conn.fetchrow(
                    """
                    INSERT INTO flash_memories
                        (content, type, tier, namespace, source, metadata, embedding, importance, tags)
                    VALUES ($1, $2, $3, $4, $5, $6, $7::vector, $8, $9)
                    RETURNING id, created_at
                    """,
                    request.content, request.type, request.tier, request.namespace,
                    request.source, _json.dumps(metadata), vector_str,
                    request.importance, request.tags,
                )
            else:
                row = await conn.fetchrow(
                    """
                    INSERT INTO flash_memories
                        (content, type, tier, namespace, source, metadata, importance, tags)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    RETURNING id, created_at
                    """,
                    request.content, request.type, request.tier, request.namespace,
                    request.source, _json.dumps(metadata), request.importance, request.tags,
                )

        return {
            "id": str(row["id"]),
            "created_at": row["created_at"].isoformat(),
            "message": f"Memoria creada en {request.namespace} ({request.tier})",
        }

    except Exception as e:
        logger.error(f"Error creando memoria manual: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{memory_id}/importance")
async def update_memory_importance(
    memory_id: str,
    request: ImportanceRequest,
    flash_memory=Depends(get_flash_memory),
):
    """Ajustar la importancia de una memoria (0.0 a 1.0)."""
    try:
        async with flash_memory.pool.acquire() as conn:
            result = await conn.execute(
                "UPDATE flash_memories SET importance = $1, updated_at = NOW() WHERE id = $2",
                request.importance, memory_id,
            )
            if result == "UPDATE 0":
                raise HTTPException(status_code=404, detail="Memoria no encontrada")
        return {"memory_id": memory_id, "importance": request.importance}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{memory_id}/feedback")
async def give_memory_feedback(
    memory_id: str,
    request: FeedbackRequest,
    flash_memory=Depends(get_flash_memory),
):
    """
    Dar feedback a una memoria: positive, negative, correction, favorite, reject, training_approved.
    El feedback nunca modifica la memoria original.
    """
    try:
        async with flash_memory.pool.acquire() as conn:
            # Verificar que la memoria existe
            exists = await conn.fetchval("SELECT 1 FROM flash_memories WHERE id = $1", memory_id)
            if not exists:
                raise HTTPException(status_code=404, detail="Memoria no encontrada")

            await conn.execute(
                """
                INSERT INTO memory_feedback (memory_id, feedback_type, score, comment, source)
                VALUES ($1, $2, $3, $4, 'user')
                """,
                memory_id, request.feedback_type, request.score, request.comment,
            )

            # Si es reject → degradar a COLD automáticamente
            if request.feedback_type == "reject":
                await conn.execute(
                    "UPDATE flash_memories SET tier = 'COLD', updated_at = NOW() WHERE id = $1",
                    memory_id,
                )

            # Si es training_approved → crear entrada en training corpus
            if request.feedback_type == "training_approved":
                mem = await conn.fetchrow("SELECT type FROM flash_memories WHERE id = $1", memory_id)
                corpus_type = {
                    "correction": "correction_pair",
                    "skill": "reasoning_example",
                    "fact": "benchmark_case",
                    "preference": "preference_pair",
                    "conversation": "prompt_example",
                }.get(mem["type"], "benchmark_case")

                await conn.execute(
                    """
                    INSERT INTO memory_training_corpus (memory_id, corpus_type, split, promoted)
                    VALUES ($1, $2, 'train', TRUE)
                    ON CONFLICT DO NOTHING
                    """,
                    memory_id, corpus_type,
                )

        return {
            "memory_id": memory_id,
            "feedback_type": request.feedback_type,
            "applied": True,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{memory_id}/promote-tier")
async def promote_memory_tier(
    memory_id: str,
    flash_memory=Depends(get_flash_memory),
):
    """Promover memoria al tier superior: COLD→WARM→HOT."""
    try:
        async with flash_memory.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT tier FROM flash_memories WHERE id = $1", memory_id)
            if not row:
                raise HTTPException(status_code=404, detail="Memoria no encontrada")

            current = row["tier"]
            promotion = {"COLD": "WARM", "WARM": "HOT"}
            new_tier = promotion.get(current)
            if not new_tier:
                return {"memory_id": memory_id, "tier": current, "message": "Ya está en HOT"}

            await conn.execute(
                "UPDATE flash_memories SET tier = $1, updated_at = NOW() WHERE id = $2",
                new_tier, memory_id,
            )
            await conn.execute(
                "INSERT INTO memory_audit_log (memory_id, action, details) VALUES ($1, 'PROMOTE', $2)",
                memory_id, f'{{"from": "{current}", "to": "{new_tier}", "source": "manual"}}',
            )

        return {"memory_id": memory_id, "from": current, "to": new_tier}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{memory_id}/demote-tier")
async def demote_memory_tier(
    memory_id: str,
    flash_memory=Depends(get_flash_memory),
):
    """Degradar memoria al tier inferior: HOT→WARM→COLD."""
    try:
        async with flash_memory.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT tier FROM flash_memories WHERE id = $1", memory_id)
            if not row:
                raise HTTPException(status_code=404, detail="Memoria no encontrada")

            current = row["tier"]
            demotion = {"HOT": "WARM", "WARM": "COLD"}
            new_tier = demotion.get(current)
            if not new_tier:
                return {"memory_id": memory_id, "tier": current, "message": "Ya está en COLD"}

            await conn.execute(
                "UPDATE flash_memories SET tier = $1, updated_at = NOW() WHERE id = $2",
                new_tier, memory_id,
            )
            await conn.execute(
                "INSERT INTO memory_audit_log (memory_id, action, details) VALUES ($1, 'DEMOTE', $2)",
                memory_id, f'{{"from": "{current}", "to": "{new_tier}", "source": "manual"}}',
            )

        return {"memory_id": memory_id, "from": current, "to": new_tier}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== Debug Endpoints ==========

@router.get("/debug/hot")
async def debug_hot_cache(
    flash_memory=Depends(get_flash_memory),
    cache=Depends(get_memory_cache),
):
    """
    🔴 Qué está en Redis HOT ahora mismo.
    Muestra las memorias más accedidas cargadas en cache.
    """
    if not cache:
        return {"cache_available": False, "message": "Redis no conectado — modo degradado", "hot_memories": []}

    try:
        hot_ids = await cache.get_hot_memories(limit=50)
        memories = await cache.get_multiple(hot_ids) if hot_ids else []

        return {
            "cache_available": True,
            "hot_count": len(memories),
            "hot_memories": [
                {
                    "id": m.id,
                    "content": m.content[:120] + ("..." if len(m.content) > 120 else ""),
                    "type": m.type,
                    "namespace": m.namespace,
                    "access_count": m.access_count,
                    "accessed_at": m.accessed_at.isoformat() if m.accessed_at else None,
                }
                for m in sorted(memories, key=lambda x: x.access_count, reverse=True)
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/debug/recent")
async def debug_recent_memories(
    limit: int = Query(20, ge=1, le=100),
    namespace: str | None = Query(None),
    flash_memory=Depends(get_flash_memory),
):
    """
    🕐 Últimas memorias guardadas.
    Útil para ver qué está aprendiendo la IA en tiempo real.
    """
    try:
        async with flash_memory.pool.acquire() as conn:
            query = """
                SELECT id, content, type, tier, namespace, source,
                       access_count, importance, tags, created_at, accessed_at
                FROM flash_memories
                {where}
                ORDER BY created_at DESC
                LIMIT $1
            """
            if namespace:
                rows = await conn.fetch(
                    query.format(where="WHERE namespace = $2"),
                    limit, namespace,
                )
            else:
                rows = await conn.fetch(query.format(where=""), limit)

        return {
            "total": len(rows),
            "filter_namespace": namespace,
            "memories": [
                {
                    "id": str(row["id"]),
                    "content": row["content"],
                    "type": row["type"],
                    "tier": row["tier"],
                    "namespace": row["namespace"],
                    "source": row["source"],
                    "access_count": row["access_count"],
                    "importance": row["importance"],
                    "tags": row["tags"],
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                    "accessed_at": row["accessed_at"].isoformat() if row["accessed_at"] else None,
                }
                for row in rows
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/debug/context")
async def debug_context(
    q: str = Query(..., description="Texto de prueba — simula qué memorias usaría la IA"),
    flash_memory=Depends(get_flash_memory),
    embedding_service=Depends(get_embedding_service),
):
    """
    🧠 Dry-run del contexto de memoria.
    Muestra exactamente qué memorias se inyectarían al prompt para un input dado,
    sin enviar nada al modelo de IA.
    """
    try:
        # Intentar búsqueda semántica
        semantic_memories = []
        embedding_ok = False
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(None, embedding_service.generate, q)
            semantic_memories = await flash_memory.search_semantic(
                embedding=embedding,
                threshold=0.3,
                limit=5,
                namespaces=["chat:usuario"],
            )
            embedding_ok = True
        except Exception as e:
            logger.warning(f"debug/context: embedding falló ({e}), usando fallback")

        # Fallback: recall por acceso/recencia
        fallback_memories = []
        if not semantic_memories:
            fallback_memories = await flash_memory.recall(q, limit=5)

        memories = semantic_memories or fallback_memories

        return {
            "query": q,
            "embedding_available": embedding_ok,
            "search_mode": "semantic" if embedding_ok else "fallback (access+recency)",
            "memories_found": len(memories),
            "would_inject": [
                {
                    "id": m.id,
                    "content": m.content,
                    "type": m.type,
                    "tier": m.tier,
                    "namespace": m.namespace,
                    "access_count": m.access_count,
                    "source": m.source,
                }
                for m in memories
            ],
            "prompt_preview": (
                "[MEMORIAS RELEVANTES]\n" +
                "\n".join(f"- [{m.type}] {m.content}" for m in memories)
            ) if memories else "(sin memorias — la IA responderá sin contexto personal)",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/debug/audit")
async def debug_audit_log(
    limit: int = Query(30, ge=1, le=200),
    action: str | None = Query(None, description="Filtrar: CREATE, PROMOTE, DEMOTE"),
    flash_memory=Depends(get_flash_memory),
):
    """
    📋 Audit log de memoria — qué cambió y cuándo.
    Muestra CREATE / PROMOTE / DEMOTE de cada memoria para debuggear
    por qué la IA recuerda (o no recuerda) algo.
    """
    try:
        async with flash_memory.pool.acquire() as conn:
            if action:
                rows = await conn.fetch(
                    """
                    SELECT al.id, al.memory_id, al.action, al.details, al.created_at,
                           fm.content, fm.type, fm.tier, fm.namespace
                    FROM memory_audit_log al
                    LEFT JOIN flash_memories fm ON al.memory_id = fm.id
                    WHERE al.action = $2
                    ORDER BY al.created_at DESC
                    LIMIT $1
                    """,
                    limit, action.upper(),
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT al.id, al.memory_id, al.action, al.details, al.created_at,
                           fm.content, fm.type, fm.tier, fm.namespace
                    FROM memory_audit_log al
                    LEFT JOIN flash_memories fm ON al.memory_id = fm.id
                    ORDER BY al.created_at DESC
                    LIMIT $1
                    """,
                    limit,
                )

        import json as _json
        return {
            "total": len(rows),
            "filter_action": action,
            "events": [
                {
                    "event_id": str(row["id"]),
                    "memory_id": str(row["memory_id"]),
                    "action": row["action"],
                    "details": _json.loads(row["details"]) if row["details"] else {},
                    "timestamp": row["created_at"].isoformat() if row["created_at"] else None,
                    "memory_content": (row["content"] or "")[:100] + ("..." if row["content"] and len(row["content"]) > 100 else ""),
                    "memory_type": row["type"],
                    "memory_tier": row["tier"],
                    "memory_namespace": row["namespace"],
                }
                for row in rows
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/map/distribution")
async def memory_map_distribution(
    flash_memory=Depends(get_flash_memory),
):
    """
    🗺️ Distribución de memorias por namespace × tier × type.
    Alimenta el MemoryMap (Heatmap + Tree views).
    """
    try:
        async with flash_memory.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT namespace, tier, type, 
                       COUNT(*) as count,
                       SUM(access_count) as total_accesses,
                       AVG(COALESCE(importance, 0.5)) as avg_importance
                FROM flash_memories
                GROUP BY namespace, tier, type
                ORDER BY namespace, tier, type
            """)

            ns_rows = await conn.fetch("""
                SELECT namespace, COUNT(*) as count,
                       SUM(access_count) as total_accesses
                FROM flash_memories
                GROUP BY namespace
                ORDER BY count DESC
            """)

        return {
            "cells": [
                {
                    "namespace": row["namespace"] or "sin_namespace",
                    "tier": row["tier"],
                    "type": row["type"],
                    "count": row["count"],
                    "total_accesses": row["total_accesses"],
                    "avg_importance": float(row["avg_importance"]) if row["avg_importance"] else 0.5,
                }
                for row in rows
            ],
            "namespaces": [
                {
                    "namespace": row["namespace"] or "sin_namespace",
                    "count": row["count"],
                    "total_accesses": row["total_accesses"],
                }
                for row in ns_rows
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/map/pipeline")
async def memory_pipeline_events(
    limit: int = Query(20, ge=1, le=50),
):
    """
    🔬 Pipeline de extracción en tiempo real.
    Retorna los últimos pipelines con sus pasos y estadísticas.
    """
    from src.memory.pipeline_events import pipeline_buffer, PIPELINE_DEFS

    return {
        "pipelines": pipeline_buffer.get_pipelines(limit),
        "step_stats": pipeline_buffer.get_step_stats(),
        "recent_events": pipeline_buffer.get_recent(limit * 10),
        "pipeline_defs": PIPELINE_DEFS,
    }
