## ═══════════════════════════════════════
## MICRO-FASE 4.9 — Auto-Update System
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 4.9-1 [VSCODE] — Sistema de auto-actualización con rollback

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 4.9 de Capa 4 (Sistema Nervioso): crear el sistema de auto-actualización de paquetes con soporte de rollback.

CONTEXTO:
- Micro-fases 4.0-4.8 completadas: paquetes, permisos, containers, pipelines, database
- Auto-update descarga nueva versión, crea snapshot, instala, verifica salud
- Si el health check falla: rollback automático a la versión anterior
- Snapshot/backup antes de cada actualización

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/pkg/updater.py:

   Ruta: ~/yeyo-os/src/pkg/updater.py
   Contenido:

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

2. Actualizar archivo src/pkg/__init__.py:

   Ruta: ~/yeyo-os/src/pkg/__init__.py
   Contenido:
   from .manifest import ManifestParser, PackageManifest
   from .builder import PackageBuilder, BuildError
   from .installer import PackageInstaller, InstallError, SignatureError, PermissionDeniedError
   from .database import PackageDatabase
   from .updater import PackageUpdater, UpdateError, RollbackError

3. Crear archivo tests/unit/pkg/test_updater.py:

   Ruta: ~/yeyo-os/tests/unit/pkg/test_updater.py
   Contenido:

   """Tests para Package Auto-Update System — Micro-fase 4.9"""

   import os
   import json
   import tempfile
   import pytest
   from pathlib import Path

   from src.pkg.updater import PackageUpdater, UpdateError, RollbackError


   @pytest.fixture
   def temp_dirs():
       with tempfile.TemporaryDirectory(prefix="yeyo-update-") as d:
           install_dir = os.path.join(d, "installed")
           snapshots_dir = os.path.join(d, "snapshots")
           os.makedirs(install_dir)
           os.makedirs(snapshots_dir)

           pkg_dir = os.path.join(install_dir, "test-pkg")
           os.makedirs(pkg_dir)
           Path(pkg_dir, "manifest.yml").write_text("name: test-pkg\nversion: 1.0.0")
           Path(pkg_dir, "version.txt").write_text("1.0.0")

           yield {
               "base": d,
               "install": install_dir,
               "snapshots": snapshots_dir,
               "pkg_dir": pkg_dir,
           }


   @pytest.fixture
   def updater(temp_dirs):
       return PackageUpdater(
           install_dir=temp_dirs["install"],
           snapshots_dir=temp_dirs["snapshots"],
       )


   class TestCheckUpdates:
       """Tests para verificación de actualizaciones."""

       @pytest.mark.asyncio
       async def test_no_updates_available(self, updater):
           updates = await updater.check_updates()
           assert updates == []

       @pytest.mark.asyncio
       async def test_register_and_check_update(self, updater):
           updater.register_available_update("test-pkg", "2.0.0", "/path/to/pkg.ypkg")
           updates = await updater.check_updates()
           assert len(updates) == 1
           assert updates[0]["new_version"] == "2.0.0"


   class TestUpdate:
       """Tests para actualización de paquetes."""

       @pytest.mark.asyncio
       async def test_update_installs_new_version(self, updater, temp_dirs):
           updater.register_available_update("test-pkg", "2.0.0", "/path/to/pkg.ypkg")
           result = await updater.update("test-pkg")
           assert result["status"] == "updated"
           assert result["new_version"] == "2.0.0"

           version = Path(temp_dirs["pkg_dir"], "version.txt").read_text()
           assert version == "2.0.0"

       @pytest.mark.asyncio
       async def test_update_creates_snapshot(self, updater, temp_dirs):
           updater.register_available_update("test-pkg", "2.0.0", "/path/to/pkg.ypkg")
           result = await updater.update("test-pkg")
           assert result["snapshot_id"] is not None

           snapshots = updater.list_snapshots("test-pkg")
           assert len(snapshots) >= 1

       @pytest.mark.asyncio
       async def test_update_no_available_raises(self, updater):
           with pytest.raises(UpdateError, match="No hay actualización"):
               await updater.update("test-pkg")

       @pytest.mark.asyncio
       async def test_update_not_installed_raises(self, updater):
           updater.register_available_update("nonexistent", "2.0.0", "/path")
           with pytest.raises(UpdateError, match="no está instalado"):
               await updater.update("nonexistent")

       @pytest.mark.asyncio
       async def test_failed_health_triggers_rollback(self, temp_dirs):
           async def failing_health(name):
               return False

           updater = PackageUpdater(
               install_dir=temp_dirs["install"],
               snapshots_dir=temp_dirs["snapshots"],
               health_check=failing_health,
           )
           updater.register_available_update("test-pkg", "2.0.0", "/path")

           with pytest.raises(UpdateError, match="Health check falló"):
               await updater.update("test-pkg")

           version = Path(temp_dirs["pkg_dir"], "version.txt").read_text()
           assert version == "1.0.0"

       @pytest.mark.asyncio
       async def test_successful_health_completes_update(self, temp_dirs):
           async def passing_health(name):
               return True

           updater = PackageUpdater(
               install_dir=temp_dirs["install"],
               snapshots_dir=temp_dirs["snapshots"],
               health_check=passing_health,
           )
           updater.register_available_update("test-pkg", "2.0.0", "/path")
           result = await updater.update("test-pkg")
           assert result["status"] == "updated"


   class TestRollback:
       """Tests para rollback."""

       @pytest.mark.asyncio
       async def test_rollback_restores_previous(self, updater, temp_dirs):
           updater.register_available_update("test-pkg", "2.0.0", "/path")
           await updater.update("test-pkg")

           result = await updater.rollback("test-pkg")
           assert result["status"] == "rolled_back"

           version = Path(temp_dirs["pkg_dir"], "version.txt").read_text()
           assert version == "1.0.0"

       @pytest.mark.asyncio
       async def test_rollback_no_snapshot_raises(self, updater):
           with pytest.raises(RollbackError, match="No hay snapshots"):
               await updater.rollback("test-pkg")

       @pytest.mark.asyncio
       async def test_snapshot_created_before_update(self, updater, temp_dirs):
           updater.register_available_update("test-pkg", "2.0.0", "/path")
           await updater.update("test-pkg")

           snapshots = updater.list_snapshots("test-pkg")
           assert len(snapshots) >= 1

           snapshot_dir = Path(temp_dirs["snapshots"]) / snapshots[0]
           assert snapshot_dir.exists()
           assert (snapshot_dir / "version.txt").exists()

       @pytest.mark.asyncio
       async def test_update_history_recorded(self, updater):
           updater.register_available_update("test-pkg", "2.0.0", "/path")
           await updater.update("test-pkg")

           history = updater.get_update_history()
           assert len(history) == 1
           assert history[0]["package_name"] == "test-pkg"

4. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/pkg/test_updater.py -v

VERIFICAR:
- [ ] Archivo src/pkg/updater.py existe con PackageUpdater
- [ ] update instala nueva versión correctamente
- [ ] Snapshot creado ANTES de la actualización
- [ ] Health check fallido dispara rollback automático
- [ ] Rollback restaura la versión anterior
- [ ] No hay update disponible lanza error
- [ ] Historial de actualizaciones registrado
- [ ] TODOS los tests pasan

SI FALLA:
- shutil.copytree: verificar que directorios existen
- Fixture async: usar pytest-asyncio
- Path operations: verificar que usa Path correctamente

NO HACER:
- No descargar paquetes de internet (simulado localmente)
- No implementar auto-discovery de updates (eso sería un registry server)
- No conectar con el installer real (integración posterior)

GATE: PackageUpdater actualiza paquetes con snapshot/rollback, health check funciona, restauración correcta, todos los tests pasan.
```
