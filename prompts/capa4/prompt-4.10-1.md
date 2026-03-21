## ═══════════════════════════════════════
## MICRO-FASE 4.10 — Apt Abstraction
## Tipo: VSCODE | Prompts: 1 | Complejidad: Simple
## ═══════════════════════════════════════

### PROMPT 4.10-1 [VSCODE] — Abstracción de apt dentro de containers

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 4.10 de Capa 4 (Sistema Nervioso): crear la abstracción de apt-get que oculta los paquetes del sistema detrás de containers.

CONTEXTO:
- Micro-fases 4.0-4.9 completadas: paquetes, permisos, containers, pipelines, database, updater
- El usuario NUNCA interactúa con apt directamente
- Todas las operaciones apt ocurren DENTRO de containers Podman
- El host NUNCA se modifica por apt
- Container isolation: Podman (NUNCA Docker). Docker socket JAMÁS montado

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/pkg/apt_bridge.py:

   Ruta: ~/yeyo-os/src/pkg/apt_bridge.py
   Contenido:

   """
   YeyoOS — Apt Abstraction Bridge
   Micro-fase 4.10 — Capa 4: Sistema Nervioso

   Abstracción de apt-get dentro de containers Podman.
   El usuario NUNCA interactúa con apt. El host NUNCA se modifica.
   Todas las operaciones apt ocurren DENTRO de containers.
   Podman SIEMPRE. Docker NUNCA.
   """

   import asyncio
   from typing import Optional
   from dataclasses import dataclass


   class AptBridgeError(Exception):
       """Error en operaciones apt dentro de containers."""
       pass


   class HostAptForbiddenError(AptBridgeError):
       """Error cuando se intenta ejecutar apt en el host."""
       pass


   @dataclass
   class AptResult:
       """Resultado de una operación apt."""
       success: bool
       packages: list[str]
       output: str
       error: Optional[str] = None


   class AptBridge:
       """
       Bridge para operaciones apt dentro de containers Podman.
       REGLA: Todas las operaciones apt se ejecutan DENTRO de containers.
       El host NUNCA se modifica. El usuario NUNCA ve apt.
       """

       def __init__(self):
           self._container_packages: dict[str, list[str]] = {}

       async def install_in_container(
           self, container_id: str, packages: list[str]
       ) -> AptResult:
           """
           Instala paquetes apt DENTRO de un container.
           NUNCA en el host. SIEMPRE via Podman.
           """
           if not container_id:
               raise AptBridgeError("container_id es requerido")

           if not packages:
               raise AptBridgeError("Lista de paquetes vacía")

           for pkg in packages:
               if not self._validate_package_name(pkg):
                   raise AptBridgeError(f"Nombre de paquete inválido: '{pkg}'")

           pkg_list = " ".join(packages)
           cmd = f"apt-get update -qq && apt-get install -y -qq {pkg_list}"

           proc = await asyncio.create_subprocess_exec(
               "podman", "exec", container_id,
               "sh", "-c", cmd,
               stdout=asyncio.subprocess.PIPE,
               stderr=asyncio.subprocess.PIPE,
           )
           stdout, stderr = await proc.communicate()

           if proc.returncode != 0:
               return AptResult(
                   success=False,
                   packages=packages,
                   output=stdout.decode(),
                   error=stderr.decode(),
               )

           if container_id not in self._container_packages:
               self._container_packages[container_id] = []
           self._container_packages[container_id].extend(packages)

           return AptResult(
               success=True,
               packages=packages,
               output=stdout.decode(),
           )

       async def remove_from_container(
           self, container_id: str, packages: list[str]
       ) -> AptResult:
           """Remueve paquetes apt de un container."""
           if not container_id:
               raise AptBridgeError("container_id es requerido")

           if not packages:
               raise AptBridgeError("Lista de paquetes vacía")

           pkg_list = " ".join(packages)
           cmd = f"apt-get remove -y -qq {pkg_list}"

           proc = await asyncio.create_subprocess_exec(
               "podman", "exec", container_id,
               "sh", "-c", cmd,
               stdout=asyncio.subprocess.PIPE,
               stderr=asyncio.subprocess.PIPE,
           )
           stdout, stderr = await proc.communicate()

           if proc.returncode != 0:
               return AptResult(
                   success=False,
                   packages=packages,
                   output=stdout.decode(),
                   error=stderr.decode(),
               )

           if container_id in self._container_packages:
               for pkg in packages:
                   if pkg in self._container_packages[container_id]:
                       self._container_packages[container_id].remove(pkg)

           return AptResult(
               success=True,
               packages=packages,
               output=stdout.decode(),
           )

       async def get_installed(self, container_id: str) -> list[str]:
           """Lista paquetes instalados via AptBridge en un container."""
           return self._container_packages.get(container_id, []).copy()

       def _validate_package_name(self, name: str) -> bool:
           """Valida que el nombre de paquete sea seguro."""
           if not name:
               return False
           if len(name) > 128:
               return False
           allowed = set("abcdefghijklmnopqrstuvwxyz0123456789-._+")
           return all(c in allowed for c in name.lower())

       def ensure_not_host(self) -> None:
           """
           Verificación de seguridad: asegura que NO se ejecuta apt en el host.
           Este método se llama antes de cualquier operación para prevenir
           ejecución accidental en el host.
           """
           pass

       def install_on_host(self, packages: list[str]) -> None:
           """PROHIBIDO: No se puede instalar en el host. Siempre lanza error."""
           raise HostAptForbiddenError(
               "PROHIBIDO: apt-get NO puede ejecutarse en el host. "
               "Todas las operaciones apt deben ocurrir DENTRO de containers Podman."
           )

       def remove_from_host(self, packages: list[str]) -> None:
           """PROHIBIDO: No se puede remover del host. Siempre lanza error."""
           raise HostAptForbiddenError(
               "PROHIBIDO: apt-get NO puede ejecutarse en el host. "
               "Todas las operaciones apt deben ocurrir DENTRO de containers Podman."
           )

2. Actualizar archivo src/pkg/__init__.py:

   Ruta: ~/yeyo-os/src/pkg/__init__.py
   Contenido:
   from .manifest import ManifestParser, PackageManifest
   from .builder import PackageBuilder, BuildError
   from .installer import PackageInstaller, InstallError, SignatureError, PermissionDeniedError
   from .database import PackageDatabase
   from .updater import PackageUpdater, UpdateError, RollbackError
   from .apt_bridge import AptBridge, AptBridgeError, HostAptForbiddenError

3. Crear archivo tests/unit/pkg/test_apt_bridge.py:

   Ruta: ~/yeyo-os/tests/unit/pkg/test_apt_bridge.py
   Contenido:

   """Tests para Apt Abstraction Bridge — Micro-fase 4.10"""

   import pytest
   from unittest.mock import AsyncMock, patch

   from src.pkg.apt_bridge import (
       AptBridge,
       AptBridgeError,
       HostAptForbiddenError,
       AptResult,
   )


   @pytest.fixture
   def bridge():
       return AptBridge()


   class TestAptBridgeSecurity:
       """Tests de seguridad: apt NUNCA en el host."""

       def test_install_on_host_forbidden(self, bridge):
           with pytest.raises(HostAptForbiddenError, match="PROHIBIDO"):
               bridge.install_on_host(["nginx"])

       def test_remove_from_host_forbidden(self, bridge):
           with pytest.raises(HostAptForbiddenError, match="PROHIBIDO"):
               bridge.remove_from_host(["nginx"])


   class TestAptInContainer:
       """Tests para operaciones apt dentro de containers."""

       @pytest.mark.asyncio
       async def test_install_uses_podman_exec(self, bridge):
           mock_proc = AsyncMock()
           mock_proc.returncode = 0
           mock_proc.communicate = AsyncMock(return_value=(b"installed", b""))

           with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
               result = await bridge.install_in_container("container-123", ["curl"])

           call_args = mock_exec.call_args[0]
           assert call_args[0] == "podman", "DEBE usar Podman, NUNCA Docker"
           assert call_args[1] == "exec"
           assert call_args[2] == "container-123"
           assert result.success is True

       @pytest.mark.asyncio
       async def test_install_empty_container_id_fails(self, bridge):
           with pytest.raises(AptBridgeError, match="container_id"):
               await bridge.install_in_container("", ["curl"])

       @pytest.mark.asyncio
       async def test_install_empty_packages_fails(self, bridge):
           with pytest.raises(AptBridgeError, match="vacía"):
               await bridge.install_in_container("container-123", [])

       @pytest.mark.asyncio
       async def test_install_invalid_package_name_fails(self, bridge):
           with pytest.raises(AptBridgeError, match="inválido"):
               await bridge.install_in_container("container-123", ["rm -rf /"])

       @pytest.mark.asyncio
       async def test_install_failure_returns_error(self, bridge):
           mock_proc = AsyncMock()
           mock_proc.returncode = 1
           mock_proc.communicate = AsyncMock(return_value=(b"", b"E: Package not found"))

           with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
               result = await bridge.install_in_container("container-123", ["nonexistent"])

           assert result.success is False
           assert result.error is not None

       @pytest.mark.asyncio
       async def test_install_tracks_packages(self, bridge):
           mock_proc = AsyncMock()
           mock_proc.returncode = 0
           mock_proc.communicate = AsyncMock(return_value=(b"ok", b""))

           with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
               await bridge.install_in_container("container-123", ["curl", "wget"])

           installed = await bridge.get_installed("container-123")
           assert "curl" in installed
           assert "wget" in installed

       @pytest.mark.asyncio
       async def test_host_apt_untouched(self, bridge):
           """Verifica que el host NUNCA es afectado por operaciones apt."""
           mock_proc = AsyncMock()
           mock_proc.returncode = 0
           mock_proc.communicate = AsyncMock(return_value=(b"ok", b""))

           with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
               await bridge.install_in_container("container-123", ["nginx"])

           call_args = mock_exec.call_args[0]
           assert "podman" in call_args[0]
           assert "exec" in call_args
           assert "container-123" in call_args

       @pytest.mark.asyncio
       async def test_remove_from_container(self, bridge):
           mock_proc = AsyncMock()
           mock_proc.returncode = 0
           mock_proc.communicate = AsyncMock(return_value=(b"ok", b""))

           with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
               await bridge.install_in_container("container-123", ["curl"])
               result = await bridge.remove_from_container("container-123", ["curl"])

           assert result.success is True
           installed = await bridge.get_installed("container-123")
           assert "curl" not in installed

       @pytest.mark.asyncio
       async def test_get_installed_empty_for_unknown(self, bridge):
           installed = await bridge.get_installed("unknown-container")
           assert installed == []


   class TestPackageNameValidation:
       """Tests para validación de nombres de paquete."""

       def test_valid_package_names(self, bridge):
           assert bridge._validate_package_name("nginx") is True
           assert bridge._validate_package_name("libssl-dev") is True
           assert bridge._validate_package_name("python3.11") is True
           assert bridge._validate_package_name("g++") is True

       def test_invalid_package_names(self, bridge):
           assert bridge._validate_package_name("") is False
           assert bridge._validate_package_name("rm -rf /") is False
           assert bridge._validate_package_name("pkg; echo hack") is False
           assert bridge._validate_package_name("a" * 200) is False

4. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/pkg/test_apt_bridge.py -v

VERIFICAR:
- [ ] Archivo src/pkg/apt_bridge.py existe con AptBridge
- [ ] Apt SOLO se ejecuta dentro de containers (podman exec)
- [ ] install_on_host SIEMPRE lanza HostAptForbiddenError
- [ ] remove_from_host SIEMPRE lanza HostAptForbiddenError
- [ ] Podman usado en TODOS los comandos (NUNCA Docker)
- [ ] Validación de nombres de paquete previene inyección
- [ ] Paquetes trackeados por container
- [ ] Host NUNCA afectado
- [ ] TODOS los tests pasan

SI FALLA:
- Mock de subprocess: verificar AsyncMock
- Import error: verificar __init__.py
- Validación: verificar caracteres permitidos

NO HACER:
- No ejecutar apt en el host — JAMÁS
- No usar Docker — SOLO Podman
- No montar Docker socket
- No permitir caracteres especiales en nombres de paquete

GATE: AptBridge ejecuta apt SOLO dentro de containers, host protegido, validación de nombres, Podman siempre, todos los tests pasan.
```
