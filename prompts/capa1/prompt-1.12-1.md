## ═══════════════════════════════════════
## MICRO-FASE 1.12 — Health Check System
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 1.12-1 [VSCODE] — Sistema unificado de health checks

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 1.12: crear el sistema unificado de health checks que verifica TODOS los subsistemas.

CONTEXTO:
- Micro-fases 1.0-1.11 completadas: interfaces, config, factory, API, WebSocket, GPU Scheduler, Event Bus, Errors, Logger listos
- HealthChecker verifica: PostgreSQL, Redis, Ollama, GPU, Filesystem
- Estados: "healthy" (todo OK), "degraded" (1 servicio caído), "unhealthy" (2+ caídos)
- Timeout: máximo 5 segundos por servicio
- Cache: resultado se cachea 10 segundos (no re-chequear cada request)
- Versión: 0.1.0

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/core/health.py:

   Ruta: ~/yeyo-os/src/core/health.py
   Contenido:

   """
   YeyoOS — Health Check System
   Micro-fase 1.12 — Capa 1: Esqueleto
   
   Sistema unificado que verifica el estado de todos los subsistemas.
   
   Estados:
     healthy:   Todos los servicios funcionando
     degraded:  1 servicio caído (el sistema funciona con limitaciones)
     unhealthy: 2+ servicios caídos (el sistema no puede operar)
   
   Cache: resultado cacheado 10 segundos para evitar sobrecarga.
   Timeout: máximo 5 segundos por servicio.
   """
   
   import asyncio
   import time
   import os
   from typing import Any
   
   
   class ServiceCheck:
       """Resultado de check de un servicio individual."""
   
       def __init__(
           self,
           name: str,
           status: str = "unknown",
           latency_ms: float = 0.0,
           details: dict[str, Any] | None = None,
           error: str | None = None,
       ):
           self.name = name
           self.status = status  # "up" | "down" | "unknown"
           self.latency_ms = latency_ms
           self.details = details or {}
           self.error = error
   
       def to_dict(self) -> dict:
           result = {
               "status": self.status,
               "latency_ms": round(self.latency_ms, 2),
           }
           if self.details:
               result["details"] = self.details
           if self.error:
               result["error"] = self.error
           return result
   
   
   class HealthChecker:
       """Verificador unificado de salud del sistema."""
   
       def __init__(
           self,
           cache_ttl_seconds: float = 10.0,
           service_timeout_seconds: float = 5.0,
       ):
           self.cache_ttl = cache_ttl_seconds
           self.service_timeout = service_timeout_seconds
           self._cache: dict | None = None
           self._cache_time: float = 0.0
           self._start_time: float = time.time()
   
       def _is_cache_valid(self) -> bool:
           """Verifica si el cache es válido."""
           if self._cache is None:
               return False
           return (time.time() - self._cache_time) < self.cache_ttl
   
       async def check_all(self) -> dict:
           """
           Verifica todos los subsistemas.
           Retorna resultado cacheado si es válido.
           """
           if self._is_cache_valid():
               return self._cache
   
           checks = await asyncio.gather(
               self._check_service("postgresql", self._check_postgresql),
               self._check_service("redis", self._check_redis),
               self._check_service("ollama", self._check_ollama),
               self._check_service("gpu", self._check_gpu),
               self._check_service("filesystem", self._check_filesystem),
               return_exceptions=True,
           )
   
           services = {}
           for check in checks:
               if isinstance(check, ServiceCheck):
                   services[check.name] = check.to_dict()
               elif isinstance(check, Exception):
                   services["unknown"] = {"status": "down", "error": str(check)}
   
           down_count = sum(
               1 for s in services.values() if s.get("status") == "down"
           )
   
           if down_count == 0:
               overall_status = "healthy"
           elif down_count == 1:
               overall_status = "degraded"
           else:
               overall_status = "unhealthy"
   
           uptime = time.time() - self._start_time
   
           result = {
               "status": overall_status,
               "services": services,
               "uptime_seconds": round(uptime, 2),
               "version": "0.1.0",
               "checks_count": len(services),
               "down_count": down_count,
           }
   
           self._cache = result
           self._cache_time = time.time()
   
           return result
   
       async def _check_service(
           self, name: str, check_fn
       ) -> ServiceCheck:
           """Ejecuta un check con timeout."""
           start = time.monotonic()
           try:
               result = await asyncio.wait_for(
                   check_fn(),
                   timeout=self.service_timeout,
               )
               latency = (time.monotonic() - start) * 1000
               return ServiceCheck(
                   name=name,
                   status="up" if result else "down",
                   latency_ms=latency,
               )
           except asyncio.TimeoutError:
               latency = (time.monotonic() - start) * 1000
               return ServiceCheck(
                   name=name,
                   status="down",
                   latency_ms=latency,
                   error=f"Timeout after {self.service_timeout}s",
               )
           except Exception as e:
               latency = (time.monotonic() - start) * 1000
               return ServiceCheck(
                   name=name,
                   status="down",
                   latency_ms=latency,
                   error=str(e),
               )
   
       async def _check_postgresql(self) -> bool:
           """Verifica PostgreSQL. Implementación real en Capa 2."""
           # Stub: retorna False hasta que se conecte en Capa 2
           return False
   
       async def _check_redis(self) -> bool:
           """Verifica Redis. Implementación real en Capa 2."""
           return False
   
       async def _check_ollama(self) -> bool:
           """Verifica Ollama. Implementación real en Capa 2."""
           return False
   
       async def _check_gpu(self) -> bool:
           """Verifica GPU disponible."""
           # Stub básico: verifica si nvidia-smi existe
           return os.path.exists("/usr/bin/nvidia-smi") or os.path.exists(
               "/usr/local/bin/nvidia-smi"
           )
   
       async def _check_filesystem(self) -> bool:
           """Verifica filesystem base."""
           try:
               # Verifica que podemos escribir en directorio temporal
               test_file = "/tmp/yeyo_health_check"
               with open(test_file, "w") as f:
                   f.write("ok")
               os.remove(test_file)
               return True
           except Exception:
               return False
   
       def invalidate_cache(self) -> None:
           """Invalida el cache manualmente."""
           self._cache = None
           self._cache_time = 0.0

2. Crear archivo tests/unit/core/test_health.py:

   Ruta: ~/yeyo-os/tests/unit/core/test_health.py
   Contenido:

   """Tests para Health Check System — Micro-fase 1.12"""
   
   import pytest
   import asyncio
   import time
   from unittest.mock import AsyncMock, patch
   from src.core.health import HealthChecker, ServiceCheck
   
   
   @pytest.fixture
   def checker():
       return HealthChecker(cache_ttl_seconds=10.0, service_timeout_seconds=5.0)
   
   
   class TestServiceCheck:
       """Tests para ServiceCheck."""
   
       def test_create_service_check(self):
           sc = ServiceCheck(name="test", status="up", latency_ms=5.3)
           assert sc.name == "test"
           assert sc.status == "up"
           assert sc.latency_ms == 5.3
   
       def test_to_dict(self):
           sc = ServiceCheck(name="test", status="up", latency_ms=5.3)
           d = sc.to_dict()
           assert d["status"] == "up"
           assert d["latency_ms"] == 5.3
   
       def test_to_dict_with_error(self):
           sc = ServiceCheck(name="test", status="down", error="connection refused")
           d = sc.to_dict()
           assert d["error"] == "connection refused"
   
       def test_default_status_is_unknown(self):
           sc = ServiceCheck(name="test")
           assert sc.status == "unknown"
   
   
   class TestHealthChecker:
       """Tests para HealthChecker."""
   
       @pytest.mark.asyncio
       async def test_check_all_returns_dict(self, checker):
           result = await checker.check_all()
           assert isinstance(result, dict)
   
       @pytest.mark.asyncio
       async def test_check_all_has_required_fields(self, checker):
           result = await checker.check_all()
           assert "status" in result
           assert "services" in result
           assert "uptime_seconds" in result
           assert "version" in result
   
       @pytest.mark.asyncio
       async def test_version_is_correct(self, checker):
           result = await checker.check_all()
           assert result["version"] == "0.1.0"
   
       @pytest.mark.asyncio
       async def test_has_all_services(self, checker):
           result = await checker.check_all()
           services = result["services"]
           assert "postgresql" in services
           assert "redis" in services
           assert "ollama" in services
           assert "gpu" in services
           assert "filesystem" in services
   
       @pytest.mark.asyncio
       async def test_uptime_is_positive(self, checker):
           result = await checker.check_all()
           assert result["uptime_seconds"] >= 0
   
   
   class TestHealthStatus:
       """Tests para estado general del sistema."""
   
       @pytest.mark.asyncio
       async def test_all_down_is_unhealthy(self):
           checker = HealthChecker()
           checker._check_postgresql = AsyncMock(return_value=False)
           checker._check_redis = AsyncMock(return_value=False)
           checker._check_ollama = AsyncMock(return_value=False)
           checker._check_gpu = AsyncMock(return_value=False)
           checker._check_filesystem = AsyncMock(return_value=False)
           result = await checker.check_all()
           assert result["status"] == "unhealthy"
   
       @pytest.mark.asyncio
       async def test_all_up_is_healthy(self):
           checker = HealthChecker()
           checker._check_postgresql = AsyncMock(return_value=True)
           checker._check_redis = AsyncMock(return_value=True)
           checker._check_ollama = AsyncMock(return_value=True)
           checker._check_gpu = AsyncMock(return_value=True)
           checker._check_filesystem = AsyncMock(return_value=True)
           result = await checker.check_all()
           assert result["status"] == "healthy"
   
       @pytest.mark.asyncio
       async def test_one_down_is_degraded(self):
           checker = HealthChecker()
           checker._check_postgresql = AsyncMock(return_value=True)
           checker._check_redis = AsyncMock(return_value=False)  # Solo Redis caído
           checker._check_ollama = AsyncMock(return_value=True)
           checker._check_gpu = AsyncMock(return_value=True)
           checker._check_filesystem = AsyncMock(return_value=True)
           result = await checker.check_all()
           assert result["status"] == "degraded"
           assert result["down_count"] == 1
   
       @pytest.mark.asyncio
       async def test_two_down_is_unhealthy(self):
           checker = HealthChecker()
           checker._check_postgresql = AsyncMock(return_value=False)
           checker._check_redis = AsyncMock(return_value=False)
           checker._check_ollama = AsyncMock(return_value=True)
           checker._check_gpu = AsyncMock(return_value=True)
           checker._check_filesystem = AsyncMock(return_value=True)
           result = await checker.check_all()
           assert result["status"] == "unhealthy"
           assert result["down_count"] == 2
   
   
   class TestHealthCache:
       """Tests para caching de resultados."""
   
       @pytest.mark.asyncio
       async def test_cache_returns_same_result(self):
           checker = HealthChecker(cache_ttl_seconds=10.0)
           checker._check_postgresql = AsyncMock(return_value=True)
           checker._check_redis = AsyncMock(return_value=True)
           checker._check_ollama = AsyncMock(return_value=True)
           checker._check_gpu = AsyncMock(return_value=True)
           checker._check_filesystem = AsyncMock(return_value=True)
   
           result1 = await checker.check_all()
           result2 = await checker.check_all()
           assert result1 is result2  # Mismo objeto (cacheado)
   
       @pytest.mark.asyncio
       async def test_cache_expires(self):
           checker = HealthChecker(cache_ttl_seconds=0.1)  # 100ms TTL
           checker._check_postgresql = AsyncMock(return_value=True)
           checker._check_redis = AsyncMock(return_value=True)
           checker._check_ollama = AsyncMock(return_value=True)
           checker._check_gpu = AsyncMock(return_value=True)
           checker._check_filesystem = AsyncMock(return_value=True)
   
           result1 = await checker.check_all()
           await asyncio.sleep(0.15)  # Esperar a que expire
           result2 = await checker.check_all()
           assert result1 is not result2
   
       @pytest.mark.asyncio
       async def test_invalidate_cache(self):
           checker = HealthChecker(cache_ttl_seconds=60.0)
           checker._check_postgresql = AsyncMock(return_value=True)
           checker._check_redis = AsyncMock(return_value=True)
           checker._check_ollama = AsyncMock(return_value=True)
           checker._check_gpu = AsyncMock(return_value=True)
           checker._check_filesystem = AsyncMock(return_value=True)
   
           result1 = await checker.check_all()
           checker.invalidate_cache()
           result2 = await checker.check_all()
           assert result1 is not result2
   
   
   class TestHealthTimeout:
       """Tests para timeout por servicio."""
   
       @pytest.mark.asyncio
       async def test_slow_service_times_out(self):
           checker = HealthChecker(service_timeout_seconds=0.1)
   
           async def slow_check():
               await asyncio.sleep(5.0)  # Mucho más que el timeout
               return True
   
           checker._check_postgresql = slow_check
           checker._check_redis = AsyncMock(return_value=True)
           checker._check_ollama = AsyncMock(return_value=True)
           checker._check_gpu = AsyncMock(return_value=True)
           checker._check_filesystem = AsyncMock(return_value=True)
   
           result = await checker.check_all()
           pg = result["services"]["postgresql"]
           assert pg["status"] == "down"
           assert "Timeout" in pg.get("error", "")

3. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/core/test_health.py -v

VERIFICAR:
- [ ] Archivo src/core/health.py existe con HealthChecker y ServiceCheck
- [ ] TODOS los tests pasan (0 failed)
- [ ] Retorna estructura correcta: status, services, uptime, version
- [ ] "degraded" si 1 servicio caído
- [ ] "unhealthy" si 2+ servicios caídos
- [ ] "healthy" si todos funcionan
- [ ] Cache funciona (mismo resultado dentro de TTL)
- [ ] Cache expira después de TTL
- [ ] invalidate_cache() fuerza re-check
- [ ] Timeout de 5s por servicio
- [ ] Servicio lento marca como "down" con error de timeout

SI FALLA:
- asyncio.gather error: verificar que todos los checks son async
- AsyncMock error: requiere Python 3.8+
- Cache test timing: aumentar sleep si hay flakiness
- Timeout test: reducir el timeout para que el test sea rápido

NO HACER:
- No conectar a servicios reales (stubs hasta Capa 2)
- No agregar métricas detalladas de cada servicio
- No implementar alerting/notifications
- No hacer health checks recursivos

GATE: HealthChecker retorna estado correcto (healthy/degraded/unhealthy), cache funciona con TTL 10s, timeout 5s por servicio, todos los tests pasan.
```
