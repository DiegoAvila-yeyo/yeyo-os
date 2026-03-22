"""Tests para PackageInstaller — Micro-fase 4.2"""

import pytest
import tarfile
import tempfile
import json
import hashlib
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

from src.pkg.installer import PackageInstaller, InstallError, SignatureError, PermissionDeniedError


def create_fake_ypkg(tmpdir: str, pkg_name: str = "test-pkg", version: str = "1.0.0") -> str:
    """Crea un .ypkg falso (sin firma válida) para tests."""
    build_dir = Path(tmpdir) / "build"
    build_dir.mkdir()

    manifest_content = f"""name: {pkg_name}
version: {version}
author: Test
description: Test package
type: node
container:
  image: {pkg_name}:{version}
  network: none
privilege_level: L2
permissions:
  - memory.read
  - gpu.inference
"""
    (build_dir / "manifest.yml").write_text(manifest_content)
    (build_dir / "ui").mkdir()
    (build_dir / "ui" / "index.html").write_text("<html>test</html>")

    # Generar firma
    hasher = hashlib.sha256()
    for file_path in sorted(build_dir.rglob("*")):
        if file_path.is_file():
            hasher.update(file_path.name.encode())
            hasher.update(file_path.read_bytes())
    signature = f"sha256:{hasher.hexdigest()}"

    metadata = {
        "name": pkg_name,
        "version": version,
        "built_at": "2025-01-01T00:00:00Z",
        "signature": signature,
        "builder_version": "0.1.0",
    }
    (build_dir / "build-metadata.json").write_text(json.dumps(metadata))

    ypkg_path = Path(tmpdir) / f"{pkg_name}-{version}.ypkg"
    with tarfile.open(ypkg_path, "w:gz") as tar:
        for item in sorted(build_dir.rglob("*")):
            arcname = item.relative_to(build_dir)
            tar.add(item, arcname=str(arcname))

    return str(ypkg_path)


class TestPackageInstallerBasic:

    def test_installer_inicializa_registro(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            installer = PackageInstaller(install_dir=tmpdir)
            assert installer.list_installed() == []

    def test_install_archivo_inexistente_falla(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            installer = PackageInstaller(install_dir=tmpdir)
            with pytest.raises(InstallError, match="no encontrado"):
                import asyncio
                asyncio.run(installer.install("/nonexistent/file.ypkg"))

    def test_install_formato_invalido_falla(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            invalid_file = Path(tmpdir) / "test.zip"
            invalid_file.write_text("not a ypkg")
            installer = PackageInstaller(install_dir=tmpdir)
            with pytest.raises(InstallError, match="Formato inválido"):
                import asyncio
                asyncio.run(installer.install(str(invalid_file)))

    def test_get_info_paquete_no_instalado_falla(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            installer = PackageInstaller(install_dir=tmpdir)
            with pytest.raises(InstallError):
                installer.get_info("nonexistent")


class TestPackageInstallerSignature:

    @pytest.mark.asyncio
    async def test_install_sin_metadata_falla(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_dir = Path(tmpdir) / "bad_build"
            bad_dir.mkdir()
            (bad_dir / "manifest.yml").write_text("name: test\nversion: 1.0.0\nauthor: x\ndescription: x\ntype: node\ncontainer:\n  image: x:1.0\n")
            # Sin build-metadata.json

            ypkg_path = Path(tmpdir) / "bad.ypkg"
            with tarfile.open(ypkg_path, "w:gz") as tar:
                tar.add(bad_dir / "manifest.yml", arcname="manifest.yml")

            installer = PackageInstaller(install_dir=str(Path(tmpdir) / "installed"))
            with pytest.raises(SignatureError):
                await installer.install(str(ypkg_path))

    @pytest.mark.asyncio
    async def test_install_firma_invalida_falla(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_dir = Path(tmpdir) / "bad_build"
            bad_dir.mkdir()
            (bad_dir / "manifest.yml").write_text("name: test\nversion: 1.0.0\nauthor: x\ndescription: x\ntype: node\ncontainer:\n  image: x:1.0\n")
            metadata = {"signature": "sha256:invalidsignaturexxx", "name": "test", "version": "1.0.0", "built_at": "x", "builder_version": "0.1"}
            (bad_dir / "build-metadata.json").write_text(json.dumps(metadata))

            ypkg_path = Path(tmpdir) / "tampered.ypkg"
            with tarfile.open(ypkg_path, "w:gz") as tar:
                for f in bad_dir.rglob("*"):
                    if f.is_file():
                        tar.add(f, arcname=str(f.relative_to(bad_dir)))

            installer = PackageInstaller(install_dir=str(Path(tmpdir) / "installed"))
            with pytest.raises(SignatureError):
                await installer.install(str(ypkg_path))


class TestPackageInstallerPermissions:

    @pytest.mark.asyncio
    async def test_permiso_denegado_impide_instalacion(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ypkg_path = create_fake_ypkg(tmpdir)

            async def deny_all(pkg_name, perms):
                return {"denied": list(perms)}

            installer = PackageInstaller(
                install_dir=str(Path(tmpdir) / "installed"),
                permission_callback=deny_all,
            )

            with pytest.raises(PermissionDeniedError):
                await installer.install(ypkg_path)

    @pytest.mark.asyncio
    async def test_permiso_concedido_permite_instalacion(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ypkg_path = create_fake_ypkg(tmpdir)

            async def grant_all(pkg_name, perms):
                return {"granted": list(perms), "denied": []}

            installer = PackageInstaller(
                install_dir=str(Path(tmpdir) / "installed"),
                permission_callback=grant_all,
            )

            with patch.object(installer, "_load_container_image", AsyncMock()):
                pkg_info = await installer.install(ypkg_path)
                assert pkg_info["name"] == "test-pkg"
