"""
YeyoOS — Error Handling System
Micro-fase 1.10 — Capa 1: Esqueleto

Excepciones custom para cada subsistema de YeyoOS.
Todas heredan de YeyoError como base.
"""


class YeyoError(Exception):
    """Excepción base de YeyoOS."""

    def __init__(self, message: str, code: str = "YEYO_ERROR", recoverable: bool = True):
        self.message = message
        self.code = code
        self.recoverable = recoverable
        super().__init__(self.message)

    def __str__(self) -> str:
        status = "recoverable" if self.recoverable else "FATAL"
        return f"[{self.code}] {self.message} ({status})"

    def to_dict(self) -> dict:
        return {
            "error": self.code,
            "message": self.message,
            "recoverable": self.recoverable,
            "type": self.__class__.__name__,
        }


class GPUError(YeyoError):
    def __init__(self, message: str, code: str = "GPU_ERROR", recoverable: bool = True):
        super().__init__(message, code, recoverable)


class GPUOutOfMemoryError(GPUError):
    def __init__(self, message: str = "GPU out of memory"):
        super().__init__(message, code="GPU_OOM", recoverable=True)


class GPUSchedulerError(GPUError):
    def __init__(self, message: str = "GPU scheduler conflict"):
        super().__init__(message, code="GPU_SCHEDULER", recoverable=True)


class IAError(YeyoError):
    def __init__(self, message: str, code: str = "IA_ERROR", recoverable: bool = True):
        super().__init__(message, code, recoverable)


class IATimeoutError(IAError):
    def __init__(self, message: str = "IA provider timeout"):
        super().__init__(message, code="IA_TIMEOUT", recoverable=True)


class IAModelNotFoundError(IAError):
    def __init__(self, message: str = "IA model not found"):
        super().__init__(message, code="IA_MODEL_NOT_FOUND", recoverable=False)


class MemoriaError(YeyoError):
    def __init__(self, message: str, code: str = "MEMORY_ERROR", recoverable: bool = True):
        super().__init__(message, code, recoverable)


class MemoriaConnectionError(MemoriaError):
    def __init__(self, message: str = "Memory database connection failed"):
        super().__init__(message, code="MEMORY_CONNECTION", recoverable=True)


class MemoriaCorruptionError(MemoriaError):
    def __init__(self, message: str = "Memory corruption detected"):
        super().__init__(message, code="MEMORY_CORRUPTION", recoverable=False)


class SecurityError(YeyoError):
    def __init__(self, message: str, code: str = "SECURITY_ERROR", recoverable: bool = False):
        super().__init__(message, code, recoverable)


class SecurityUnauthorizedError(SecurityError):
    def __init__(self, message: str = "Unauthorized access"):
        super().__init__(message, code="SECURITY_UNAUTHORIZED", recoverable=False)


class SecuritySandboxViolationError(SecurityError):
    def __init__(self, message: str = "Sandbox violation detected"):
        super().__init__(message, code="SECURITY_SANDBOX", recoverable=False)


class NodeError(YeyoError):
    def __init__(self, message: str, code: str = "NODE_ERROR", recoverable: bool = True):
        super().__init__(message, code, recoverable)


class NodeCrashError(NodeError):
    def __init__(self, message: str = "Node crashed"):
        super().__init__(message, code="NODE_CRASH", recoverable=True)


class NodeContainerError(NodeError):
    def __init__(self, message: str = "Node container error"):
        super().__init__(message, code="NODE_CONTAINER", recoverable=True)
