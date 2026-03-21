## ═══════════════════════════════════════
## MICRO-FASE 1.6 — API Tests
## Tipo: VSCODE | Prompts: 2 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 1.6-2 [VSCODE] — Tests de la API FastAPI

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 1.6, Prompt 2 de 2: tests completos para la API FastAPI.

CONTEXTO:
- Prompt 1.6-1 completado: FastAPI skeleton con /health y /api/v1/status
- Usamos httpx + pytest para tests de API
- TestClient de FastAPI para tests sin levantar servidor real
- CORS debe permitir SOLO http://localhost:3000

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Instalar dependencia de test:
   cd ~/yeyo-os
   source .venv/bin/activate
   pip install httpx

2. Crear directorio para tests de API:
   mkdir -p tests/unit/api

3. Crear archivo tests/unit/api/__init__.py:

   Ruta: ~/yeyo-os/tests/unit/api/__init__.py
   Contenido: (archivo vacío)

4. Crear archivo tests/unit/api/test_api_main.py:

   Ruta: ~/yeyo-os/tests/unit/api/test_api_main.py
   Contenido:

   """Tests para API Base — Micro-fase 1.6"""
   
   import pytest
   from fastapi.testclient import TestClient
   from src.api.main import app
   
   
   @pytest.fixture
   def client():
       """Cliente de test para la API."""
       return TestClient(app)
   
   
   class TestHealthEndpoint:
       """Tests para /health."""
   
       def test_health_returns_200(self, client):
           response = client.get("/health")
           assert response.status_code == 200
   
       def test_health_returns_json(self, client):
           response = client.get("/health")
           data = response.json()
           assert "status" in data
           assert "version" in data
           assert "uptime_seconds" in data
   
       def test_health_status_is_healthy(self, client):
           response = client.get("/health")
           assert response.json()["status"] == "healthy"
   
       def test_health_version_is_correct(self, client):
           response = client.get("/health")
           assert response.json()["version"] == "0.1.0"
   
       def test_health_uptime_is_number(self, client):
           response = client.get("/health")
           uptime = response.json()["uptime_seconds"]
           assert isinstance(uptime, (int, float))
           assert uptime >= 0
   
   
   class TestStatusEndpoint:
       """Tests para /api/v1/status."""
   
       def test_status_returns_200(self, client):
           response = client.get("/api/v1/status")
           assert response.status_code == 200
   
       def test_status_returns_json(self, client):
           response = client.get("/api/v1/status")
           data = response.json()
           assert "status" in data
           assert "version" in data
           assert "services" in data
   
       def test_status_has_all_services(self, client):
           response = client.get("/api/v1/status")
           services = response.json()["services"]
           assert "api" in services
           assert "postgresql" in services
           assert "redis" in services
           assert "ollama" in services
           assert "gpu" in services
   
       def test_status_api_is_up(self, client):
           response = client.get("/api/v1/status")
           assert response.json()["services"]["api"] == "up"
   
       def test_status_pending_services(self, client):
           """Servicios pendientes hasta Capa 2."""
           response = client.get("/api/v1/status")
           services = response.json()["services"]
           assert services["postgresql"] == "pending"
           assert services["redis"] == "pending"
           assert services["ollama"] == "pending"
           assert services["gpu"] == "pending"
   
   
   class TestCORS:
       """Tests para CORS middleware."""
   
       def test_cors_allows_localhost_3000(self, client):
           response = client.options(
               "/health",
               headers={
                   "Origin": "http://localhost:3000",
                   "Access-Control-Request-Method": "GET",
               },
           )
           assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
   
       def test_cors_blocks_unknown_origin(self, client):
           response = client.options(
               "/health",
               headers={
                   "Origin": "http://evil.com",
                   "Access-Control-Request-Method": "GET",
               },
           )
           assert response.headers.get("access-control-allow-origin") != "http://evil.com"
   
       def test_cors_allows_credentials(self, client):
           response = client.options(
               "/health",
               headers={
                   "Origin": "http://localhost:3000",
                   "Access-Control-Request-Method": "GET",
               },
           )
           assert response.headers.get("access-control-allow-credentials") == "true"
   
   
   class TestAppMetadata:
       """Tests para metadata de la app."""
   
       def test_app_title(self):
           assert app.title == "YeyoOS API"
   
       def test_app_version(self):
           assert app.version == "0.1.0"
   
       def test_openapi_available(self, client):
           response = client.get("/openapi.json")
           assert response.status_code == 200
   
       def test_docs_available(self, client):
           response = client.get("/docs")
           assert response.status_code == 200
   
   
   class TestNotFound:
       """Tests para rutas inexistentes."""
   
       def test_unknown_route_returns_404(self, client):
           response = client.get("/nonexistent")
           assert response.status_code == 404
   
       def test_unknown_api_route_returns_404(self, client):
           response = client.get("/api/v1/nonexistent")
           assert response.status_code == 404

5. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/api/test_api_main.py -v

VERIFICAR:
- [ ] TODOS los tests pasan (0 failed)
- [ ] /health retorna 200 con status "healthy"
- [ ] /api/v1/status retorna 200 con 5 services
- [ ] CORS permite localhost:3000
- [ ] CORS bloquea orígenes desconocidos
- [ ] OpenAPI y docs accesibles
- [ ] Rutas inexistentes retornan 404

SI FALLA:
- httpx no instalado: `pip install httpx`
- TestClient error: `from fastapi.testclient import TestClient`
- CORS test falla: verificar que el middleware está configurado correctamente en main.py

NO HACER:
- No agregar tests de autenticación (no existe todavía)
- No testear endpoints de chat/memoria (no existen)
- No hacer tests de carga/rendimiento aún
- No mockear el servidor completo

GATE: Todos los tests de API pasan, CORS verificado, health y status endpoints funcionando.
```
