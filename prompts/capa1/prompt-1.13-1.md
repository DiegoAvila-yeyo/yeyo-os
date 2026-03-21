## ═══════════════════════════════════════
## MICRO-FASE 1.13 — Integration Test Capa 1
## Tipo: MIXTA (CLI + VSCODE) | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 1.13-1 [MIXTA] — Test de integración completo de Capa 1

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Micro-fase 1.13: INTEGRATION TEST de toda la Capa 1. Esta es la verificación final antes de pasar a Capa 2.

TODAS las micro-fases 1.0-1.12 deben estar completadas.
TAMBIÉN la Capa 0 debe seguir pasando (test de regresión).

EJECUTAR:

1. Ir al proyecto:
   cd ~/yeyo-os
   source .venv/bin/activate

2. Primero verificar que Capa 0 sigue pasando (REGRESIÓN):
   python -m pytest tests/test_capa0_integration.py -v --tb=short
   # Si algún test falla, corregir ANTES de continuar

3. Crear archivo tests/test_capa1_integration.py:

   Ruta: ~/yeyo-os/tests/test_capa1_integration.py
   Contenido:

   """
   Integration Test — Capa 1: Esqueleto
   Micro-fase 1.13
   
   Verifica que TODAS las piezas de Capa 1 están en su lugar
   y funcionan correctamente en conjunto.
   
   Ejecutar: pytest tests/test_capa1_integration.py -v
   """
   
   import pytest
   import asyncio
   import json
   import time
   from unittest.mock import AsyncMock, MagicMock
   from fastapi.testclient import TestClient
   
   
   # ============================================================
   # 1.0 — IAProvider Interface
   # ============================================================
   
   class TestIAProviderInterface:
       """Verifica que la interfaz IAProvider está correctamente definida."""
   
       def test_import_ia_interfaces(self):
           from src.ia.interfaces import IAProvider, IAMessage, IAResponse
           assert IAProvider is not None
           assert IAMessage is not None
           assert IAResponse is not None
   
       def test_ia_provider_is_abstract(self):
           from src.ia.interfaces import IAProvider
           with pytest.raises(TypeError):
               IAProvider()
   
       def test_ia_provider_has_seven_methods(self):
           from src.ia.interfaces import IAProvider
           assert len(IAProvider.__abstractmethods__) == 7
   
       def test_ia_message_validates(self):
           from src.ia.interfaces import IAMessage
           msg = IAMessage(role="user", content="test")
           assert msg.role == "user"
   
       def test_ia_response_has_fields(self):
           from src.ia.interfaces import IAResponse
           fields = IAResponse.model_fields
           assert "content" in fields
           assert "model" in fields
           assert "tokens_used" in fields
           assert "latency_ms" in fields
   
   
   # ============================================================
   # 1.1 — OllamaProvider
   # ============================================================
   
   class TestOllamaProvider:
       """Verifica que OllamaProvider implementa IAProvider."""
   
       def test_import_ollama_provider(self):
           from src.ia.ollama_provider import OllamaProvider
           assert OllamaProvider is not None
   
       def test_ollama_is_ia_provider(self):
           from src.ia.ollama_provider import OllamaProvider
           from src.ia.interfaces import IAProvider
           provider = OllamaProvider()
           assert isinstance(provider, IAProvider)
   
       def test_ollama_default_model(self):
           from src.ia.ollama_provider import OllamaProvider
           provider = OllamaProvider()
           assert provider.get_model_name() == "qwen2.5:3b"
   
       def test_ollama_max_tokens(self):
           from src.ia.ollama_provider import OllamaProvider
           provider = OllamaProvider()
           assert provider.get_max_tokens() == 4000
   
   
   # ============================================================
   # 1.2 — MemoriaProvider Interface
   # ============================================================
   
   class TestMemoriaProviderInterface:
       """Verifica que MemoriaProvider está correctamente definida."""
   
       def test_import_memoria_interfaces(self):
           from src.memory.interfaces import MemoriaProvider, Memory, MemoryTier, MemoryType
           assert MemoriaProvider is not None
   
       def test_memoria_is_abstract(self):
           from src.memory.interfaces import MemoriaProvider
           with pytest.raises(TypeError):
               MemoriaProvider()
   
       def test_memoria_has_nine_methods(self):
           from src.memory.interfaces import MemoriaProvider
           assert len(MemoriaProvider.__abstractmethods__) == 9
   
       def test_no_delete_method(self):
           from src.memory.interfaces import MemoriaProvider
           assert not hasattr(MemoriaProvider, "delete")
           assert not hasattr(MemoriaProvider, "remove")
   
       def test_memory_tiers(self):
           from src.memory.interfaces import MemoryTier
           assert MemoryTier.HOT == "HOT"
           assert MemoryTier.WARM == "WARM"
           assert MemoryTier.COLD == "COLD"
   
       def test_memory_types(self):
           from src.memory.interfaces import MemoryType
           assert len(MemoryType) == 5
   
   
   # ============================================================
   # 1.3 — Orquestador Interface
   # ============================================================
   
   class TestOrquestadorInterface:
       """Verifica que Orquestador está correctamente definido."""
   
       def test_import_orquestador(self):
           from src.core.interfaces import OrquestadorProvider, TokenBudget
           assert OrquestadorProvider is not None
   
       def test_orquestador_is_abstract(self):
           from src.core.interfaces import OrquestadorProvider
           with pytest.raises(TypeError):
               OrquestadorProvider()
   
       def test_token_budget_is_4000(self):
           from src.core.interfaces import TokenBudget
           budget = TokenBudget()
           assert budget.total == 4000
   
   
   # ============================================================
   # 1.4 — Config System
   # ============================================================
   
   class TestConfigSystem:
       """Verifica que el sistema de configuración funciona."""
   
       def test_import_config(self):
           from src.core.config import YeyoConfig, get_config
           assert YeyoConfig is not None
   
       def test_config_with_overrides(self):
           from src.core.config import get_config
           config = get_config(
               database_url="postgresql://test@localhost/test",
               redis_url="redis://localhost:6379/0",
           )
           assert config.ollama_host == "http://localhost:11434"
           assert config.ollama_model == "qwen2.5:3b"
   
       def test_token_budget_total(self):
           from src.core.config import get_config
           config = get_config(
               database_url="postgresql://test@localhost/test",
               redis_url="redis://localhost:6379/0",
           )
           assert config.token_budget_total == 4000
   
       def test_gpu_available_vram(self):
           from src.core.config import get_config
           config = get_config(
               database_url="postgresql://test@localhost/test",
               redis_url="redis://localhost:6379/0",
           )
           assert config.gpu_available_vram_mb == 2872
   
   
   # ============================================================
   # 1.5 — Factory Pattern
   # ============================================================
   
   class TestFactory:
       """Verifica que el Factory funciona correctamente."""
   
       def test_import_factory(self):
           from src.core.factory import ProviderFactory
           assert ProviderFactory is not None
   
       def test_factory_returns_ia_provider(self):
           from src.core.factory import ProviderFactory
           from src.core.config import get_config
           from src.ia.interfaces import IAProvider
           ProviderFactory.reset()
           ProviderFactory._config = None
           config = get_config(
               database_url="postgresql://test@localhost/test",
               redis_url="redis://localhost:6379/0",
           )
           provider = ProviderFactory.get_ia_provider(config=config)
           assert isinstance(provider, IAProvider)
           ProviderFactory.reset()
   
       def test_factory_memoria_not_implemented(self):
           from src.core.factory import ProviderFactory
           ProviderFactory.reset()
           ProviderFactory._config = None
           with pytest.raises(NotImplementedError):
               ProviderFactory.get_memoria_provider()
   
       def test_factory_singleton(self):
           from src.core.factory import ProviderFactory
           from src.core.config import get_config
           ProviderFactory.reset()
           ProviderFactory._config = None
           config = get_config(
               database_url="postgresql://test@localhost/test",
               redis_url="redis://localhost:6379/0",
           )
           p1 = ProviderFactory.get_ia_provider(config=config)
           p2 = ProviderFactory.get_ia_provider(config=config)
           assert p1 is p2
           ProviderFactory.reset()
   
   
   # ============================================================
   # 1.6 — API Base (FastAPI)
   # ============================================================
   
   class TestAPIBase:
       """Verifica que la API FastAPI funciona."""
   
       def test_import_app(self):
           from src.api.main import app
           assert app is not None
   
       def test_health_endpoint(self):
           from src.api.main import app
           client = TestClient(app)
           response = client.get("/health")
           assert response.status_code == 200
           data = response.json()
           assert data["status"] == "healthy"
           assert data["version"] == "0.1.0"
   
       def test_status_endpoint(self):
           from src.api.main import app
           client = TestClient(app)
           response = client.get("/api/v1/status")
           assert response.status_code == 200
           data = response.json()
           assert "services" in data
           assert len(data["services"]) == 5
   
       def test_cors_configured(self):
           from src.api.main import app
           client = TestClient(app)
           response = client.options(
               "/health",
               headers={
                   "Origin": "http://localhost:3000",
                   "Access-Control-Request-Method": "GET",
               },
           )
           assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
   
   
   # ============================================================
   # 1.7 — WebSocket Server
   # ============================================================
   
   class TestWebSocket:
       """Verifica que el WebSocket funciona."""
   
       def test_import_connection_manager(self):
           from src.api.websocket import ConnectionManager
           assert ConnectionManager is not None
   
       def test_connection_manager_defaults(self):
           from src.api.websocket import ConnectionManager
           mgr = ConnectionManager()
           assert mgr.max_connections == 50
           assert mgr.connection_count == 0
   
       def test_websocket_echo(self):
           from src.api.main import app
           client = TestClient(app)
           with client.websocket_connect("/ws") as websocket:
               websocket.send_text("integration test")
               data = websocket.receive_json()
               assert data["type"] == "echo"
               assert data["content"] == "integration test"
   
   
   # ============================================================
   # 1.8 — GPU Scheduler
   # ============================================================
   
   class TestGPUScheduler:
       """Verifica que el GPU Scheduler funciona."""
   
       def test_import_gpu_scheduler(self):
           from src.core.gpu_scheduler import GPUScheduler, GPUPriority, GPUTask
           assert GPUScheduler is not None
   
       def test_gpu_scheduler_defaults(self):
           from src.core.gpu_scheduler import GPUScheduler
           s = GPUScheduler()
           assert s.total_vram_mb == 3072
           assert s.compositor_reserved_mb == 200
           assert s.available_vram_mb == 2872
   
       @pytest.mark.asyncio
       async def test_gpu_submit_and_release(self):
           from src.core.gpu_scheduler import GPUScheduler, GPUPriority, GPUTask
           s = GPUScheduler()
           task = GPUTask(
               name="test",
               priority=GPUPriority.P1_USER,
               vram_needed_mb=1800,
           )
           task_id = await s.submit(task)
           assert s.free_vram_mb == 1072
           await s.release(task_id)
           assert s.free_vram_mb == 2872
   
       @pytest.mark.asyncio
       async def test_gpu_preemption(self):
           from src.core.gpu_scheduler import GPUScheduler, GPUPriority, GPUTask
           s = GPUScheduler()
           bg = GPUTask(name="bg", priority=GPUPriority.P2_BACKGROUND, vram_needed_mb=1800)
           user = GPUTask(name="user", priority=GPUPriority.P1_USER, vram_needed_mb=1800)
           await s.submit(bg)
           await s.submit(user)
           assert user.status == "running"
           assert bg.status == "preempted"
   
   
   # ============================================================
   # 1.9 — Event Bus
   # ============================================================
   
   class TestEventBus:
       """Verifica que el Event Bus funciona."""
   
       def test_import_event_bus(self):
           from src.core.event_bus import EventBus, SYSTEM_EVENTS
           assert EventBus is not None
           assert len(SYSTEM_EVENTS) > 0
   
       def test_singleton(self):
           from src.core.event_bus import EventBus
           EventBus.reset_instance()
           b1 = EventBus.instance()
           b2 = EventBus.instance()
           assert b1 is b2
           EventBus.reset_instance()
   
       @pytest.mark.asyncio
       async def test_pub_sub(self):
           from src.core.event_bus import EventBus
           bus = EventBus()
           received = []
           async def handler(data):
               received.append(data)
           bus.subscribe("test.event", handler)
           await bus.publish("test.event", "hello")
           assert received == ["hello"]
           bus.clear()
   
   
   # ============================================================
   # 1.10 — Error Handling
   # ============================================================
   
   class TestErrorHandling:
       """Verifica que el sistema de errores funciona."""
   
       def test_import_errors(self):
           from src.core.errors import (
               YeyoError, GPUError, IAError,
               MemoriaError, SecurityError, NodeError,
           )
           assert YeyoError is not None
   
       def test_all_inherit_from_yeyo_error(self):
           from src.core.errors import (
               YeyoError, GPUError, IAError,
               MemoriaError, SecurityError, NodeError,
           )
           assert issubclass(GPUError, YeyoError)
           assert issubclass(IAError, YeyoError)
           assert issubclass(MemoriaError, YeyoError)
           assert issubclass(SecurityError, YeyoError)
           assert issubclass(NodeError, YeyoError)
   
       def test_error_codes_unique(self):
           from src.core.errors import (
               GPUOutOfMemoryError, GPUSchedulerError,
               IATimeoutError, IAModelNotFoundError,
               MemoriaConnectionError, MemoriaCorruptionError,
               SecurityUnauthorizedError, SecuritySandboxViolationError,
               NodeCrashError, NodeContainerError,
           )
           errors = [
               GPUOutOfMemoryError(), GPUSchedulerError(),
               IATimeoutError(), IAModelNotFoundError(),
               MemoriaConnectionError(), MemoriaCorruptionError(),
               SecurityUnauthorizedError(), SecuritySandboxViolationError(),
               NodeCrashError(), NodeContainerError(),
           ]
           codes = [e.code for e in errors]
           assert len(codes) == len(set(codes))
   
       def test_security_not_recoverable(self):
           from src.core.errors import SecurityError
           err = SecurityError("test")
           assert err.recoverable is False
   
   
   # ============================================================
   # 1.11 — Logging System
   # ============================================================
   
   class TestLoggingSystem:
       """Verifica que el logging funciona."""
   
       def test_import_logger(self):
           from src.core.logger import YeyoLogger, JSONFormatter, redact_sensitive
           assert YeyoLogger is not None
   
       def test_redact_password(self):
           from src.core.logger import redact_sensitive, REDACTED
           result = redact_sensitive("password=secret123")
           assert "secret123" not in result
           assert REDACTED in result
   
       def test_json_output(self, tmp_path):
           from src.core.logger import YeyoLogger
           import logging
           log_dir = str(tmp_path / "logs")
           os.makedirs(log_dir, exist_ok=True)
           YeyoLogger.configure(log_dir=log_dir, log_level="DEBUG")
           logger = YeyoLogger.get_logger("yeyo.integration.test")
           # Verificar que no lanza excepción
           logger.info("Integration test log")
   
   
   # ============================================================
   # 1.12 — Health Check System
   # ============================================================
   
   class TestHealthCheckSystem:
       """Verifica que el Health Check funciona."""
   
       def test_import_health(self):
           from src.core.health import HealthChecker, ServiceCheck
           assert HealthChecker is not None
   
       @pytest.mark.asyncio
       async def test_health_check_structure(self):
           from src.core.health import HealthChecker
           checker = HealthChecker()
           result = await checker.check_all()
           assert "status" in result
           assert "services" in result
           assert "version" in result
           assert result["version"] == "0.1.0"
   
       @pytest.mark.asyncio
       async def test_health_cache(self):
           from src.core.health import HealthChecker
           checker = HealthChecker(cache_ttl_seconds=60)
           r1 = await checker.check_all()
           r2 = await checker.check_all()
           assert r1 is r2  # Cacheado
   
   
   # ============================================================
   # CROSS-CUTTING: Verificar integraciones entre componentes
   # ============================================================
   
   class TestCrossCutting:
       """Tests que verifican la integración entre componentes."""
   
       def test_factory_uses_config(self):
           """Factory debe usar valores de Config."""
           from src.core.factory import ProviderFactory
           from src.core.config import get_config
           ProviderFactory.reset()
           ProviderFactory._config = None
           config = get_config(
               database_url="postgresql://test@localhost/test",
               redis_url="redis://localhost:6379/0",
               ollama_model="custom-model:1b",
           )
           provider = ProviderFactory.get_ia_provider(config=config)
           assert provider.get_model_name() == "custom-model:1b"
           ProviderFactory.reset()
   
       def test_errors_can_be_serialized_to_json(self):
           """Errores deben poder serializarse para la API."""
           from src.core.errors import GPUOutOfMemoryError
           err = GPUOutOfMemoryError("No hay VRAM")
           d = err.to_dict()
           json_str = json.dumps(d)
           assert "GPU_OOM" in json_str
   
       @pytest.mark.asyncio
       async def test_event_bus_with_error_handling(self):
           """Event Bus debe manejar errores de suscriptores."""
           from src.core.event_bus import EventBus
           bus = EventBus()
           results = []
   
           async def good(data):
               results.append("ok")
   
           async def bad(data):
               raise RuntimeError("boom")
   
           bus.subscribe("test", bad)
           bus.subscribe("test", good)
           await bus.publish("test", None)
           assert "ok" in results
           bus.clear()

4. Agregar import os al inicio del archivo (necesario para TestLoggingSystem):

   Asegurar que al inicio del archivo está:
   import os
   (después de los otros imports)

5. Ejecutar TODA la suite de Capa 1:
   cd ~/yeyo-os
   source .venv/bin/activate
   
   # Primero los tests unitarios de cada micro-fase
   python -m pytest tests/unit/ -v --tb=short
   
   # Luego el test de integración de Capa 1
   python -m pytest tests/test_capa1_integration.py -v --tb=short

6. Verificar regresión de Capa 0 (si el archivo existe):
   python -m pytest tests/test_capa0_integration.py -v --tb=short 2>/dev/null || echo "Capa 0 tests no encontrados (OK si es primer setup)"

VERIFICAR:
- [ ] TODOS los tests unitarios pasan: `pytest tests/unit/ -v` → 0 failed
- [ ] Test de integración Capa 1 pasa: `pytest tests/test_capa1_integration.py -v` → 0 failed
- [ ] Capa 0 sigue pasando (regresión): `pytest tests/test_capa0_integration.py -v` → 0 failed
- [ ] IAProvider importable y abstracta
- [ ] OllamaProvider es instancia de IAProvider
- [ ] MemoriaProvider sin método delete
- [ ] TokenBudget total == 4000
- [ ] Config valida y carga correctamente
- [ ] Factory retorna singleton IAProvider
- [ ] API /health retorna 200
- [ ] WebSocket /ws funciona con echo
- [ ] GPU Scheduler preemption correcta
- [ ] Event Bus pub/sub funcional
- [ ] Errores con códigos únicos
- [ ] Logger output JSON con datos sensibles redactados
- [ ] HealthChecker retorna status correcto

RESULTADO ESPERADO:
tests/test_capa1_integration.py::TestIAProviderInterface::test_import_ia_interfaces PASSED
tests/test_capa1_integration.py::TestIAProviderInterface::test_ia_provider_is_abstract PASSED
tests/test_capa1_integration.py::TestIAProviderInterface::test_ia_provider_has_seven_methods PASSED
tests/test_capa1_integration.py::TestIAProviderInterface::test_ia_message_validates PASSED
tests/test_capa1_integration.py::TestIAProviderInterface::test_ia_response_has_fields PASSED
tests/test_capa1_integration.py::TestOllamaProvider::test_import_ollama_provider PASSED
tests/test_capa1_integration.py::TestOllamaProvider::test_ollama_is_ia_provider PASSED
tests/test_capa1_integration.py::TestOllamaProvider::test_ollama_default_model PASSED
tests/test_capa1_integration.py::TestOllamaProvider::test_ollama_max_tokens PASSED
tests/test_capa1_integration.py::TestMemoriaProviderInterface::test_import_memoria_interfaces PASSED
tests/test_capa1_integration.py::TestMemoriaProviderInterface::test_memoria_is_abstract PASSED
tests/test_capa1_integration.py::TestMemoriaProviderInterface::test_memoria_has_nine_methods PASSED
tests/test_capa1_integration.py::TestMemoriaProviderInterface::test_no_delete_method PASSED
tests/test_capa1_integration.py::TestMemoriaProviderInterface::test_memory_tiers PASSED
tests/test_capa1_integration.py::TestMemoriaProviderInterface::test_memory_types PASSED
tests/test_capa1_integration.py::TestOrquestadorInterface::test_import_orquestador PASSED
tests/test_capa1_integration.py::TestOrquestadorInterface::test_orquestador_is_abstract PASSED
tests/test_capa1_integration.py::TestOrquestadorInterface::test_token_budget_is_4000 PASSED
tests/test_capa1_integration.py::TestConfigSystem::test_import_config PASSED
tests/test_capa1_integration.py::TestConfigSystem::test_config_with_overrides PASSED
tests/test_capa1_integration.py::TestConfigSystem::test_token_budget_total PASSED
tests/test_capa1_integration.py::TestConfigSystem::test_gpu_available_vram PASSED
tests/test_capa1_integration.py::TestFactory::test_import_factory PASSED
tests/test_capa1_integration.py::TestFactory::test_factory_returns_ia_provider PASSED
tests/test_capa1_integration.py::TestFactory::test_factory_memoria_not_implemented PASSED
tests/test_capa1_integration.py::TestFactory::test_factory_singleton PASSED
tests/test_capa1_integration.py::TestAPIBase::test_import_app PASSED
tests/test_capa1_integration.py::TestAPIBase::test_health_endpoint PASSED
tests/test_capa1_integration.py::TestAPIBase::test_status_endpoint PASSED
tests/test_capa1_integration.py::TestAPIBase::test_cors_configured PASSED
tests/test_capa1_integration.py::TestWebSocket::test_import_connection_manager PASSED
tests/test_capa1_integration.py::TestWebSocket::test_connection_manager_defaults PASSED
tests/test_capa1_integration.py::TestWebSocket::test_websocket_echo PASSED
tests/test_capa1_integration.py::TestGPUScheduler::test_import_gpu_scheduler PASSED
tests/test_capa1_integration.py::TestGPUScheduler::test_gpu_scheduler_defaults PASSED
tests/test_capa1_integration.py::TestGPUScheduler::test_gpu_submit_and_release PASSED
tests/test_capa1_integration.py::TestGPUScheduler::test_gpu_preemption PASSED
tests/test_capa1_integration.py::TestEventBus::test_import_event_bus PASSED
tests/test_capa1_integration.py::TestEventBus::test_singleton PASSED
tests/test_capa1_integration.py::TestEventBus::test_pub_sub PASSED
tests/test_capa1_integration.py::TestErrorHandling::test_import_errors PASSED
tests/test_capa1_integration.py::TestErrorHandling::test_all_inherit_from_yeyo_error PASSED
tests/test_capa1_integration.py::TestErrorHandling::test_error_codes_unique PASSED
tests/test_capa1_integration.py::TestErrorHandling::test_security_not_recoverable PASSED
tests/test_capa1_integration.py::TestLoggingSystem::test_import_logger PASSED
tests/test_capa1_integration.py::TestLoggingSystem::test_redact_password PASSED
tests/test_capa1_integration.py::TestLoggingSystem::test_json_output PASSED
tests/test_capa1_integration.py::TestHealthCheckSystem::test_import_health PASSED
tests/test_capa1_integration.py::TestHealthCheckSystem::test_health_check_structure PASSED
tests/test_capa1_integration.py::TestHealthCheckSystem::test_health_cache PASSED
tests/test_capa1_integration.py::TestCrossCutting::test_factory_uses_config PASSED
tests/test_capa1_integration.py::TestCrossCutting::test_errors_can_be_serialized_to_json PASSED
tests/test_capa1_integration.py::TestCrossCutting::test_event_bus_with_error_handling PASSED

========================= 50 passed in Xs =========================

🚪 GATE FINAL CAPA 1: 50/50 tests passing. Esqueleto completo. Todas las interfaces definidas, config funcional, factory listo, API corriendo, GPU scheduler con prioridades, event bus pub/sub, errores jerárquicos, logging JSON, health checks. LISTO PARA CAPA 2.
```
