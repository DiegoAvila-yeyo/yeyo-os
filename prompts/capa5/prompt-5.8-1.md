## ═══════════════════════════════════════
## MICRO-FASE 5.8 — Code Node (Sandbox Execution)
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 5.8-1 [VSCODE] — Ejecución de código en sandbox aislado

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 5.8 de Capa 5 (Órganos): crear el sandbox de ejecución de código en container efímero aislado.

CONTEXTO:
- Micro-fase 5.7 completada: CodeNode con Monaco editor y asistencia IA
- Sandbox = container efímero: se crea, ejecuta código, se DESTRUYE
- SEGURIDAD CRÍTICA:
  - NO network access (--network=none)
  - 30 segundos timeout
  - 256MB RAM máximo
  - Solo soporta: Python, JavaScript, Bash
  - NO acceso a filesystem fuera de /tmp
  - Container auto-destruido después de ejecución
- Output capturado: stdout, stderr, exit code
- Hardware: GTX 1060 3GB VRAM, 16GB RAM

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/nodes/code/sandbox.py:

   Ruta: ~/yeyo-os/src/nodes/code/sandbox.py
   Contenido:

   """
   YeyoOS — Code Sandbox (Ephemeral Container)
   Micro-fase 5.8 — Capa 5: Órganos

   SEGURIDAD CRÍTICA:
   - Container efímero: crear → ejecutar → DESTRUIR
   - SIN acceso a red (--network=none)
   - Timeout: 30 segundos
   - RAM: 256MB máximo
   - Solo: Python, JavaScript, Bash
   - Sin filesystem fuera de /tmp
   """

   import uuid
   import asyncio
   from datetime import datetime, timezone
   from typing import Optional
   from dataclasses import dataclass, field


   SUPPORTED_SANDBOX_LANGUAGES = {
       "python": {
           "image": "python:3.11-slim",
           "command": "python3 -c",
           "file_ext": ".py",
       },
       "javascript": {
           "image": "node:20-slim",
           "command": "node -e",
           "file_ext": ".js",
       },
       "bash": {
           "image": "alpine:3.18",
           "command": "sh -c",
           "file_ext": ".sh",
       },
   }

   SANDBOX_TIMEOUT = 30  # segundos
   SANDBOX_MEMORY = "256m"  # 256MB máximo
   SANDBOX_CPU = "0.5"  # medio CPU


   @dataclass
   class SandboxResult:
       """Resultado de ejecución en sandbox."""
       id: str
       language: str
       stdout: str
       stderr: str
       exit_code: int
       execution_time_ms: float
       timed_out: bool = False
       created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


   class CodeSandbox:
       """
       Sandbox de ejecución de código en container efímero.
       SEGURIDAD: sin red, timeout 30s, 256MB RAM, auto-destruido.
       """

       async def execute(self, code: str, language: str) -> SandboxResult:
           """
           Ejecuta código en sandbox aislado.
           FLUJO:
           1. Valida lenguaje soportado
           2. Crea container efímero (Podman)
           3. Ejecuta código con timeout
           4. Captura output
           5. DESTRUYE container
           """
           result_id = f"sandbox-{uuid.uuid4().hex[:8]}"

           if language not in SUPPORTED_SANDBOX_LANGUAGES:
               return SandboxResult(
                   id=result_id,
                   language=language,
                   stdout="",
                   stderr=f"Lenguaje no soportado: {language}. "
                          f"Soportados: {list(SUPPORTED_SANDBOX_LANGUAGES.keys())}",
                   exit_code=1,
                   execution_time_ms=0,
               )

           # Validar código peligroso
           danger_check = self._check_dangerous_code(code, language)
           if danger_check:
               return SandboxResult(
                   id=result_id,
                   language=language,
                   stdout="",
                   stderr=f"Código bloqueado por seguridad: {danger_check}",
                   exit_code=1,
                   execution_time_ms=0,
               )

           lang_config = SUPPORTED_SANDBOX_LANGUAGES[language]
           container_name = f"yeyo-sandbox-{uuid.uuid4().hex[:8]}"

           start_time = datetime.now(timezone.utc)

           try:
               result = await self._run_in_container(
                   container_name=container_name,
                   image=lang_config["image"],
                   command=lang_config["command"],
                   code=code,
               )

               elapsed = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

               return SandboxResult(
                   id=result_id,
                   language=language,
                   stdout=result["stdout"],
                   stderr=result["stderr"],
                   exit_code=result["exit_code"],
                   execution_time_ms=elapsed,
                   timed_out=result.get("timed_out", False),
               )

           finally:
               # SIEMPRE destruir el container
               await self._destroy_container(container_name)

       async def _run_in_container(
           self, container_name: str, image: str, command: str, code: str
       ) -> dict:
           """Ejecuta código dentro de un container Podman efímero."""
           # Escapar código para shell
           escaped_code = code.replace("'", "'\\''")

           podman_cmd = [
               "podman", "run",
               "--rm",                         # Auto-remove on exit
               "--name", container_name,
               "--network=none",               # SIN RED
               "--memory", SANDBOX_MEMORY,      # 256MB max
               "--cpus", SANDBOX_CPU,           # Medio CPU
               "--read-only",                   # Filesystem read-only
               "--tmpfs", "/tmp:rw,size=50m",   # Solo /tmp writable (50MB)
               "--no-new-privileges",           # Sin escalamiento
               "--cap-drop=ALL",                # Sin capabilities
               "--security-opt=no-new-privileges:true",
               "--pids-limit=50",               # Max 50 procesos
               image,
               "sh", "-c", f"{command} '{escaped_code}'",
           ]

           try:
               process = await asyncio.create_subprocess_exec(
                   *podman_cmd,
                   stdout=asyncio.subprocess.PIPE,
                   stderr=asyncio.subprocess.PIPE,
               )

               stdout, stderr = await asyncio.wait_for(
                   process.communicate(),
                   timeout=SANDBOX_TIMEOUT,
               )

               return {
                   "stdout": stdout.decode("utf-8", errors="replace")[:10000],
                   "stderr": stderr.decode("utf-8", errors="replace")[:10000],
                   "exit_code": process.returncode or 0,
                   "timed_out": False,
               }

           except asyncio.TimeoutError:
               # Matar proceso si timeout
               try:
                   process.kill()
               except Exception:
                   pass
               return {
                   "stdout": "",
                   "stderr": f"Timeout: ejecución excedió {SANDBOX_TIMEOUT} segundos",
                   "exit_code": 124,
                   "timed_out": True,
               }

       async def _destroy_container(self, container_name: str) -> None:
           """Destruye container por nombre (forzado)."""
           try:
               process = await asyncio.create_subprocess_exec(
                   "podman", "rm", "-f", container_name,
                   stdout=asyncio.subprocess.PIPE,
                   stderr=asyncio.subprocess.PIPE,
               )
               await asyncio.wait_for(process.communicate(), timeout=10)
           except Exception:
               pass  # Best effort

       def _check_dangerous_code(self, code: str, language: str) -> Optional[str]:
           """Verifica patrones peligrosos en el código."""
           import re

           dangerous_patterns = [
               (r"import\s+os\b.*\bsystem\b", "os.system() no permitido"),
               (r"import\s+subprocess", "subprocess no permitido"),
               (r"__import__", "__import__ no permitido"),
               (r"eval\s*\(.*exec", "eval/exec anidados no permitidos"),
               (r"open\s*\(.*/etc/", "acceso a /etc/ no permitido"),
               (r"open\s*\(.*/proc/", "acceso a /proc/ no permitido"),
           ]

           for pattern, reason in dangerous_patterns:
               if re.search(pattern, code, re.IGNORECASE | re.DOTALL):
                   return reason

           return None

2. Actualizar src/nodes/code/__init__.py:

   Ruta: ~/yeyo-os/src/nodes/code/__init__.py
   Contenido:
   from .service import CodeNode
   from .sandbox import CodeSandbox, SandboxResult

3. Crear archivo tests/unit/nodes/code/test_sandbox.py:

   Ruta: ~/yeyo-os/tests/unit/nodes/code/test_sandbox.py
   Contenido:

   """Tests para Code Sandbox — Micro-fase 5.8"""

   import pytest
   from unittest.mock import AsyncMock, patch, MagicMock
   from src.nodes.code.sandbox import (
       CodeSandbox, SandboxResult,
       SUPPORTED_SANDBOX_LANGUAGES, SANDBOX_TIMEOUT, SANDBOX_MEMORY,
   )


   class TestSandboxSecurity:
       """Tests de seguridad del sandbox."""

       def test_timeout_is_30_seconds(self):
           assert SANDBOX_TIMEOUT == 30

       def test_memory_is_256mb(self):
           assert SANDBOX_MEMORY == "256m"

       def test_only_three_languages(self):
           assert set(SUPPORTED_SANDBOX_LANGUAGES.keys()) == {
               "python", "javascript", "bash"
           }

       @pytest.mark.asyncio
       async def test_unsupported_language_rejected(self):
           sandbox = CodeSandbox()
           result = await sandbox.execute("code", "ruby")
           assert result.exit_code == 1
           assert "no soportado" in result.stderr.lower()

       def test_dangerous_os_system_blocked(self):
           sandbox = CodeSandbox()
           result = sandbox._check_dangerous_code(
               "import os\nos.system('rm -rf /')", "python"
           )
           assert result is not None

       def test_dangerous_subprocess_blocked(self):
           sandbox = CodeSandbox()
           result = sandbox._check_dangerous_code(
               "import subprocess\nsubprocess.run(['ls'])", "python"
           )
           assert result is not None

       def test_dangerous_import_blocked(self):
           sandbox = CodeSandbox()
           result = sandbox._check_dangerous_code(
               "__import__('os').system('whoami')", "python"
           )
           assert result is not None

       def test_safe_code_allowed(self):
           sandbox = CodeSandbox()
           result = sandbox._check_dangerous_code(
               "print('Hello World')", "python"
           )
           assert result is None

       def test_safe_math_allowed(self):
           sandbox = CodeSandbox()
           result = sandbox._check_dangerous_code(
               "x = sum(range(100))\nprint(x)", "python"
           )
           assert result is None


   class TestSandboxExecution:
       """Tests de ejecución (con mocks de Podman)."""

       @pytest.mark.asyncio
       async def test_python_execution_returns_result(self):
           sandbox = CodeSandbox()
           mock_process = MagicMock()
           mock_process.communicate = AsyncMock(
               return_value=(b"42\n", b"")
           )
           mock_process.returncode = 0
           mock_process.kill = MagicMock()

           with patch("asyncio.create_subprocess_exec", return_value=mock_process):
               result = await sandbox.execute("print(42)", "python")
               assert result.stdout.strip() == "42"
               assert result.exit_code == 0
               assert result.timed_out is False

       @pytest.mark.asyncio
       async def test_container_destroyed_after_execution(self):
           sandbox = CodeSandbox()
           sandbox._run_in_container = AsyncMock(return_value={
               "stdout": "ok", "stderr": "", "exit_code": 0
           })
           sandbox._destroy_container = AsyncMock()

           result = await sandbox.execute("print('hi')", "python")
           sandbox._destroy_container.assert_called_once()

       @pytest.mark.asyncio
       async def test_container_destroyed_on_error(self):
           sandbox = CodeSandbox()
           sandbox._run_in_container = AsyncMock(
               side_effect=RuntimeError("container error")
           )
           sandbox._destroy_container = AsyncMock()

           with pytest.raises(RuntimeError):
               await sandbox.execute("print('hi')", "python")
           sandbox._destroy_container.assert_called_once()

       @pytest.mark.asyncio
       async def test_js_execution(self):
           sandbox = CodeSandbox()
           mock_process = MagicMock()
           mock_process.communicate = AsyncMock(
               return_value=(b"hello\n", b"")
           )
           mock_process.returncode = 0
           mock_process.kill = MagicMock()

           with patch("asyncio.create_subprocess_exec", return_value=mock_process):
               result = await sandbox.execute("console.log('hello')", "javascript")
               assert result.language == "javascript"

4. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/nodes/code/test_sandbox.py -v

VERIFICAR:
- [ ] Sandbox: sin red (--network=none en comando Podman)
- [ ] Timeout: 30 segundos
- [ ] RAM: 256MB máximo
- [ ] Solo Python, JavaScript, Bash soportados
- [ ] Container SIEMPRE destruido (incluso en error)
- [ ] Código peligroso bloqueado (os.system, subprocess, __import__)
- [ ] Código seguro permitido (print, math, etc.)
- [ ] Output capturado: stdout, stderr, exit_code
- [ ] Filesystem read-only excepto /tmp
- [ ] TODOS los tests pasan

SI FALLA:
- Podman no instalado: tests usan mocks de subprocess
- asyncio.wait_for mock: verificar timeout handling
- Import error: verificar __init__.py

NO HACER:
- No relajar NINGUNA restricción de seguridad
- No permitir network access bajo ninguna circunstancia
- No aumentar timeout más allá de 30 segundos
- No aumentar memoria más allá de 256MB
- No implementar Git (eso es 5.9)

GATE: CodeSandbox ejecuta en container efímero, sin red, timeout 30s, 256MB RAM, auto-destruido, código peligroso bloqueado, todos los tests pasan.
```
