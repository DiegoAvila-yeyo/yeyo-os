## ═══════════════════════════════════════
## MICRO-FASE 2.16 — Memory API Endpoints
## Tipo: VSCODE | Prompts: 1 | Complejidad: Simple
## ═══════════════════════════════════════

### PROMPT 2.16-1 [VSCODE] — Implementar endpoints FastAPI para memoria

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 2.16 de Capa 2 (Cerebro): implementar los endpoints de la API REST para operaciones de Flash Memory. IMPORTANTE: NO existe endpoint DELETE — las memorias NUNCA se borran.

CONTEXTO:
- Capa 1 completada: FastAPI base configurada
- Micro-fases 2.0-2.10 completadas: FlashMemory, Embeddings, Asociaciones funcionando
- REGLA SAGRADA: NO hay endpoint DELETE para memorias
- Si alguien intenta DELETE, retornar 405 Method Not Allowed con mensaje explicativo
- Hardware: GTX 1060 3GB VRAM, 16GB RAM, WSL2 Ubuntu

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/api/routes/memory.py:

   Ruta: ~/yeyo-os/src/api/routes/memory.py
   Contenido:

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

2. Crear tests:

   Ruta: ~/yeyo-os/tests/unit/api/test_memory_routes.py
   Contenido:

   """
   Tests para Memory API Endpoints — Micro-fase 2.16
   Tests unitarios con TestClient de FastAPI.
   """

   import pytest
   from unittest.mock import AsyncMock, MagicMock
   from fastapi import FastAPI
   from fastapi.testclient import TestClient
   from src.api.routes.memory import (
       router,
       get_flash_memory,
       get_embedding_service,
       get_association_engine,
   )
   from src.memory.models import Memory


   @pytest.fixture
   def mock_flash_memory():
       fm = AsyncMock()
       fm.search_semantic.return_value = [
           Memory(
               id="mem-1",
               content="Python es mi favorito",
               type="preference",
               checksum="a" * 64,
               access_count=5,
           ),
       ]
       fm.get_by_id.return_value = Memory(
           id="mem-1",
           content="Python es mi favorito",
           type="preference",
           checksum="a" * 64,
           access_count=5,
       )
       fm.get_stats.return_value = {
           "total_memories": 42,
           "by_tier": {"HOT": 5, "WARM": 30, "COLD": 7},
           "by_type": {"fact": 20, "preference": 12, "conversation": 10},
           "total_associations": 15,
       }
       return fm


   @pytest.fixture
   def mock_embedding_service():
       emb = MagicMock()
       emb.generate.return_value = [0.1] * 384
       return emb


   @pytest.fixture
   def mock_association_engine():
       ae = AsyncMock()
       ae.find_related.return_value = [
           Memory(
               id="mem-2",
               content="JavaScript también me gusta",
               type="preference",
               checksum="b" * 64,
           ),
       ]
       return ae


   @pytest.fixture
   def client(mock_flash_memory, mock_embedding_service, mock_association_engine):
       app = FastAPI()
       app.include_router(router)

       app.dependency_overrides[get_flash_memory] = lambda: mock_flash_memory
       app.dependency_overrides[get_embedding_service] = lambda: mock_embedding_service
       app.dependency_overrides[get_association_engine] = lambda: mock_association_engine

       return TestClient(app)


   class TestSearchEndpoint:
       """Tests de GET /api/v1/memory/search."""

       def test_search_returns_results(self, client):
           response = client.get("/api/v1/memory/search?q=Python")
           assert response.status_code == 200
           data = response.json()
           assert "results" in data
           assert "total" in data
           assert "query" in data
           assert data["query"] == "Python"

       def test_search_requires_query(self, client):
           response = client.get("/api/v1/memory/search")
           assert response.status_code == 422

       def test_search_empty_query_rejected(self, client):
           response = client.get("/api/v1/memory/search?q=")
           assert response.status_code == 422


   class TestStatsEndpoint:
       """Tests de GET /api/v1/memory/stats."""

       def test_stats_returns_data(self, client):
           response = client.get("/api/v1/memory/stats")
           assert response.status_code == 200
           data = response.json()
           assert "total_memories" in data
           assert "by_tier" in data
           assert "by_type" in data
           assert "total_associations" in data

       def test_stats_has_correct_total(self, client):
           response = client.get("/api/v1/memory/stats")
           data = response.json()
           assert data["total_memories"] == 42


   class TestGetMemoryEndpoint:
       """Tests de GET /api/v1/memory/{id}."""

       def test_get_memory_by_id(self, client):
           response = client.get("/api/v1/memory/mem-1")
           assert response.status_code == 200
           data = response.json()
           assert data["id"] == "mem-1"
           assert data["content"] == "Python es mi favorito"

       def test_get_memory_not_found(self, client, mock_flash_memory):
           mock_flash_memory.get_by_id.return_value = None
           response = client.get("/api/v1/memory/nonexistent")
           assert response.status_code == 404


   class TestAssociationsEndpoint:
       """Tests de GET /api/v1/memory/{id}/associations."""

       def test_get_associations(self, client):
           response = client.get("/api/v1/memory/mem-1/associations")
           assert response.status_code == 200
           data = response.json()
           assert isinstance(data, list)
           assert len(data) > 0


   class TestDeleteForbidden:
       """Tests de DELETE — DEBE ESTAR PROHIBIDO."""

       def test_delete_returns_405(self, client):
           """DELETE de memoria DEBE retornar 405 Method Not Allowed."""
           response = client.delete("/api/v1/memory/mem-1")
           assert response.status_code == 405

       def test_delete_has_explanation(self, client):
           """DELETE debe incluir mensaje explicando por qué está prohibido."""
           response = client.delete("/api/v1/memory/mem-1")
           data = response.json()
           assert "PROHIBIDO" in data["detail"] or "NUNCA" in data["detail"]

       def test_delete_any_id_forbidden(self, client):
           """DELETE debe ser prohibido para CUALQUIER ID."""
           for test_id in ["mem-1", "mem-999", "any-id", "test"]:
               response = client.delete(f"/api/v1/memory/{test_id}")
               assert response.status_code == 405


   class TestAllEndpointsExist:
       """Verificar que todos los endpoints existen."""

       def test_search_exists(self, client):
           response = client.get("/api/v1/memory/search?q=test")
           assert response.status_code != 404

       def test_stats_exists(self, client):
           response = client.get("/api/v1/memory/stats")
           assert response.status_code != 404

       def test_get_by_id_exists(self, client):
           response = client.get("/api/v1/memory/test-id")
           assert response.status_code != 404

       def test_associations_exists(self, client):
           response = client.get("/api/v1/memory/test-id/associations")
           assert response.status_code != 404

       def test_delete_exists_but_forbidden(self, client):
           response = client.delete("/api/v1/memory/test-id")
           assert response.status_code == 405

3. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/api/test_memory_routes.py -v

VERIFICAR:
- [ ] Archivo src/api/routes/memory.py existe
- [ ] GET /api/v1/memory/search — búsqueda semántica funciona
- [ ] GET /api/v1/memory/stats — estadísticas correctas
- [ ] GET /api/v1/memory/{id} — obtiene memoria
- [ ] GET /api/v1/memory/{id}/associations — asociaciones
- [ ] DELETE /api/v1/memory/{id} — retorna 405 SIEMPRE
- [ ] DELETE incluye mensaje explicativo
- [ ] Query vacío rechazado (422)
- [ ] Memoria no encontrada retorna 404
- [ ] TODOS los tests pasan

SI FALLA:
- FastAPI no instalado: `pip install fastapi`
- httpx: `pip install httpx` (para TestClient)
- Import error: verificar micro-fases 2.1, 2.3, 2.10

NO HACER:
- NUNCA crear un endpoint DELETE funcional para memorias
- No exponer embeddings raw en la API
- No permitir modificación directa de memorias via API
- No remover el endpoint DELETE 405 (es documentación activa)

GATE: Todos los endpoints existen, búsqueda semántica funciona, DELETE retorna 405 SIEMPRE, stats correctos, todos los tests pasan.
```
