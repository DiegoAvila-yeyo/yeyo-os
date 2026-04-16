"""
YeyoOS — Arena Sandbox
Isolated execution environment for attack/defense testing.
Uses tempdir + subprocess + timeout. NEVER touches the real system.
"""
import asyncio
import logging
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("yeyoos.arena.sandbox")

# Minimal test files copied into every sandbox so attacks have something to target.
_SANDBOX_SEED_FILES: dict[str, str] = {
    "app.py": (
        "from flask import Flask, request\n"
        "app = Flask(__name__)\n"
        "users = {'admin': 'password123'}\n\n"
        "@app.route('/login', methods=['POST'])\n"
        "def login():\n"
        "    user = request.form.get('user', '')\n"
        "    pw = request.form.get('pw', '')\n"
        "    # VULNERABLE: string concatenation SQL\n"
        "    query = f\"SELECT * FROM users WHERE name='{user}' AND pw='{pw}'\"\n"
        "    return query\n"
    ),
    "data.txt": "id,name,role\n1,admin,superuser\n2,guest,viewer\n",
    "config.env": "SECRET_KEY=super-secret-key-12345\nDATABASE_URL=sqlite:///db.sqlite\n",
}

# Environment variables explicitly REMOVED inside the sandbox.
_STRIPPED_ENV_VARS = [
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "DATABASE_URL",
    "SECRET_KEY",
    "API_KEY",
    "HOME",
    "SSH_AUTH_SOCK",
]


@dataclass
class SandboxResult:
    """Outcome of a single sandbox execution."""

    success: bool
    stdout: str
    stderr: str
    return_code: int
    duration_ms: float
    attack_succeeded: bool = False


class ArenaSandbox:
    """Isolated execution environment for attack / defense testing.

    Usage::

        async with ArenaSandbox(timeout=30) as sb:
            result = await sb.execute_attack(code, "sql_injection")
    """

    def __init__(self, timeout: int = 30) -> None:
        self.timeout = timeout
        self.temp_dir: Optional[str] = None

    # -- lifecycle --------------------------------------------------------

    async def setup(self) -> str:
        """Create a temporary directory and seed it with vulnerable test files."""
        self.temp_dir = tempfile.mkdtemp(prefix="yeyoos_arena_")
        for name, content in _SANDBOX_SEED_FILES.items():
            path = os.path.join(self.temp_dir, name)
            with open(path, "w") as fh:
                fh.write(content)
        logger.info("Sandbox created at %s", self.temp_dir)
        return self.temp_dir

    async def cleanup(self) -> None:
        """Remove the sandbox directory tree."""
        if self.temp_dir and os.path.isdir(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            logger.info("Sandbox cleaned up: %s", self.temp_dir)
            self.temp_dir = None

    async def __aenter__(self) -> "ArenaSandbox":
        await self.setup()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: ANN001
        await self.cleanup()

    # -- helpers ----------------------------------------------------------

    def _safe_env(self) -> dict[str, str]:
        """Return a sanitized copy of the current environment."""
        env = os.environ.copy()
        for key in _STRIPPED_ENV_VARS:
            env.pop(key, None)
        # Restrict PATH to basics
        env["PATH"] = "/usr/bin:/bin:/usr/local/bin"
        return env

    # -- execution --------------------------------------------------------

    async def execute_attack(self, code: str, attack_type: str) -> SandboxResult:
        """Run *code* inside the sandbox and determine if it 'succeeded'.

        The code is written to a temp file and executed as a subprocess with
        ``timeout`` seconds.  NEVER uses ``eval()`` / ``exec()`` in the
        main process.
        """
        if not self.temp_dir:
            raise RuntimeError("Sandbox not set up — call setup() or use as context manager.")

        script_path = os.path.join(self.temp_dir, "_attack.py")
        with open(script_path, "w") as fh:
            fh.write(code)

        start = time.perf_counter()
        try:
            proc = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    "python3",
                    script_path,
                    cwd=self.temp_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=self._safe_env(),
                ),
                timeout=self.timeout,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=self.timeout
            )
        except asyncio.TimeoutError:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.warning("Attack timed out after %d s (type=%s)", self.timeout, attack_type)
            return SandboxResult(
                success=False,
                stdout="",
                stderr="Execution timed out",
                return_code=-1,
                duration_ms=duration_ms,
                attack_succeeded=False,
            )
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.error("Sandbox execution error: %s", exc)
            return SandboxResult(
                success=False,
                stdout="",
                stderr=str(exc),
                return_code=-1,
                duration_ms=duration_ms,
                attack_succeeded=False,
            )

        duration_ms = (time.perf_counter() - start) * 1000
        stdout = stdout_bytes.decode(errors="replace")
        stderr = stderr_bytes.decode(errors="replace")
        return_code = proc.returncode or 0

        # Heuristic: attack "succeeded" if exit-code is 0 and stdout contains
        # keywords such as "ATTACK_SUCCESS" or "VULNERABLE".
        attack_succeeded = return_code == 0 and any(
            kw in stdout.upper() for kw in ("ATTACK_SUCCESS", "VULNERABLE", "EXPLOITED", "LEAKED")
        )

        return SandboxResult(
            success=True,
            stdout=stdout,
            stderr=stderr,
            return_code=return_code,
            duration_ms=duration_ms,
            attack_succeeded=attack_succeeded,
        )

    async def execute_defense(
        self, defense_code: str, attack_code: str
    ) -> SandboxResult:
        """Run *defense_code* then try *attack_code*.

        If the attack fails (non-zero exit or no success keywords) after the
        defense has been applied the defense is considered successful.
        """
        if not self.temp_dir:
            raise RuntimeError("Sandbox not set up — call setup() or use as context manager.")

        # Write combined script: defense first, then attack
        combined = (
            "# --- DEFENSE ---\n"
            f"{defense_code}\n\n"
            "# --- ATTACK ---\n"
            f"{attack_code}\n"
        )

        script_path = os.path.join(self.temp_dir, "_defense_test.py")
        with open(script_path, "w") as fh:
            fh.write(combined)

        start = time.perf_counter()
        try:
            proc = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    "python3",
                    script_path,
                    cwd=self.temp_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=self._safe_env(),
                ),
                timeout=self.timeout,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=self.timeout
            )
        except asyncio.TimeoutError:
            duration_ms = (time.perf_counter() - start) * 1000
            return SandboxResult(
                success=False,
                stdout="",
                stderr="Defense test timed out",
                return_code=-1,
                duration_ms=duration_ms,
                attack_succeeded=False,
            )
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            return SandboxResult(
                success=False, stdout="", stderr=str(exc),
                return_code=-1, duration_ms=duration_ms, attack_succeeded=False,
            )

        duration_ms = (time.perf_counter() - start) * 1000
        stdout = stdout_bytes.decode(errors="replace")
        stderr = stderr_bytes.decode(errors="replace")
        return_code = proc.returncode or 0

        attack_succeeded = return_code == 0 and any(
            kw in stdout.upper() for kw in ("ATTACK_SUCCESS", "VULNERABLE", "EXPLOITED", "LEAKED")
        )

        # For a defense result the semantics are inverted: success means the
        # defense blocked the attack.
        return SandboxResult(
            success=not attack_succeeded,
            stdout=stdout,
            stderr=stderr,
            return_code=return_code,
            duration_ms=duration_ms,
            attack_succeeded=attack_succeeded,
        )
