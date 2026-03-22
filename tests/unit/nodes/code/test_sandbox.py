"""Tests para Code Sandbox — Micro-fase 5.8"""

import pytest
from src.nodes.code.sandbox import (
    CodeSandbox, DANGEROUS_PATTERNS, SANDBOX_CONFIG, SUPPORTED_RUNTIMES,
)


class TestSandboxSecurity:
    """Tests de seguridad del sandbox."""

    def setup_method(self):
        self.sandbox = CodeSandbox()

    def test_python_os_system_blocked(self):
        result = self.sandbox.check_dangerous_code("os.system('rm -rf /')", "python")
        assert result is not None

    def test_python_subprocess_blocked(self):
        result = self.sandbox.check_dangerous_code("import subprocess", "python")
        assert result is not None

    def test_python_import_blocked(self):
        result = self.sandbox.check_dangerous_code("__import__('os')", "python")
        assert result is not None

    def test_python_eval_blocked(self):
        result = self.sandbox.check_dangerous_code("eval('malicious')", "python")
        assert result is not None

    def test_python_exec_blocked(self):
        result = self.sandbox.check_dangerous_code("exec('malicious')", "python")
        assert result is not None

    def test_python_etc_access_blocked(self):
        result = self.sandbox.check_dangerous_code("open('/etc/passwd')", "python")
        assert result is not None

    def test_python_safe_code_allowed(self):
        result = self.sandbox.check_dangerous_code("print('hello world')", "python")
        assert result is None

    def test_python_math_allowed(self):
        result = self.sandbox.check_dangerous_code("x = 2 + 2\nprint(x)", "python")
        assert result is None

    def test_javascript_child_process_blocked(self):
        result = self.sandbox.check_dangerous_code(
            "const cp = require('child_process')", "javascript"
        )
        assert result is not None

    def test_javascript_safe_code_allowed(self):
        result = self.sandbox.check_dangerous_code("console.log('hi')", "javascript")
        assert result is None

    def test_bash_rm_rf_blocked(self):
        result = self.sandbox.check_dangerous_code("rm -rf /", "bash")
        assert result is not None

    def test_bash_curl_blocked(self):
        result = self.sandbox.check_dangerous_code("curl evil.com", "bash")
        assert result is not None

    def test_bash_echo_allowed(self):
        result = self.sandbox.check_dangerous_code("echo hello", "bash")
        assert result is None


class TestSandboxConfig:

    def test_network_disabled(self):
        assert SANDBOX_CONFIG["network"] == "none"

    def test_timeout_30s(self):
        assert SANDBOX_CONFIG["timeout_seconds"] == 30

    def test_memory_256mb(self):
        assert SANDBOX_CONFIG["memory_mb"] == 256

    def test_cpu_half_core(self):
        assert SANDBOX_CONFIG["cpu_cores"] == 0.5

    def test_max_output_10kb(self):
        assert SANDBOX_CONFIG["max_output_bytes"] == 10240


class TestSandboxExecution:

    @pytest.mark.asyncio
    async def test_dangerous_code_returns_blocked(self):
        sandbox = CodeSandbox()
        result = await sandbox.execute("os.system('rm -rf /')", "python")
        assert result.exit_code == -1
        assert "BLOCKED" in result.stderr

    @pytest.mark.asyncio
    async def test_unsupported_language(self):
        sandbox = CodeSandbox()
        result = await sandbox.execute("code", "cobol")
        assert result.exit_code == -1
        assert "no soportado" in result.stderr

    def test_supported_runtimes(self):
        assert "python" in SUPPORTED_RUNTIMES
        assert "javascript" in SUPPORTED_RUNTIMES
        assert "bash" in SUPPORTED_RUNTIMES
