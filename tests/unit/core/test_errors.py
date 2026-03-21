"""Tests para Error Handling — Micro-fase 1.10"""

import pytest
from src.core.errors import (
    YeyoError, GPUError, GPUOutOfMemoryError, GPUSchedulerError,
    IAError, IATimeoutError, IAModelNotFoundError,
    MemoriaError, MemoriaConnectionError, MemoriaCorruptionError,
    SecurityError, SecurityUnauthorizedError, SecuritySandboxViolationError,
    NodeError, NodeCrashError, NodeContainerError,
)


class TestYeyoError:
    def test_create_with_message(self):
        err = YeyoError("test error")
        assert err.message == "test error"

    def test_default_code(self):
        assert YeyoError("test").code == "YEYO_ERROR"

    def test_default_recoverable(self):
        assert YeyoError("test").recoverable is True

    def test_custom_code(self):
        assert YeyoError("test", code="CUSTOM").code == "CUSTOM"

    def test_not_recoverable(self):
        assert YeyoError("fatal", recoverable=False).recoverable is False

    def test_str_representation(self):
        s = str(YeyoError("test error", code="TEST"))
        assert "TEST" in s and "test error" in s and "recoverable" in s

    def test_str_fatal(self):
        assert "FATAL" in str(YeyoError("fatal", code="FATAL", recoverable=False))

    def test_to_dict(self):
        d = YeyoError("test", code="TEST", recoverable=True).to_dict()
        assert d["error"] == "TEST"
        assert d["message"] == "test"
        assert d["recoverable"] is True
        assert d["type"] == "YeyoError"

    def test_is_exception(self):
        assert isinstance(YeyoError("test"), Exception)

    def test_can_be_raised_and_caught(self):
        with pytest.raises(YeyoError) as exc_info:
            raise YeyoError("test error")
        assert exc_info.value.message == "test error"


class TestInheritance:
    def test_gpu_error_inherits_yeyo(self):
        assert issubclass(GPUError, YeyoError)

    def test_gpu_oom_inherits_gpu(self):
        assert issubclass(GPUOutOfMemoryError, GPUError)

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
    def test_all_codes_unique(self):
        errors = [
            GPUOutOfMemoryError(), GPUSchedulerError(), IATimeoutError(),
            IAModelNotFoundError(), MemoriaConnectionError(), MemoriaCorruptionError(),
            SecurityUnauthorizedError(), SecuritySandboxViolationError(),
            NodeCrashError(), NodeContainerError(),
        ]
        codes = [e.code for e in errors]
        assert len(codes) == len(set(codes))

    def test_gpu_oom_code(self):
        assert GPUOutOfMemoryError().code == "GPU_OOM"

    def test_ia_timeout_code(self):
        assert IATimeoutError().code == "IA_TIMEOUT"

    def test_memory_corruption_code(self):
        assert MemoriaCorruptionError().code == "MEMORY_CORRUPTION"

    def test_security_sandbox_code(self):
        assert SecuritySandboxViolationError().code == "SECURITY_SANDBOX"


class TestRecoverability:
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
