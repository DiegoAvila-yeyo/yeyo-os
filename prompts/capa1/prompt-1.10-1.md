## ═══════════════════════════════════════
## MICRO-FASE 1.10 — Error Handling
## Tipo: VSCODE | Prompts: 1 | Complejidad: Simple
## ═══════════════════════════════════════

### PROMPT 1.10-1 [VSCODE] — Sistema global de errores con excepciones custom

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 1.10: crear el sistema global de errores con excepciones custom y estrategia de recuperación.

CONTEXTO:
- Micro-fases 1.0-1.9 completadas: interfaces, config, factory, API, WebSocket, GPU Scheduler, Event Bus listos
- Excepciones custom para cada subsistema del OS
- Todas heredan de YeyoError (base)
- Cada error tiene: message, code (string único), recoverable (bool)
- recoverable=True → el sistema puede intentar recuperarse automáticamente
- recoverable=False → requiere intervención humana o restart

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/core/errors.py:

   Ruta: ~/yeyo-os/src/core/errors.py
   Contenido:

   """
   YeyoOS — Error Handling System
   Micro-fase 1.10 — Capa 1: Esqueleto
   
   Excepciones custom para cada subsistema de YeyoOS.
   Todas heredan de YeyoError como base.
   
   Cada error tiene:
   - message: descripción legible del error
   - code: código único para identificación (ej: "GPU_OOM")
   - recoverable: si el sistema puede intentar recuperarse
   """
   
   
   class YeyoError(Exception):
       """Excepción base de YeyoOS. Todas las excepciones del sistema heredan de esta."""
   
       def __init__(
           self,
           message: str,
           code: str = "YEYO_ERROR",
           recoverable: bool = True,
       ):
           self.message = message
           self.code = code
           self.recoverable = recoverable
           super().__init__(self.message)
   
       def __str__(self) -> str:
           status = "recoverable" if self.recoverable else "FATAL"
           return f"[{self.code}] {self.message} ({status})"
   
       def to_dict(self) -> dict:
           """Serializa el error a dict para APIs y logging."""
           return {
               "error": self.code,
               "message": self.message,
               "recoverable": self.recoverable,
               "type": self.__class__.__name__,
           }
   
   
   class GPUError(YeyoError):
       """Errores relacionados con GPU y VRAM."""
   
       def __init__(
           self,
           message: str,
           code: str = "GPU_ERROR",
           recoverable: bool = True,
       ):
           super().__init__(message, code, recoverable)
   
   
   class GPUOutOfMemoryError(GPUError):
       """GPU sin VRAM disponible."""
   
       def __init__(self, message: str = "GPU out of memory"):
           super().__init__(message, code="GPU_OOM", recoverable=True)
   
   
   class GPUSchedulerError(GPUError):
       """Error en el scheduler de GPU."""
   
       def __init__(self, message: str = "GPU scheduler conflict"):
           super().__init__(message, code="GPU_SCHEDULER", recoverable=True)
   
   
   class IAError(YeyoError):
       """Errores relacionados con el proveedor de IA."""
   
       def __init__(
           self,
           message: str,
           code: str = "IA_ERROR",
           recoverable: bool = True,
       ):
           super().__init__(message, code, recoverable)
   
   
   class IATimeoutError(IAError):
       """Timeout al llamar al proveedor de IA."""
   
       def __init__(self, message: str = "IA provider timeout"):
           super().__init__(message, code="IA_TIMEOUT", recoverable=True)
   
   
   class IAModelNotFoundError(IAError):
       """Modelo de IA no encontrado."""
   
       def __init__(self, message: str = "IA model not found"):
           super().__init__(message, code="IA_MODEL_NOT_FOUND", recoverable=False)
   
   
   class MemoriaError(YeyoError):
       """Errores relacionados con Flash Memory."""
   
       def __init__(
           self,
           message: str,
           code: str = "MEMORY_ERROR",
           recoverable: bool = True,
       ):
           super().__init__(message, code, recoverable)
   
   
   class MemoriaConnectionError(MemoriaError):
       """Error de conexión a PostgreSQL/pgvector."""
   
       def __init__(self, message: str = "Memory database connection failed"):
           super().__init__(message, code="MEMORY_CONNECTION", recoverable=True)
   
   
   class MemoriaCorruptionError(MemoriaError):
       """Corrupción detectada en memoria (checksum mismatch)."""
   
       def __init__(self, message: str = "Memory corruption detected"):
           super().__init__(message, code="MEMORY_CORRUPTION", recoverable=False)
   
   
   class SecurityError(YeyoError):
       """Errores de seguridad."""
   
       def __init__(
           self,
           message: str,
           code: str = "SECURITY_ERROR",
           recoverable: bool = False,
       ):
           # Security errors son NOT recoverable por defecto
           super().__init__(message, code, recoverable)
   
   
   class SecurityUnauthorizedError(SecurityError):
       """Acceso no autorizado."""
   
       def __init__(self, message: str = "Unauthorized access"):
           super().__init__(message, code="SECURITY_UNAUTHORIZED", recoverable=False)
   
   
   class SecuritySandboxViolationError(SecurityError):
       """Violación de sandbox de un nodo."""
   
       def __init__(self, message: str = "Sandbox violation detected"):
           super().__init__(message, code="SECURITY_SANDBOX", recoverable=False)
   
   
   class NodeError(YeyoError):
       """Errores relacionados con nodos del hub."""
   
       def __init__(
           self,
           message: str,
           code: str = "NODE_ERROR",
           recoverable: bool = True,
       ):
           super().__init__(message, code, recoverable)
   
   
   class NodeCrashError(NodeError):
       """Crash de un nodo."""
   
       def __init__(self, message: str = "Node crashed"):
           super().__init__(message, code="NODE_CRASH", recoverable=True)
   
   
   class NodeContainerError(NodeError):
       """Error de contenedor Podman de un nodo."""
   
       def __init__(self, message: str = "Node container error"):
           super().__init__(message, code="NODE_CONTAINER", recoverable=True)

2. Crear archivo tests/unit/core/test_errors.py:

   Ruta: ~/yeyo-os/tests/unit/core/test_errors.py
   Contenido:

   """Tests para Error Handling — Micro-fase 1.10"""
   
   import pytest
   from src.core.errors import (
       YeyoError,
       GPUError,
       GPUOutOfMemoryError,
       GPUSchedulerError,
       IAError,
       IATimeoutError,
       IAModelNotFoundError,
       MemoriaError,
       MemoriaConnectionError,
       MemoriaCorruptionError,
       SecurityError,
       SecurityUnauthorizedError,
       SecuritySandboxViolationError,
       NodeError,
       NodeCrashError,
       NodeContainerError,
   )
   
   
   class TestYeyoError:
       """Tests para la excepción base."""
   
       def test_create_with_message(self):
           err = YeyoError("test error")
           assert err.message == "test error"
   
       def test_default_code(self):
           err = YeyoError("test")
           assert err.code == "YEYO_ERROR"
   
       def test_default_recoverable(self):
           err = YeyoError("test")
           assert err.recoverable is True
   
       def test_custom_code(self):
           err = YeyoError("test", code="CUSTOM")
           assert err.code == "CUSTOM"
   
       def test_not_recoverable(self):
           err = YeyoError("fatal", recoverable=False)
           assert err.recoverable is False
   
       def test_str_representation(self):
           err = YeyoError("test error", code="TEST")
           s = str(err)
           assert "TEST" in s
           assert "test error" in s
           assert "recoverable" in s
   
       def test_str_fatal(self):
           err = YeyoError("fatal", code="FATAL", recoverable=False)
           assert "FATAL" in str(err)
   
       def test_to_dict(self):
           err = YeyoError("test", code="TEST", recoverable=True)
           d = err.to_dict()
           assert d["error"] == "TEST"
           assert d["message"] == "test"
           assert d["recoverable"] is True
           assert d["type"] == "YeyoError"
   
       def test_is_exception(self):
           err = YeyoError("test")
           assert isinstance(err, Exception)
   
       def test_can_be_raised_and_caught(self):
           with pytest.raises(YeyoError) as exc_info:
               raise YeyoError("test error")
           assert exc_info.value.message == "test error"
   
   
   class TestInheritance:
       """Tests para herencia de excepciones."""
   
       def test_gpu_error_inherits_yeyo(self):
           assert issubclass(GPUError, YeyoError)
   
       def test_gpu_oom_inherits_gpu(self):
           assert issubclass(GPUOutOfMemoryError, GPUError)
   
       def test_gpu_scheduler_inherits_gpu(self):
           assert issubclass(GPUSchedulerError, GPUError)
   
       def test_ia_error_inherits_yeyo(self):
           assert issubclass(IAError, YeyoError)
   
       def test_ia_timeout_inherits_ia(self):
           assert issubclass(IATimeoutError, IAError)
   
       def test_ia_model_not_found_inherits_ia(self):
           assert issubclass(IAModelNotFoundError, IAError)
   
       def test_memoria_error_inherits_yeyo(self):
           assert issubclass(MemoriaError, YeyoError)
   
       def test_memoria_connection_inherits_memoria(self):
           assert issubclass(MemoriaConnectionError, MemoriaError)
   
       def test_memoria_corruption_inherits_memoria(self):
           assert issubclass(MemoriaCorruptionError, MemoriaError)
   
       def test_security_error_inherits_yeyo(self):
           assert issubclass(SecurityError, YeyoError)
   
       def test_security_unauthorized_inherits_security(self):
           assert issubclass(SecurityUnauthorizedError, SecurityError)
   
       def test_security_sandbox_inherits_security(self):
           assert issubclass(SecuritySandboxViolationError, SecurityError)
   
       def test_node_error_inherits_yeyo(self):
           assert issubclass(NodeError, YeyoError)
   
       def test_node_crash_inherits_node(self):
           assert issubclass(NodeCrashError, NodeError)
   
       def test_node_container_inherits_node(self):
           assert issubclass(NodeContainerError, NodeError)
   
   
   class TestErrorCodes:
       """Tests para códigos de error únicos."""
   
       def test_all_codes_unique(self):
           errors = [
               GPUOutOfMemoryError(),
               GPUSchedulerError(),
               IATimeoutError(),
               IAModelNotFoundError(),
               MemoriaConnectionError(),
               MemoriaCorruptionError(),
               SecurityUnauthorizedError(),
               SecuritySandboxViolationError(),
               NodeCrashError(),
               NodeContainerError(),
           ]
           codes = [e.code for e in errors]
           assert len(codes) == len(set(codes)), f"Códigos duplicados: {codes}"
   
       def test_gpu_oom_code(self):
           assert GPUOutOfMemoryError().code == "GPU_OOM"
   
       def test_ia_timeout_code(self):
           assert IATimeoutError().code == "IA_TIMEOUT"
   
       def test_memory_corruption_code(self):
           assert MemoriaCorruptionError().code == "MEMORY_CORRUPTION"
   
       def test_security_sandbox_code(self):
           assert SecuritySandboxViolationError().code == "SECURITY_SANDBOX"
   
   
   class TestRecoverability:
       """Tests para el flag recoverable."""
   
       def test_gpu_oom_recoverable(self):
           assert GPUOutOfMemoryError().recoverable is True
   
       def test_ia_timeout_recoverable(self):
           assert IATimeoutError().recoverable is True
   
       def test_ia_model_not_found_not_recoverable(self):
           assert IAModelNotFoundError().recoverable is False
   
       def test_memory_connection_recoverable(self):
           assert MemoriaConnectionError().recoverable is True
   
       def test_memory_corruption_not_recoverable(self):
           assert MemoriaCorruptionError().recoverable is False
   
       def test_security_not_recoverable_by_default(self):
           assert SecurityError("test").recoverable is False
   
       def test_security_unauthorized_not_recoverable(self):
           assert SecurityUnauthorizedError().recoverable is False
   
       def test_node_crash_recoverable(self):
           assert NodeCrashError().recoverable is True
   
   
   class TestCatchHierarchy:
       """Tests para captura jerárquica de excepciones."""
   
       def test_catch_gpu_error_catches_oom(self):
           with pytest.raises(GPUError):
               raise GPUOutOfMemoryError()
   
       def test_catch_yeyo_error_catches_all(self):
           with pytest.raises(YeyoError):
               raise SecuritySandboxViolationError()
   
       def test_catch_ia_error_catches_timeout(self):
           with pytest.raises(IAError):
               raise IATimeoutError()
   
       def test_catch_exception_catches_yeyo(self):
           with pytest.raises(Exception):
               raise YeyoError("test")

3. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/core/test_errors.py -v

VERIFICAR:
- [ ] Archivo src/core/errors.py existe con todas las excepciones
- [ ] TODOS los tests pasan (0 failed)
- [ ] Todas heredan de YeyoError
- [ ] Códigos de error son únicos
- [ ] recoverable flag funciona correctamente
- [ ] Security errors son NOT recoverable por defecto
- [ ] to_dict() serializa correctamente
- [ ] str() muestra código, mensaje, y estado
- [ ] Jerarquía de excepciones permite captura a cualquier nivel

SI FALLA:
- Import error: verificar que src/core/__init__.py existe
- Herencia error: verificar que todas llaman a super().__init__()

NO HACER:
- No implementar error recovery automático (eso es Capa 2+)
- No conectar con logging system todavía
- No agregar error tracking/telemetry
- No crear excepciones para funcionalidad que no existe aún

GATE: Todas las excepciones heredan de YeyoError, códigos únicos, recoverable flag correcto, jerarquía de captura funciona, todos los tests pasan.
```
