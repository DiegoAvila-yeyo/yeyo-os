"""
YeyoOS — Code Sandbox (Ephemeral Execution)
Micro-fase 5.8 — Capa 5: Órganos

Ejecución segura de código en container efímero.
REGLAS: Sin red, 30s timeout, 256MB RAM, auto-destrucción.
"""

import asyncio
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


# Patrones peligrosos por lenguaje
DANGEROUS_PATTERNS = {
    "python": [
        r"\bos\.system\b", r"\bsubprocess\b", r"\b__import__\b",
        r"\beval\b", r"\bexec\b", r"\bopen\b\s*\(\s*['\"]\/etc",
        r"\bsocket\b", r"\brequests\b", r"\burllib\b",
        r"\bshutil\.rmtree\b", r"\bos\.remove\b",
    ],
    "javascript": [
        r"\bchild_process\b", r"\bexec\b", r"\bspawn\b",
        r"\brequire\s*\(\s*['\"]fs['\"]", r"\bprocess\.env\b",
        r"\bfetch\b", r"\bhttp\b",
    ],
    "bash": [
        r"\brm\s+-rf\b", r"\bcurl\b", r"\bwget\b",
        r"\bnc\b", r"\bsudo\b", r"\bchmod\b",
        r"\b>/dev/", r"\bdd\b\s+if=",
    ],
}

SANDBOX_CONFIG = {
    "network": "none",
    "timeout_seconds": 30,
    "memory_mb": 256,
    "cpu_cores": 0.5,
    "tmp_size_mb": 50,
    "max_output_bytes": 10240,  # 10KB
}

SUPPORTED_RUNTIMES = {
    "python": {"image": "python:3.11-slim", "cmd": "python3"},
    "javascript": {"image": "node:20-slim", "cmd": "node"},
    "bash": {"image": "alpine:latest", "cmd": "sh"},
}


@dataclass
class SandboxResult:
    """Resultado de ejecución en sandbox."""
    stdout: str
    stderr: str
    exit_code: int
    execution_time_ms: float
    timed_out: bool = False
    memory_exceeded: bool = False


class CodeSandbox:
    """
    Sandbox efímero para ejecución de código.
    Sin red, timeout 30s, 256MB RAM, auto-destrucción.
    """

    def check_dangerous_code(self, code: str, language: str) -> Optional[str]:
        """
        Verifica código contra patrones peligrosos.
        Retorna razón si es peligroso, None si es seguro.
        """
        patterns = DANGEROUS_PATTERNS.get(language, [])
        for pattern in patterns:
            if re.search(pattern, code):
                return f"Código contiene patrón peligroso: {pattern}"
        return None

    async def execute(self, code: str, language: str) -> SandboxResult:
        """
        Ejecuta código en container efímero.
        FLUJO: check seguridad → crear container → ejecutar → capturar → destruir
        """
        # 1. Verificar seguridad
        danger = self.check_dangerous_code(code, language)
        if danger:
            return SandboxResult(
                stdout="",
                stderr=f"BLOCKED: {danger}",
                exit_code=-1,
                execution_time_ms=0,
            )

        if language not in SUPPORTED_RUNTIMES:
            return SandboxResult(
                stdout="",
                stderr=f"Lenguaje no soportado: {language}",
                exit_code=-1,
                execution_time_ms=0,
            )

        runtime = SUPPORTED_RUNTIMES[language]
        start_time = datetime.now(timezone.utc)

        try:
            # Ejecutar en container con Podman
            result = await self._run_in_container(
                code=code,
                image=runtime["image"],
                cmd=runtime["cmd"],
            )
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            result.execution_time_ms = elapsed
            return result

        except asyncio.TimeoutError:
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            return SandboxResult(
                stdout="",
                stderr="TIMEOUT: Ejecución excedió 30 segundos",
                exit_code=-1,
                execution_time_ms=elapsed,
                timed_out=True,
            )

    async def _run_in_container(
        self, code: str, image: str, cmd: str
    ) -> SandboxResult:
        """Ejecuta código en container Podman efímero."""
        container_cmd = [
            "podman", "run", "--rm",
            "--network=none",
            f"--memory={SANDBOX_CONFIG['memory_mb']}m",
            f"--cpus={SANDBOX_CONFIG['cpu_cores']}",
            "--read-only",
            "--tmpfs", f"/tmp:size={SANDBOX_CONFIG['tmp_size_mb']}m",
            "--no-new-privileges",
            "--security-opt=no-new-privileges:true",
            image,
            cmd, "-c", code,
        ]

        process = await asyncio.create_subprocess_exec(
            *container_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=SANDBOX_CONFIG["timeout_seconds"],
        )

        # Truncar output a max_output_bytes
        max_bytes = SANDBOX_CONFIG["max_output_bytes"]
        stdout_str = stdout.decode("utf-8", errors="replace")[:max_bytes]
        stderr_str = stderr.decode("utf-8", errors="replace")[:max_bytes]

        return SandboxResult(
            stdout=stdout_str,
            stderr=stderr_str,
            exit_code=process.returncode or 0,
            execution_time_ms=0,
        )
