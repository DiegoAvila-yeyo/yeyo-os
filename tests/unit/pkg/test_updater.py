"""Tests para PackageUpdater — Micro-fase 4.9"""

import os
import json
import pytest
import tempfile
from pathlib import Path
from src.pkg.updater import PackageUpdater, UpdateError, RollbackError


def setup_package_dir(base_dir: str, pkg_name: str, version: str = "1.0.0") -> str:
    """Crea directorio de paquete simulado."""
    install_dir = os.path.join(base_dir, "installed")
    pkg_dir = os.path.join(install_dir, pkg_name)
    os.makedirs(pkg_dir, exist_ok=True)
    Path(pkg_dir, "version.txt").write_text(version)
    Path(pkg_dir, "manifest.yml").write_text(f"name: {pkg_name}\nversion: {version}")
    return install_dir


class TestPackageUpdaterBasico:

    @pytest.mark.asyncio
    async def test_check_updates_vacio(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            updater = PackageUpdater(
                install_dir=os.path.join(tmpdir, "installed"),
                snapshots_dir=os.path.join(tmpdir, "snapshots"),
            )
            updates = await updater.check_updates()
            assert updates == []

    @pytest.mark.asyncio
    async def test_register_available_update(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            updater = PackageUpdater(
                install_dir=os.path.join(tmpdir, "installed"),
                snapshots_dir=os.path.join(tmpdir, "snapshots"),
            )
            updater.register_available_update("mi-pkg", "2.0.0", "/path/to/pkg.ypkg")
            updates = await updater.check_updates()
            assert len(updates) == 1
            assert updates[0]["new_version"] == "2.0.0"

    @pytest.mark.asyncio
    async def test_update_sin_update_disponible_falla(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            updater = PackageUpdater(
                install_dir=os.path.join(tmpdir, "installed"),
                snapshots_dir=os.path.join(tmpdir, "snapshots"),
            )
            with pytest.raises(UpdateError, match="No hay actualización"):
                await updater.update("pkg-sin-update")

    @pytest.mark.asyncio
    async def test_update_paquete_no_instalado_falla(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            updater = PackageUpdater(
                install_dir=os.path.join(tmpdir, "installed"),
                snapshots_dir=os.path.join(tmpdir, "snapshots"),
            )
            updater.register_available_update("no-instalado", "2.0.0", "/fake")
            with pytest.raises(UpdateError, match="no está instalado"):
                await updater.update("no-instalado")


class TestPackageUpdaterSnapshot:

    def test_crear_snapshot(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            install_dir = setup_package_dir(tmpdir, "mi-pkg")
            updater = PackageUpdater(
                install_dir=install_dir,
                snapshots_dir=os.path.join(tmpdir, "snapshots"),
            )
            snapshot_id = updater._create_snapshot("mi-pkg")
            assert "mi-pkg" in snapshot_id
            snapshot_dir = Path(tmpdir) / "snapshots" / snapshot_id
            assert snapshot_dir.exists()

    def test_listar_snapshots(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            install_dir = setup_package_dir(tmpdir, "mi-pkg")
            updater = PackageUpdater(
                install_dir=install_dir,
                snapshots_dir=os.path.join(tmpdir, "snapshots"),
            )
            updater._create_snapshot("mi-pkg")
            snapshots = updater.list_snapshots("mi-pkg")
            assert len(snapshots) >= 1


class TestPackageUpdaterUpdate:

    @pytest.mark.asyncio
    async def test_update_exitoso(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            install_dir = setup_package_dir(tmpdir, "mi-pkg")

            async def health_ok(name):
                return True

            updater = PackageUpdater(
                install_dir=install_dir,
                snapshots_dir=os.path.join(tmpdir, "snapshots"),
                health_check=health_ok,
            )
            updater.register_available_update("mi-pkg", "2.0.0", "/fake")
            result = await updater.update("mi-pkg")
            assert result["status"] == "updated"
            assert result["new_version"] == "2.0.0"

    @pytest.mark.asyncio
    async def test_update_con_health_check_falla_hace_rollback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            install_dir = setup_package_dir(tmpdir, "mi-pkg")

            async def health_fail(name):
                return False

            updater = PackageUpdater(
                install_dir=install_dir,
                snapshots_dir=os.path.join(tmpdir, "snapshots"),
                health_check=health_fail,
            )
            updater.register_available_update("mi-pkg", "2.0.0", "/fake")
            with pytest.raises(UpdateError, match="Health check"):
                await updater.update("mi-pkg")

            version_file = Path(install_dir) / "mi-pkg" / "version.txt"
            assert version_file.read_text() == "1.0.0"


class TestPackageUpdaterRollback:

    @pytest.mark.asyncio
    async def test_rollback_restaura_version_anterior(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            install_dir = setup_package_dir(tmpdir, "mi-pkg")
            updater = PackageUpdater(
                install_dir=install_dir,
                snapshots_dir=os.path.join(tmpdir, "snapshots"),
            )
            updater._create_snapshot("mi-pkg")

            version_file = Path(install_dir) / "mi-pkg" / "version.txt"
            version_file.write_text("2.0.0-broken")

            result = await updater.rollback("mi-pkg")
            assert result["status"] == "rolled_back"
            assert version_file.read_text() == "1.0.0"

    @pytest.mark.asyncio
    async def test_rollback_sin_snapshot_falla(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            install_dir = setup_package_dir(tmpdir, "sin-snapshot")
            updater = PackageUpdater(
                install_dir=install_dir,
                snapshots_dir=os.path.join(tmpdir, "snapshots"),
            )
            with pytest.raises(RollbackError, match="No hay snapshots"):
                await updater.rollback("sin-snapshot")
