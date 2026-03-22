"""
YeyoOS — Package Auto-Update System
Micro-fase 4.9 — Capa 4: Sistema Nervioso

Sistema de actualización de paquetes con rollback automático.
Crea snapshot antes de actualizar. Si falla health check, hace rollback.
"""

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Callable, Awaitable


class UpdateError(Exception):
    """Error durante la actualización de un paquete."""
    pass


class RollbackError(Exception):
    """Error durante el rollback de un paquete."""
    pass


HealthCheckFn = Callable[[str], Awaitable[bool]]


class PackageUpdater:
    """Gestor de actualizaciones de paquetes con rollback."""

    def __init__(
        self,
        install_dir: str = "installed_packages",
        snapshots_dir: str = "snapshots",
        health_check: Optional[HealthCheckFn] = None,
    ):
        self.install_dir = Path(install_dir)
        self.snapshots_dir = Path(snapshots_dir)
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self.health_check = health_check
        self._available_updates: dict[str, dict] = {}
        self._update_history: list[dict] = []

    def register_available_update(
        self, package_name: str, new_version: str, ypkg_path: str
    ) -> None:
        """Registra una actualización disponible para un paquete."""
        self._available_updates[package_name] = {
            "package_name": package_name,
            "new_version": new_version,
            "ypkg_path": ypkg_path,
            "discovered_at": datetime.now(timezone.utc).isoformat(),
        }

    async def check_updates(self) -> list[dict]:
        """Retorna la lista de actualizaciones disponibles."""
        return list(self._available_updates.values())

    async def update(self, package_name: str) -> dict:
        """
        Actualiza un paquete:
        1. Verificar que hay update disponible
        2. Crear snapshot del estado actual
        3. Instalar nueva versión
        4. Ejecutar health check
        5. Si falla: rollback automático
        """
        if package_name not in self._available_updates:
            raise UpdateError(
                f"No hay actualización disponible para '{package_name}'"
            )

        update_info = self._available_updates[package_name]
        pkg_dir = self.install_dir / package_name

        if not pkg_dir.exists():
            raise UpdateError(f"Paquete '{package_name}' no está instalado")

        snapshot_id = self._create_snapshot(package_name)

        try:
            self._apply_update(package_name, update_info)

            if self.health_check:
                is_healthy = await self.health_check(package_name)
                if not is_healthy:
                    await self.rollback(package_name)
                    raise UpdateError(
                        f"Health check falló para '{package_name}'. "
                        f"Rollback automático ejecutado."
                    )

            del self._available_updates[package_name]

            result = {
                "package_name": package_name,
                "new_version": update_info["new_version"],
                "status": "updated",
                "snapshot_id": snapshot_id,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            self._update_history.append(result)
            return result

        except UpdateError:
            raise
        except Exception as e:
            await self.rollback(package_name)
            raise UpdateError(
                f"Error actualizando '{package_name}': {e}. Rollback ejecutado."
            )

    def _create_snapshot(self, package_name: str) -> str:
        """Crea un snapshot del estado actual del paquete."""
        pkg_dir = self.install_dir / package_name
        if not pkg_dir.exists():
            raise UpdateError(f"No se puede crear snapshot: '{package_name}' no existe")

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        snapshot_id = f"{package_name}_{timestamp}"
        snapshot_dir = self.snapshots_dir / snapshot_id

        shutil.copytree(pkg_dir, snapshot_dir)

        metadata = {
            "package_name": package_name,
            "snapshot_id": snapshot_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        (snapshot_dir / ".snapshot-metadata.json").write_text(
            json.dumps(metadata, indent=2)
        )

        return snapshot_id

    def _apply_update(self, package_name: str, update_info: dict) -> None:
        """Aplica la actualización (simula instalación de nueva versión)."""
        pkg_dir = self.install_dir / package_name

        version_file = pkg_dir / "version.txt"
        version_file.write_text(update_info["new_version"])

        update_marker = pkg_dir / ".last-update.json"
        update_marker.write_text(json.dumps({
            "version": update_info["new_version"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }))

    async def rollback(self, package_name: str) -> dict:
        """Restaura un paquete a su versión anterior desde snapshot."""
        snapshots = self._get_snapshots(package_name)
        if not snapshots:
            raise RollbackError(
                f"No hay snapshots disponibles para '{package_name}'"
            )

        latest_snapshot = snapshots[-1]
        snapshot_dir = self.snapshots_dir / latest_snapshot

        pkg_dir = self.install_dir / package_name
        if pkg_dir.exists():
            shutil.rmtree(pkg_dir)

        shutil.copytree(snapshot_dir, pkg_dir)

        snapshot_metadata_file = pkg_dir / ".snapshot-metadata.json"
        if snapshot_metadata_file.exists():
            snapshot_metadata_file.unlink()

        return {
            "package_name": package_name,
            "restored_from": latest_snapshot,
            "status": "rolled_back",
            "rolled_back_at": datetime.now(timezone.utc).isoformat(),
        }

    def _get_snapshots(self, package_name: str) -> list[str]:
        """Obtiene snapshots disponibles para un paquete, ordenados por fecha."""
        if not self.snapshots_dir.exists():
            return []
        snapshots = [
            d.name
            for d in sorted(self.snapshots_dir.iterdir())
            if d.is_dir() and d.name.startswith(f"{package_name}_")
        ]
        return snapshots

    def get_update_history(self) -> list[dict]:
        """Retorna el historial de actualizaciones."""
        return list(self._update_history)

    def list_snapshots(self, package_name: str) -> list[str]:
        """Lista snapshots disponibles para un paquete."""
        return self._get_snapshots(package_name)
