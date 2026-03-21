"""
YeyoOS — Memory API Endpoints
Micro-fase 2.16 — Capa 2: Cerebro

Endpoints REST para operaciones de Flash Memory:
- GET /api/v1/memory/search — búsqueda semántica
- GET /api/v1/memory/stats — estadísticas
- GET /api/v1/memory/{id} — obtener memoria
- GET /api/v1/memory/{id}/associations — asociaciones
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


# ========== Endpoints ==========

@router.get("/search", response_model=MemorySearchResponse)
async def search_memories(
    q: str = Query(..., min_length=1, description="Texto de búsqueda"),
    limit: int = Query(5, ge=1, le=50),
    threshold: float = Query(0.5, ge=0.0, le=1.0),
    flash_memory=Depends(get_flash_memory),
    embedding_service=Depends(get_embedding_service),
):
    """
    Búsqueda semántica en Flash Memory.
    Usa embeddings para encontrar memorias similares al query.
    """
    try:
        embedding = embedding_service.generate(q)
        memories = await flash_memory.search_semantic(
            embedding=embedding,
            threshold=threshold,
            limit=limit,
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
