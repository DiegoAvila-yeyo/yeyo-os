## ═══════════════════════════════════════
## MICRO-FASE 4.4 — Container Security
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 4.4-1 [VSCODE] — Hardening de containers Podman para aislamiento de nodos

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 4.4 de Capa 4 (Sistema Nervioso): crear el sistema de seguridad de containers Podman para aislar nodos.

CONTEXTO:
- Micro-fases 4.0-4.3 completadas: Manifest, Builder, Installer, Permissions funcionando
- Container isolation: Podman (NUNCA Docker). Docker socket JAMÁS montado
- Reglas ABSOLUTAS:
  * No Docker socket JAMÁS (ni /var/run/docker.sock ni ningún otro)
  * No modo privilegiado JAMÁS
  * No SYS_ADMIN capability JAMÁS
  * No NET_RAW capability JAMÁS
  * no-new-privileges SIEMPRE activado
  * ALL capabilities dropped SIEMPRE
  * Root filesystem read-only SIEMPRE
- Seccomp, PID namespaces, network namespaces habilitados

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/security/container.py:

   Ruta: ~/yeyo-os/src/security/container.py
   Contenido:

   """
   YeyoOS — Secure Container Manager (Podman)
   Micro-fase 4.4 — Capa 4: Sistema Nervioso

   Gestiona containers Podman con hardening de seguridad.
   REGLAS ABSOLUTAS:
   - Podman SIEMPRE. Docker NUNCA.
   - Docker socket JAMÁS montado.
   - No privileged mode. No SYS_ADMIN. No NET_RAW.
   - no-new-privileges SIEMPRE. ALL capabilities dropped.
   - Root filesystem read-only.
   """

   import asyncio
   from typing import Optional
   from dataclasses import dataclass, field


   FORBIDDEN_MOUNTS = [
       "/var/run/docker.sock",
       "/run/docker.sock",
       "/var/run/podman/podman.sock",
   ]

   FORBIDDEN_CAPABILITIES = [
       "SYS_ADMIN",
       "NET_RAW",
       "SYS_PTRACE",
       "NET_ADMIN",
       "SYS_MODULE",
       "SYS_RAWIO",
       "MKNOD",
   ]

   REQUIRED_SECURITY_OPTS = [
       "no-new-privileges:true",
   ]


   @dataclass
   class ContainerManifest:
       """Datos del manifest relevantes para seguridad del container."""
       image: str
       memory_limit: str = "512m"
       cpu_limit: str = "1.0"
       network: str = "none"
       privilege_level: str = "L2"
       pids_limit: int = 256
       extra_mounts: list[str] = field(default_factory=list)
       extra_caps: list[str] = field(default_factory=list)


   class ContainerSecurityError(Exception):
       """Error de seguridad en configuración de container."""
       pass


   class SecureContainer:
       """Gestiona containers Podman con hardening de seguridad máximo."""

       def __init__(self):
           self._running_containers: dict[str, dict] = {}

       def get_run_args(self, manifest: ContainerManifest) -> list[str]:
           """
           Genera argumentos de Podman seguros para ejecutar un container.
           Aplica TODAS las restricciones de seguridad.
           """
           self._validate_security(manifest)

           args = [
               "--rm",
               "--security-opt=no-new-privileges:true",
               "--cap-drop=ALL",
               "--read-only",
               "--tmpfs=/tmp:rw,noexec,nosuid",
               f"--memory={manifest.memory_limit}",
               f"--cpus={manifest.cpu_limit}",
               f"--pids-limit={manifest.pids_limit}",
               f"--network={manifest.network}",
               "--userns=keep-id",
               "--security-opt=seccomp=default",
               "--log-driver=journald",
           ]

           if manifest.privilege_level == "L5":
               args.extend([
                   "--memory=256m",
                   "--cpus=0.5",
                   "--pids-limit=64",
                   "--network=none",
                   "--read-only",
               ])

           return args

       def _validate_security(self, manifest: ContainerManifest) -> None:
           """
           Valida que la configuración del container no viole reglas de seguridad.
           Lanza ContainerSecurityError si hay violaciones.
           """
           for mount in manifest.extra_mounts:
               for forbidden in FORBIDDEN_MOUNTS:
                   if forbidden in mount:
                       raise ContainerSecurityError(
                           f"PROHIBIDO: Montar {forbidden} no está permitido. "
                           f"Docker socket JAMÁS se monta en containers."
                       )

           for cap in manifest.extra_caps:
               cap_upper = cap.upper()
               if cap_upper in FORBIDDEN_CAPABILITIES:
                   raise ContainerSecurityError(
                       f"PROHIBIDO: Capability {cap_upper} no está permitida."
                   )

       async def run(
           self,
           manifest: ContainerManifest,
           command: Optional[list[str]] = None,
       ) -> dict:
           """Ejecuta un container con seguridad hardened."""
           self._validate_security(manifest)
           args = self.get_run_args(manifest)

           cmd = ["podman", "run"] + args + [manifest.image]
           if command:
               cmd.extend(command)

           proc = await asyncio.create_subprocess_exec(
               *cmd,
               stdout=asyncio.subprocess.PIPE,
               stderr=asyncio.subprocess.PIPE,
           )
           stdout, stderr = await proc.communicate()

           container_id = stdout.decode().strip()[:12] if stdout else "unknown"

           result = {
               "container_id": container_id,
               "exit_code": proc.returncode,
               "stdout": stdout.decode() if stdout else "",
               "stderr": stderr.decode() if stderr else "",
               "image": manifest.image,
               "status": "exited",
           }

           return result

       async def run_detached(self, manifest: ContainerManifest) -> str:
           """Ejecuta un container en background y retorna el container_id."""
           self._validate_security(manifest)
           args = self.get_run_args(manifest)

           # Remover --rm para containers detached (se limpia al stop)
           args_detached = [a for a in args if a != "--rm"]
           args_detached.append("-d")

           cmd = ["podman", "run"] + args_detached + [manifest.image]

           proc = await asyncio.create_subprocess_exec(
               *cmd,
               stdout=asyncio.subprocess.PIPE,
               stderr=asyncio.subprocess.PIPE,
           )
           stdout, stderr = await proc.communicate()

           if proc.returncode != 0:
               raise ContainerSecurityError(
                   f"Podman run falló: {stderr.decode()}"
               )

           container_id = stdout.decode().strip()[:12]
           self._running_containers[container_id] = {
               "image": manifest.image,
               "status": "running",
               "manifest": manifest,
           }
           return container_id

       async def stop(self, container_id: str) -> None:
           """Detiene un container en ejecución."""
           proc = await asyncio.create_subprocess_exec(
               "podman", "stop", container_id,
               stdout=asyncio.subprocess.PIPE,
               stderr=asyncio.subprocess.PIPE,
           )
           await proc.communicate()

           proc_rm = await asyncio.create_subprocess_exec(
               "podman", "rm", container_id, "--force",
               stdout=asyncio.subprocess.PIPE,
               stderr=asyncio.subprocess.PIPE,
           )
           await proc_rm.communicate()

           if container_id in self._running_containers:
               self._running_containers[container_id]["status"] = "stopped"

       async def get_status(self, container_id: str) -> dict:
           """Obtiene el estado de un container."""
           proc = await asyncio.create_subprocess_exec(
               "podman", "inspect", container_id,
               "--format", "{{.State.Status}}",
               stdout=asyncio.subprocess.PIPE,
               stderr=asyncio.subprocess.PIPE,
           )
           stdout, stderr = await proc.communicate()

           if proc.returncode != 0:
               return {"container_id": container_id, "status": "not_found"}

           status = stdout.decode().strip()
           return {
               "container_id": container_id,
               "status": status,
           }

       def get_running_containers(self) -> dict[str, dict]:
           """Retorna los containers registrados como en ejecución."""
           return {
               cid: info
               for cid, info in self._running_containers.items()
               if info["status"] == "running"
           }

2. Actualizar archivo src/security/__init__.py:

   Ruta: ~/yeyo-os/src/security/__init__.py
   Contenido:
   from .permissions import Permission, PermissionManager, PermissionGrant
   from .container import SecureContainer, ContainerManifest, ContainerSecurityError

3. Crear archivo tests/unit/security/test_container.py:

   Ruta: ~/yeyo-os/tests/unit/security/test_container.py
   Contenido:

   """Tests para Container Security — Micro-fase 4.4"""

   import pytest
   from unittest.mock import AsyncMock, patch

   from src.security.container import (
       SecureContainer,
       ContainerManifest,
       ContainerSecurityError,
       FORBIDDEN_MOUNTS,
       FORBIDDEN_CAPABILITIES,
   )


   @pytest.fixture
   def container():
       return SecureContainer()


   @pytest.fixture
   def default_manifest():
       return ContainerManifest(
           image="yeyo-test:1.0.0",
           memory_limit="512m",
           cpu_limit="1.0",
           network="none",
       )


   class TestSecureContainerArgs:
       """Tests para argumentos de seguridad de Podman."""

       def test_no_new_privileges_enabled(self, container, default_manifest):
           args = container.get_run_args(default_manifest)
           assert "--security-opt=no-new-privileges:true" in args

       def test_all_capabilities_dropped(self, container, default_manifest):
           args = container.get_run_args(default_manifest)
           assert "--cap-drop=ALL" in args

       def test_read_only_root_filesystem(self, container, default_manifest):
           args = container.get_run_args(default_manifest)
           assert "--read-only" in args

       def test_memory_limited(self, container, default_manifest):
           args = container.get_run_args(default_manifest)
           assert "--memory=512m" in args

       def test_cpu_limited(self, container, default_manifest):
           args = container.get_run_args(default_manifest)
           assert "--cpus=1.0" in args

       def test_pids_limited(self, container, default_manifest):
           args = container.get_run_args(default_manifest)
           assert "--pids-limit=256" in args

       def test_network_isolated(self, container, default_manifest):
           args = container.get_run_args(default_manifest)
           assert "--network=none" in args

       def test_userns_keep_id(self, container, default_manifest):
           args = container.get_run_args(default_manifest)
           assert "--userns=keep-id" in args

       def test_tmpfs_tmp_noexec(self, container, default_manifest):
           args = container.get_run_args(default_manifest)
           assert "--tmpfs=/tmp:rw,noexec,nosuid" in args

       def test_rm_flag_present(self, container, default_manifest):
           args = container.get_run_args(default_manifest)
           assert "--rm" in args

       def test_seccomp_default(self, container, default_manifest):
           args = container.get_run_args(default_manifest)
           assert "--security-opt=seccomp=default" in args

       def test_l5_sandbox_extra_restrictions(self, container):
           manifest = ContainerManifest(
               image="yeyo-sandbox:1.0.0",
               privilege_level="L5",
           )
           args = container.get_run_args(manifest)
           assert "--network=none" in args
           assert "--pids-limit=64" in args


   class TestSecureContainerSecurity:
       """Tests para validaciones de seguridad ABSOLUTAS."""

       def test_no_docker_sock_mount(self, container):
           manifest = ContainerManifest(
               image="test:1.0",
               extra_mounts=["/var/run/docker.sock:/var/run/docker.sock"],
           )
           with pytest.raises(ContainerSecurityError, match="PROHIBIDO"):
               container.get_run_args(manifest)

       def test_no_run_docker_sock(self, container):
           manifest = ContainerManifest(
               image="test:1.0",
               extra_mounts=["/run/docker.sock:/run/docker.sock"],
           )
           with pytest.raises(ContainerSecurityError, match="PROHIBIDO"):
               container.get_run_args(manifest)

       def test_no_podman_sock_mount(self, container):
           manifest = ContainerManifest(
               image="test:1.0",
               extra_mounts=["/var/run/podman/podman.sock:/run/podman.sock"],
           )
           with pytest.raises(ContainerSecurityError, match="PROHIBIDO"):
               container.get_run_args(manifest)

       def test_no_sys_admin_capability(self, container):
           manifest = ContainerManifest(
               image="test:1.0",
               extra_caps=["SYS_ADMIN"],
           )
           with pytest.raises(ContainerSecurityError, match="PROHIBIDO"):
               container.get_run_args(manifest)

       def test_no_net_raw_capability(self, container):
           manifest = ContainerManifest(
               image="test:1.0",
               extra_caps=["NET_RAW"],
           )
           with pytest.raises(ContainerSecurityError, match="PROHIBIDO"):
               container.get_run_args(manifest)

       def test_no_sys_ptrace_capability(self, container):
           manifest = ContainerManifest(
               image="test:1.0",
               extra_caps=["SYS_PTRACE"],
           )
           with pytest.raises(ContainerSecurityError, match="PROHIBIDO"):
               container.get_run_args(manifest)

       def test_no_net_admin_capability(self, container):
           manifest = ContainerManifest(
               image="test:1.0",
               extra_caps=["NET_ADMIN"],
           )
           with pytest.raises(ContainerSecurityError, match="PROHIBIDO"):
               container.get_run_args(manifest)

       def test_all_forbidden_mounts_blocked(self, container):
           for mount in FORBIDDEN_MOUNTS:
               manifest = ContainerManifest(
                   image="test:1.0",
                   extra_mounts=[f"{mount}:{mount}"],
               )
               with pytest.raises(ContainerSecurityError):
                   container.get_run_args(manifest)

       def test_all_forbidden_capabilities_blocked(self, container):
           for cap in FORBIDDEN_CAPABILITIES:
               manifest = ContainerManifest(
                   image="test:1.0",
                   extra_caps=[cap],
               )
               with pytest.raises(ContainerSecurityError):
                   container.get_run_args(manifest)

       def test_safe_manifest_passes_validation(self, container, default_manifest):
           args = container.get_run_args(default_manifest)
           assert len(args) > 0


   class TestSecureContainerRun:
       """Tests para ejecución de containers."""

       @pytest.mark.asyncio
       async def test_run_uses_podman(self, container, default_manifest):
           mock_proc = AsyncMock()
           mock_proc.returncode = 0
           mock_proc.communicate = AsyncMock(return_value=(b"abc123", b""))

           with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
               result = await container.run(default_manifest)

           call_args = mock_exec.call_args[0]
           assert call_args[0] == "podman", "DEBE usar Podman, NUNCA Docker"
           assert call_args[1] == "run"

       @pytest.mark.asyncio
       async def test_run_returns_result(self, container, default_manifest):
           mock_proc = AsyncMock()
           mock_proc.returncode = 0
           mock_proc.communicate = AsyncMock(return_value=(b"container_id_123", b""))

           with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
               result = await container.run(default_manifest)

           assert "container_id" in result
           assert result["exit_code"] == 0
           assert result["status"] == "exited"

       @pytest.mark.asyncio
       async def test_run_with_command(self, container, default_manifest):
           mock_proc = AsyncMock()
           mock_proc.returncode = 0
           mock_proc.communicate = AsyncMock(return_value=(b"output", b""))

           with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
               await container.run(default_manifest, command=["echo", "hello"])

           call_args = mock_exec.call_args[0]
           assert "echo" in call_args
           assert "hello" in call_args

       @pytest.mark.asyncio
       async def test_stop_calls_podman_stop(self, container):
           mock_proc = AsyncMock()
           mock_proc.returncode = 0
           mock_proc.communicate = AsyncMock(return_value=(b"", b""))

           with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
               await container.stop("abc123")

           calls = mock_exec.call_args_list
           assert any("stop" in str(c) for c in calls)

4. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/security/test_container.py -v

VERIFICAR:
- [ ] Archivo src/security/container.py existe con SecureContainer
- [ ] no-new-privileges SIEMPRE habilitado
- [ ] ALL capabilities SIEMPRE dropped
- [ ] Root filesystem SIEMPRE read-only
- [ ] Memory y CPU limitados
- [ ] Network aislada (default: none)
- [ ] Docker socket JAMÁS montable (var/run/docker.sock, run/docker.sock)
- [ ] Podman socket tampoco montable
- [ ] SYS_ADMIN, NET_RAW, SYS_PTRACE, NET_ADMIN bloqueados
- [ ] L5 (sandbox) tiene restricciones extras
- [ ] Podman usado en TODOS los comandos (NUNCA Docker)
- [ ] TODOS los tests pasan

SI FALLA:
- Mock de subprocess: usar AsyncMock correctamente
- Import error: verificar __init__.py
- Capabilities case: convertir a uppercase antes de comparar

NO HACER:
- No usar Docker en ningún lugar — SOLO Podman
- No montar Docker socket bajo NINGUNA circunstancia
- No agregar modo privilegiado
- No permitir SYS_ADMIN ni NET_RAW

GATE: SecureContainer aplica hardening completo, bloquea TODAS las operaciones prohibidas, usa solo Podman, todos los tests pasan.
```
