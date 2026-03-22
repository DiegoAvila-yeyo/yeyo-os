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
