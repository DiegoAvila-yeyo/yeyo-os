## ═══════════════════════════════════════
## MICRO-FASE 4.2 — YEYO-PKG Installer
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 4.2-1 [VSCODE] — Instalar paquetes .ypkg en el sistema

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 4.2 de Capa 4 (Sistema Nervioso): crear el instalador de paquetes .ypkg.

CONTEXTO:
- Micro-fases 4.0-4.1 completadas: ManifestParser + PackageBuilder funcionando
- El instalador verifica firma, extrae, valida, carga imagen en Podman, registra en DB
- Container isolation: Podman (NUNCA Docker). Docker socket JAMÁS montado
- Permisos: ALLOWLIST — el usuario debe aprobar cada permiso solicitado
- Nodos IA siempre L5 (sandbox)

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/pkg/installer.py:

   Ruta: ~/yeyo-os/src/pkg/installer.py
   Contenido:

   """
   YeyoOS — YEYO-PKG Package Installer
   Micro-fase 4.2 — Capa 4: Sistema Nervioso

   Instala, desinstala y gestiona paquetes .ypkg.
   Verifica firmas, valida permisos, carga imágenes en Podman.
   """

   import os
   import json
   import tarfile
   import tempfile
   import asyncio
   import shutil
   from datetime import datetime, timezone
   from pathlib import Path
   from typing import Optional, Callable, Awaitable

   from .manifest import ManifestParser, PackageManifest


   class InstallError(Exception):
       """Error durante la instalación de un paquete."""
       pass


   class SignatureError(InstallError):
       """Error de verificación de firma."""
       pass


   class PermissionDeniedError(InstallError):
       """Error cuando el usuario deniega permisos."""
       pass


   PermissionCallback = Callable[[str, list[str]], Awaitable[dict]]


   class PackageInstaller:
       """Instala y gestiona paquetes .ypkg en YeyoOS."""

       def __init__(
           self,
           install_dir: str = "installed_packages",
           permission_callback: Optional[PermissionCallback] = None,
       ):
           self.install_dir = Path(install_dir)
           self.install_dir.mkdir(parents=True, exist_ok=True)
           self.permission_callback = permission_callback
           self._registry: dict[str, dict] = {}
           self._load_registry()

       def _registry_path(self) -> Path:
           return self.install_dir / "registry.json"

       def _load_registry(self) -> None:
           """Carga el registro de paquetes instalados."""
           registry_file = self._registry_path()
           if registry_file.exists():
               self._registry = json.loads(registry_file.read_text())
           else:
               self._registry = {}

       def _save_registry(self) -> None:
           """Guarda el registro de paquetes instalados."""
           self._registry_path().write_text(
               json.dumps(self._registry, indent=2, default=str)
           )

       async def install(self, ypkg_path: str) -> dict:
           """
           Instala un paquete .ypkg en el sistema.
           Retorna información del paquete instalado.
           """
           ypkg = Path(ypkg_path)
           if not ypkg.exists():
               raise InstallError(f"Archivo no encontrado: {ypkg_path}")

           if not ypkg.name.endswith(".ypkg"):
               raise InstallError(f"Formato inválido. Se esperaba .ypkg: {ypkg.name}")

           with tempfile.TemporaryDirectory(prefix="yeyo-install-") as temp_dir:
               temp_path = Path(temp_dir)
               self._extract_package(ypkg, temp_path)
               self._verify_signature(temp_path)
               manifest = self._validate_manifest(temp_path)

               if manifest.name in self._registry:
                   raise InstallError(
                       f"Paquete '{manifest.name}' ya está instalado. "
                       f"Desinstálalo primero o usa update."
                   )

               await self._check_permissions(manifest)
               await self._load_container_image(temp_path)
               self._install_ui_bundle(manifest, temp_path)
               self._register_package(manifest)

           return self.get_info(manifest.name)

       def _extract_package(self, ypkg: Path, dest: Path) -> None:
           """Extrae el contenido del .ypkg."""
           try:
               with tarfile.open(ypkg, "r:gz") as tar:
                   tar.extractall(dest, filter="data")
           except tarfile.TarError as e:
               raise InstallError(f"Error extrayendo paquete: {e}")

       def _verify_signature(self, extracted_dir: Path) -> None:
           """Verifica la firma SHA-256 del paquete."""
           metadata_file = extracted_dir / "build-metadata.json"
           if not metadata_file.exists():
               raise SignatureError("build-metadata.json no encontrado en el paquete")

           metadata = json.loads(metadata_file.read_text())
           signature = metadata.get("signature")
           if not signature:
               raise SignatureError("Firma no encontrada en metadata")

           if not signature.startswith("sha256:"):
               raise SignatureError(f"Formato de firma inválido: {signature}")

           import hashlib
           hasher = hashlib.sha256()
           for file_path in sorted(extracted_dir.rglob("*")):
               if file_path.is_file() and file_path.name != "build-metadata.json":
                   hasher.update(file_path.name.encode())
                   hasher.update(file_path.read_bytes())

           expected = f"sha256:{hasher.hexdigest()}"
           if signature != expected:
               raise SignatureError(
                   "Firma del paquete no coincide. El paquete puede haber sido alterado."
               )

       def _validate_manifest(self, extracted_dir: Path) -> PackageManifest:
           """Valida el manifest del paquete extraído."""
           manifest_file = extracted_dir / "manifest.yml"
           if not manifest_file.exists():
               raise InstallError("manifest.yml no encontrado en el paquete")
           return ManifestParser.parse_file(str(manifest_file))

       async def _check_permissions(self, manifest: PackageManifest) -> None:
           """Solicita aprobación de permisos al usuario (ALLOWLIST)."""
           if not manifest.permissions:
               return

           if self.permission_callback:
               result = await self.permission_callback(
                   manifest.name, manifest.permissions
               )
               denied = result.get("denied", [])
               if denied:
                   raise PermissionDeniedError(
                       f"Permisos denegados para '{manifest.name}': {denied}"
                   )

       async def _load_container_image(self, extracted_dir: Path) -> None:
           """Carga la imagen de container en Podman."""
           image_file = extracted_dir / "container-image.tar"
           if not image_file.exists():
               return

           proc = await asyncio.create_subprocess_exec(
               "podman", "load",
               "-i", str(image_file),
               stdout=asyncio.subprocess.PIPE,
               stderr=asyncio.subprocess.PIPE,
           )
           stdout, stderr = await proc.communicate()

           if proc.returncode != 0:
               raise InstallError(
                   f"Podman load falló (exit {proc.returncode}): {stderr.decode()}"
               )

       def _install_ui_bundle(self, manifest: PackageManifest, extracted_dir: Path) -> None:
           """Instala el bundle de UI del paquete."""
           pkg_dir = self.install_dir / manifest.name
           pkg_dir.mkdir(parents=True, exist_ok=True)

           ui_src = extracted_dir / "ui"
           if ui_src.exists():
               ui_dest = pkg_dir / "ui"
               if ui_dest.exists():
                   shutil.rmtree(ui_dest)
               shutil.copytree(ui_src, ui_dest)

           manifest_src = extracted_dir / "manifest.yml"
           if manifest_src.exists():
               shutil.copy2(manifest_src, pkg_dir / "manifest.yml")

           assets_src = extracted_dir / "assets"
           if assets_src.exists():
               assets_dest = pkg_dir / "assets"
               if assets_dest.exists():
                   shutil.rmtree(assets_dest)
               shutil.copytree(assets_src, assets_dest)

       def _register_package(self, manifest: PackageManifest) -> None:
           """Registra el paquete en el registro local."""
           self._registry[manifest.name] = {
               "name": manifest.name,
               "version": manifest.version,
               "author": manifest.author,
               "description": manifest.description,
               "type": manifest.type.value,
               "privilege_level": manifest.privilege_level.value,
               "permissions": manifest.permissions,
               "installed_at": datetime.now(timezone.utc).isoformat(),
               "status": "installed",
           }
           self._save_registry()

       async def uninstall(self, package_name: str) -> None:
           """Desinstala un paquete del sistema."""
           if package_name not in self._registry:
               raise InstallError(f"Paquete '{package_name}' no está instalado")

           pkg_info = self._registry[package_name]
           image_name = None
           pkg_dir = self.install_dir / package_name
           manifest_file = pkg_dir / "manifest.yml"
           if manifest_file.exists():
               try:
                   manifest = ManifestParser.parse_file(str(manifest_file))
                   image_name = manifest.container.image
               except Exception:
                   pass

           if image_name:
               proc = await asyncio.create_subprocess_exec(
                   "podman", "rmi", image_name, "--force",
                   stdout=asyncio.subprocess.PIPE,
                   stderr=asyncio.subprocess.PIPE,
               )
               await proc.communicate()

           if pkg_dir.exists():
               shutil.rmtree(pkg_dir)

           del self._registry[package_name]
           self._save_registry()

       def list_installed(self) -> list[dict]:
           """Lista todos los paquetes instalados."""
           return list(self._registry.values())

       def get_info(self, package_name: str) -> dict:
           """Obtiene información de un paquete instalado."""
           if package_name not in self._registry:
               raise InstallError(f"Paquete '{package_name}' no está instalado")
           return self._registry[package_name]

2. Actualizar archivo src/pkg/__init__.py:

   Ruta: ~/yeyo-os/src/pkg/__init__.py
   Contenido:
   from .manifest import ManifestParser, PackageManifest
   from .builder import PackageBuilder, BuildError
   from .installer import PackageInstaller, InstallError, SignatureError, PermissionDeniedError

3. Crear archivo tests/unit/pkg/test_installer.py:

   Ruta: ~/yeyo-os/tests/unit/pkg/test_installer.py
   Contenido:

   """Tests para YEYO-PKG Installer — Micro-fase 4.2"""

   import os
   import json
   import tarfile
   import hashlib
   import tempfile
   import pytest
   from unittest.mock import AsyncMock, patch
   from pathlib import Path

   from src.pkg.installer import (
       PackageInstaller,
       InstallError,
       SignatureError,
       PermissionDeniedError,
   )


   def _create_test_ypkg(temp_dir: str, tampered: bool = False) -> str:
       """Crea un .ypkg de prueba válido."""
       build_dir = Path(temp_dir) / "build"
       build_dir.mkdir()

       manifest_content = """
   name: "test-pkg"
   version: "1.0.0"
   author: "Test"
   description: "Test package"
   type: "node"
   container:
     image: "test:1.0.0"
   permissions:
     - "memory.read"
     - "memory.write"
   privilege_level: "L2"
   """
       (build_dir / "manifest.yml").write_text(manifest_content)

       ui_dir = build_dir / "ui"
       ui_dir.mkdir()
       (ui_dir / "index.html").write_text("<html>Test</html>")

       hasher = hashlib.sha256()
       for file_path in sorted(build_dir.rglob("*")):
           if file_path.is_file():
               hasher.update(file_path.name.encode())
               hasher.update(file_path.read_bytes())

       signature = f"sha256:{hasher.hexdigest()}"
       if tampered:
           signature = "sha256:tampered_invalid_signature_value"

       metadata = {
           "name": "test-pkg",
           "version": "1.0.0",
           "built_at": "2024-01-01T00:00:00Z",
           "signature": signature,
       }
       (build_dir / "build-metadata.json").write_text(json.dumps(metadata))

       ypkg_path = Path(temp_dir) / "test-pkg-1.0.0.ypkg"
       with tarfile.open(ypkg_path, "w:gz") as tar:
           for item in sorted(build_dir.rglob("*")):
               arcname = item.relative_to(build_dir)
               tar.add(item, arcname=str(arcname))

       return str(ypkg_path)


   @pytest.fixture
   def temp_dirs():
       """Crea directorios temporales para tests."""
       with tempfile.TemporaryDirectory(prefix="yeyo-test-") as d:
           pkg_dir = os.path.join(d, "packages")
           install_dir = os.path.join(d, "installed")
           os.makedirs(pkg_dir)
           os.makedirs(install_dir)
           yield {"base": d, "packages": pkg_dir, "installed": install_dir}


   class TestPackageInstaller:
       """Tests para PackageInstaller."""

       @pytest.mark.asyncio
       async def test_install_valid_package(self, temp_dirs):
           ypkg_path = _create_test_ypkg(temp_dirs["packages"])
           installer = PackageInstaller(install_dir=temp_dirs["installed"])
           result = await installer.install(ypkg_path)
           assert result["name"] == "test-pkg"
           assert result["version"] == "1.0.0"
           assert result["status"] == "installed"

       @pytest.mark.asyncio
       async def test_install_nonexistent_file_fails(self, temp_dirs):
           installer = PackageInstaller(install_dir=temp_dirs["installed"])
           with pytest.raises(InstallError, match="no encontrado"):
               await installer.install("/nonexistent/file.ypkg")

       @pytest.mark.asyncio
       async def test_install_invalid_format_fails(self, temp_dirs):
           fake_file = Path(temp_dirs["packages"]) / "fake.txt"
           fake_file.write_text("not a package")
           installer = PackageInstaller(install_dir=temp_dirs["installed"])
           with pytest.raises(InstallError, match="Formato inválido"):
               await installer.install(str(fake_file))

       @pytest.mark.asyncio
       async def test_signature_check_fails_on_tampered(self, temp_dirs):
           ypkg_path = _create_test_ypkg(temp_dirs["packages"], tampered=True)
           installer = PackageInstaller(install_dir=temp_dirs["installed"])
           with pytest.raises(SignatureError, match="no coincide"):
               await installer.install(ypkg_path)

       @pytest.mark.asyncio
       async def test_permissions_prompted(self, temp_dirs):
           ypkg_path = _create_test_ypkg(temp_dirs["packages"])

           permission_granted = False

           async def mock_permission_callback(name, perms):
               nonlocal permission_granted
               permission_granted = True
               return {"granted": perms, "denied": []}

           installer = PackageInstaller(
               install_dir=temp_dirs["installed"],
               permission_callback=mock_permission_callback,
           )
           await installer.install(ypkg_path)
           assert permission_granted is True

       @pytest.mark.asyncio
       async def test_permissions_denied_blocks_install(self, temp_dirs):
           ypkg_path = _create_test_ypkg(temp_dirs["packages"])

           async def deny_callback(name, perms):
               return {"granted": [], "denied": perms}

           installer = PackageInstaller(
               install_dir=temp_dirs["installed"],
               permission_callback=deny_callback,
           )
           with pytest.raises(PermissionDeniedError):
               await installer.install(ypkg_path)

       @pytest.mark.asyncio
       async def test_uninstall_removes_package(self, temp_dirs):
           ypkg_path = _create_test_ypkg(temp_dirs["packages"])
           installer = PackageInstaller(install_dir=temp_dirs["installed"])
           await installer.install(ypkg_path)

           assert len(installer.list_installed()) == 1

           mock_proc = AsyncMock()
           mock_proc.returncode = 0
           mock_proc.communicate = AsyncMock(return_value=(b"", b""))

           with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
               await installer.uninstall("test-pkg")

           assert len(installer.list_installed()) == 0

       @pytest.mark.asyncio
       async def test_uninstall_nonexistent_fails(self, temp_dirs):
           installer = PackageInstaller(install_dir=temp_dirs["installed"])
           with pytest.raises(InstallError, match="no está instalado"):
               await installer.uninstall("nonexistent")

       def test_list_installed_empty(self, temp_dirs):
           installer = PackageInstaller(install_dir=temp_dirs["installed"])
           assert installer.list_installed() == []

       @pytest.mark.asyncio
       async def test_list_installed_shows_packages(self, temp_dirs):
           ypkg_path = _create_test_ypkg(temp_dirs["packages"])
           installer = PackageInstaller(install_dir=temp_dirs["installed"])
           await installer.install(ypkg_path)
           installed = installer.list_installed()
           assert len(installed) == 1
           assert installed[0]["name"] == "test-pkg"

       @pytest.mark.asyncio
       async def test_get_info_returns_package_details(self, temp_dirs):
           ypkg_path = _create_test_ypkg(temp_dirs["packages"])
           installer = PackageInstaller(install_dir=temp_dirs["installed"])
           await installer.install(ypkg_path)
           info = installer.get_info("test-pkg")
           assert info["name"] == "test-pkg"
           assert info["version"] == "1.0.0"
           assert "installed_at" in info

       @pytest.mark.asyncio
       async def test_duplicate_install_rejected(self, temp_dirs):
           ypkg_path = _create_test_ypkg(temp_dirs["packages"])
           installer = PackageInstaller(install_dir=temp_dirs["installed"])
           await installer.install(ypkg_path)
           with pytest.raises(InstallError, match="ya está instalado"):
               await installer.install(ypkg_path)

4. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/pkg/test_installer.py -v

VERIFICAR:
- [ ] Archivo src/pkg/installer.py existe con PackageInstaller
- [ ] Instala paquete .ypkg válido correctamente
- [ ] Verificación de firma falla en paquete alterado (SignatureError)
- [ ] Permisos solicitados al usuario via callback (ALLOWLIST)
- [ ] Permisos denegados bloquean la instalación
- [ ] Uninstall remueve paquete completamente
- [ ] List muestra paquetes instalados
- [ ] Duplicado rechazado
- [ ] TODOS los tests pasan

SI FALLA:
- tarfile filter: Python 3.12+ requiere filter="data"
- Import circular: verificar orden de imports en __init__.py
- Asyncio: verificar que pytest-asyncio está instalado

NO HACER:
- No implementar el sistema de permisos completo (eso es micro-fase 4.3)
- No conectar con la base de datos SQLite aún (micro-fase 4.8)
- No implementar auto-update (micro-fase 4.9)
- No montar Docker socket JAMÁS

GATE: PackageInstaller instala/desinstala .ypkg, verifica firmas, solicita permisos, rechaza paquetes inválidos/alterados, todos los tests pasan.
```
