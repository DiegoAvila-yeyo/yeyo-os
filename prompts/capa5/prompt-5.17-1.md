## ═══════════════════════════════════════
## MICRO-FASE 5.17 — Node API Endpoints
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 5.17-1 [VSCODE] — REST API para gestión de nodos

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 5.17 de Capa 5 (Órganos): crear los endpoints REST API para gestionar nodos.

CONTEXTO:
- Micro-fase 5.16 completada: NodeRegistry con registro central
- API REST para: listar tipos, abrir nodos, cerrar nodos, obtener status, enviar datos
- Cada nodo abierto tiene un ID único y corre en su container
- FastAPI router con prefijo /api/v1/nodes
- Backend: Python 3.11 + FastAPI

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear estructura:
   mkdir -p src/api/routes

2. Crear archivo src/api/routes/__init__.py (vacío si no existe):

   Ruta: ~/yeyo-os/src/api/routes/__init__.py
   Contenido: (archivo vacío)

3. Crear archivo src/api/routes/nodes.py:

   Ruta: ~/yeyo-os/src/api/routes/nodes.py
   Contenido:

   """
   YeyoOS — Node API Endpoints
   Micro-fase 5.17 — Capa 5: Órganos

   REST API para gestión de nodos del sistema.
   """

   from fastapi import APIRouter, HTTPException
   from pydantic import BaseModel
   from typing import Optional, Any

   from src.nodes.registry import NodeRegistry, NodeNotFoundError
   from src.nodes.base import NodeBase


   router = APIRouter(prefix="/api/v1/nodes", tags=["nodes"])

   # Nodos activos en memoria
   _active_nodes: dict[str, NodeBase] = {}


   class OpenNodeRequest(BaseModel):
       config: Optional[dict] = None


   class ProcessNodeRequest(BaseModel):
       data: dict


   # ═══════════════════════════════════
   # ENDPOINTS
   # ═══════════════════════════════════

   @router.get("/")
   async def list_node_types() -> dict:
       """GET /api/v1/nodes — Lista tipos de nodo disponibles."""
       types = NodeRegistry.list_types()
       return {
           "types": [
               {
                   "type": t,
                   **NodeRegistry.get_info(t),
               }
               for t in types
           ],
           "count": len(types),
       }

   @router.get("/active")
   async def list_active_nodes() -> dict:
       """GET /api/v1/nodes/active — Lista nodos activos."""
       nodes_info = []
       for node_id, node in _active_nodes.items():
           status = await node.get_status()
           nodes_info.append(status)
       return {"nodes": nodes_info, "count": len(nodes_info)}

   @router.post("/{node_type}/open")
   async def open_node(node_type: str, request: OpenNodeRequest = OpenNodeRequest()) -> dict:
       """POST /api/v1/nodes/{type}/open — Abre un nodo."""
       try:
           node = NodeRegistry.create(node_type)
       except NodeNotFoundError as e:
           raise HTTPException(status_code=404, detail=str(e))

       try:
           await node.open()
       except Exception as e:
           raise HTTPException(status_code=500, detail=f"Error inicializando nodo: {e}")

       _active_nodes[node.id] = node

       return {
           "node_id": node.id,
           "type": node_type,
           "status": node.status.value,
       }

   @router.delete("/{node_id}/close")
   async def close_node(node_id: str) -> dict:
       """DELETE /api/v1/nodes/{id}/close — Cierra un nodo."""
       if node_id not in _active_nodes:
           raise HTTPException(status_code=404, detail=f"Nodo '{node_id}' no encontrado")

       node = _active_nodes[node_id]
       try:
           await node.close()
       except Exception as e:
           raise HTTPException(status_code=500, detail=f"Error cerrando nodo: {e}")

       del _active_nodes[node_id]

       return {"node_id": node_id, "status": "closed"}

   @router.get("/{node_id}/status")
   async def get_node_status(node_id: str) -> dict:
       """GET /api/v1/nodes/{id}/status — Obtiene status de un nodo."""
       if node_id not in _active_nodes:
           raise HTTPException(status_code=404, detail=f"Nodo '{node_id}' no encontrado")

       node = _active_nodes[node_id]
       return await node.get_status()

   @router.post("/{node_id}/process")
   async def process_node_data(node_id: str, request: ProcessNodeRequest) -> dict:
       """POST /api/v1/nodes/{id}/process — Envía datos a un nodo."""
       if node_id not in _active_nodes:
           raise HTTPException(status_code=404, detail=f"Nodo '{node_id}' no encontrado")

       node = _active_nodes[node_id]
       try:
           result = await node.process(request.data)
           return {"node_id": node_id, "result": result}
       except Exception as e:
           raise HTTPException(status_code=500, detail=f"Error procesando: {e}")

   @router.get("/{node_id}/ui")
   async def get_node_ui(node_id: str) -> dict:
       """GET /api/v1/nodes/{id}/ui — Obtiene configuración UI del nodo."""
       if node_id not in _active_nodes:
           raise HTTPException(status_code=404, detail=f"Nodo '{node_id}' no encontrado")

       node = _active_nodes[node_id]
       return await node.render_ui()

4. Crear archivo tests/unit/nodes/test_node_api.py:

   Ruta: ~/yeyo-os/tests/unit/nodes/test_node_api.py
   Contenido:

   """Tests para Node API Endpoints — Micro-fase 5.17"""

   import pytest
   from unittest.mock import AsyncMock, patch, MagicMock
   from fastapi.testclient import TestClient
   from fastapi import FastAPI

   from src.api.routes.nodes import router, _active_nodes
   from src.nodes.base import NodeBase, PrivilegeLevel
   from src.nodes.registry import NodeRegistry


   class FakeNode(NodeBase):
       async def initialize(self): pass
       async def render_ui(self) -> dict:
           return {"component": "FakeNode", "props": {}}
       async def process(self, input_data: dict) -> dict:
           return {"echo": input_data}
       async def cleanup(self): pass

       def __init__(self):
           super().__init__(name="Fake", version="1.0")


   @pytest.fixture
   def client():
       app = FastAPI()
       app.include_router(router)
       _active_nodes.clear()
       NodeRegistry.clear()
       NodeRegistry.register("fake", FakeNode)
       return TestClient(app)


   class TestNodeAPIEndpoints:

       def test_list_node_types(self, client):
           response = client.get("/api/v1/nodes/")
           assert response.status_code == 200
           data = response.json()
           assert "types" in data
           assert data["count"] >= 1

       def test_open_node(self, client):
           response = client.post("/api/v1/nodes/fake/open")
           assert response.status_code == 200
           data = response.json()
           assert "node_id" in data
           assert data["type"] == "fake"

       def test_open_unknown_type_404(self, client):
           response = client.post("/api/v1/nodes/nonexistent/open")
           assert response.status_code == 404

       def test_close_node(self, client):
           # Open first
           open_resp = client.post("/api/v1/nodes/fake/open")
           node_id = open_resp.json()["node_id"]
           # Close
           close_resp = client.delete(f"/api/v1/nodes/{node_id}/close")
           assert close_resp.status_code == 200

       def test_close_nonexistent_404(self, client):
           response = client.delete("/api/v1/nodes/fake-id/close")
           assert response.status_code == 404

       def test_get_status(self, client):
           open_resp = client.post("/api/v1/nodes/fake/open")
           node_id = open_resp.json()["node_id"]
           status_resp = client.get(f"/api/v1/nodes/{node_id}/status")
           assert status_resp.status_code == 200
           data = status_resp.json()
           assert data["name"] == "Fake"

       def test_process_data(self, client):
           open_resp = client.post("/api/v1/nodes/fake/open")
           node_id = open_resp.json()["node_id"]
           process_resp = client.post(
               f"/api/v1/nodes/{node_id}/process",
               json={"data": {"key": "value"}},
           )
           assert process_resp.status_code == 200

       def test_list_active_nodes(self, client):
           client.post("/api/v1/nodes/fake/open")
           response = client.get("/api/v1/nodes/active")
           assert response.status_code == 200
           assert response.json()["count"] == 1

5. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/nodes/test_node_api.py -v

VERIFICAR:
- [ ] GET /api/v1/nodes — lista tipos disponibles
- [ ] POST /api/v1/nodes/{type}/open — abre nodo, retorna ID
- [ ] DELETE /api/v1/nodes/{id}/close — cierra nodo
- [ ] GET /api/v1/nodes/{id}/status — retorna status
- [ ] POST /api/v1/nodes/{id}/process — envía datos al nodo
- [ ] 404 para tipo desconocido y nodo no encontrado
- [ ] TODOS los tests pasan

SI FALLA:
- FastAPI: `pip install fastapi`
- TestClient: `pip install httpx` (requerido por TestClient)
- Import error: verificar __init__.py

NO HACER:
- No exponer endpoints sin autenticación en producción
- No permitir abrir nodos sin verificar permisos
- No implementar WebSocket aquí (eso sería Capa 6)

GATE: API REST completa para nodos, todos los endpoints funcionan, 404 correcto, open/close lifecycle, todos los tests pasan.
```
