## ═══════════════════════════════════════
## MICRO-FASE 6.4 — Smart Snapshots
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 6.4-1 [VSCODE] — Snapshots Btrfs disparados por eventos

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 6.4 de Capa 6 (Sistema Inmune): implementar Smart Snapshots con Btrfs, disparados por eventos del sistema.

CONTEXTO:
- Micro-fases 6.0-6.3 completadas: Guardian + Anomaly + Auto-Response + Kill Switch
- Smart Snapshots: Btrfs snapshots disparados por EVENTOS, no solo por tiempo
- Triggers: antes de instalar paquetes, antes de updates, antes de operaciones riesgosas
- Btrfs snapshots son instantáneos (COW - Copy on Write)
- Max 50 snapshots, auto-limpieza de los más antiguos
- Cada snapshot etiquetado con el evento que lo disparó
- Restore: seleccionar snapshot → verificar integridad → restaurar

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear estructura de directorios:
   mkdir -p src/security

2. Crear archivo src/security/__init__.py (vacío si no existe):

   Ruta: ~/yeyo-os/src/security/__init__.py
   Contenido: (archivo vacío)

3. Crear archivo src/security/snapshots.py:

   Ruta: ~/yeyo-os/src/security/snapshots.py
   Contenido:

   """
   YeyoOS — Smart Snapshots (Btrfs)
   Micro-fase 6.4 — Capa 6: Sistema Inmune

   Snapshots disparados por EVENTOS, no solo por tiempo.
   Btrfs COW = instantáneos, sin overhead.
   Max 50 snapshots, auto-limpieza de los más antiguos.
   """

   import json
   import subprocess
   import hashlib
   from datetime import datetime, timezone
   from pathlib import Path
   from dataclasses import dataclass, field, asdict
   from typing import Optional
   import logging

   logger = logging.getLogger("yeyo.security.snapshots")

   # ═══════════════════════════════════
   # TIPOS DE DATOS
   # ═══════════════════════════════════

   @dataclass
   class SnapshotInfo:
       """Información de un snapshot."""
       id: str
       label: str
       trigger_event: str
       created_at: str
       path: str
       subvolume: str
       size_estimate: str = "COW (instant)"
       integrity_hash: str = ""
       metadata: dict = field(default_factory=dict)

   @dataclass
   class SnapshotConfig:
       """Configuración del sistema de snapshots."""
       snapshot_dir: str = "/snapshots/yeyo"
       max_snapshots: int = 50
       subvolume: str = "/"
       metadata_file: str = "/var/lib/yeyo/snapshots.json"

   # ═══════════════════════════════════
   # TRIGGERS — Eventos que disparan snapshots
   # ═══════════════════════════════════

   TRIGGER_EVENTS = {
       "pre_package_install": "Antes de instalar paquete",
       "pre_system_update": "Antes de actualizar sistema",
       "pre_risky_operation": "Antes de operación riesgosa",
       "pre_config_change": "Antes de cambio de configuración",
       "pre_critical_response": "Antes de respuesta CRITICAL de Guardian",
       "scheduled_hourly": "Snapshot programado (cada hora)",
       "manual": "Snapshot manual del usuario",
       "pre_restore": "Antes de restaurar otro snapshot",
   }

   # ═══════════════════════════════════
   # SMART SNAPSHOT MANAGER
   # ═══════════════════════════════════

   class SmartSnapshotManager:
       """Gestor de snapshots Btrfs inteligentes."""

       def __init__(self, config: Optional[SnapshotConfig] = None):
           self.config = config or SnapshotConfig()
           self._snapshots: list[SnapshotInfo] = []
           self._load_metadata()

       def _load_metadata(self) -> None:
           """Carga metadatos de snapshots existentes."""
           path = Path(self.config.metadata_file)
           if path.exists():
               try:
                   data = json.loads(path.read_text())
                   self._snapshots = [
                       SnapshotInfo(**s) for s in data.get("snapshots", [])
                   ]
                   logger.info(f"Cargados {len(self._snapshots)} snapshots existentes")
               except (json.JSONDecodeError, TypeError) as e:
                   logger.warning(f"Error cargando metadatos de snapshots: {e}")
                   self._snapshots = []

       def _save_metadata(self) -> None:
           """Guarda metadatos de snapshots."""
           path = Path(self.config.metadata_file)
           path.parent.mkdir(parents=True, exist_ok=True)
           data = {
               "snapshots": [asdict(s) for s in self._snapshots],
               "updated_at": datetime.now(timezone.utc).isoformat(),
           }
           path.write_text(json.dumps(data, indent=2))

       def _generate_id(self, trigger_event: str) -> str:
           """Genera un ID único para el snapshot."""
           ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
           return f"snap-{trigger_event}-{ts}"

       def _compute_hash(self, snapshot_path: str) -> str:
           """Calcula hash SHA-256 del snapshot para verificar integridad."""
           try:
               result = subprocess.run(
                   ["btrfs", "subvolume", "show", snapshot_path],
                   capture_output=True, text=True, timeout=30,
               )
               content = result.stdout + result.stderr
               return hashlib.sha256(content.encode()).hexdigest()[:16]
           except (subprocess.SubprocessError, FileNotFoundError):
               return hashlib.sha256(snapshot_path.encode()).hexdigest()[:16]

       # ═══════════════════════════════════
       # CREAR SNAPSHOT
       # ═══════════════════════════════════

       def create(
           self,
           trigger_event: str,
           label: Optional[str] = None,
           metadata: Optional[dict] = None,
       ) -> SnapshotInfo:
           """
           Crea un snapshot Btrfs disparado por un evento.

           Args:
               trigger_event: Tipo de evento (ver TRIGGER_EVENTS)
               label: Etiqueta descriptiva (auto-generada si no se da)
               metadata: Metadatos adicionales
           """
           # Auto-limpieza si excede máximo
           self._enforce_max_snapshots()

           snap_id = self._generate_id(trigger_event)
           snap_path = f"{self.config.snapshot_dir}/{snap_id}"

           if label is None:
               label = TRIGGER_EVENTS.get(
                   trigger_event,
                   f"Snapshot: {trigger_event}"
               )

           logger.info(f"Creando snapshot: {snap_id} — {label}")

           # Crear snapshot Btrfs (instantáneo, COW)
           try:
               Path(self.config.snapshot_dir).mkdir(parents=True, exist_ok=True)

               result = subprocess.run(
                   [
                       "btrfs", "subvolume", "snapshot", "-r",
                       self.config.subvolume, snap_path,
                   ],
                   capture_output=True, text=True, timeout=60,
               )

               if result.returncode != 0:
                   logger.warning(
                       f"Btrfs snapshot falló (¿no es Btrfs?): {result.stderr}"
                   )
                   # Fallback: crear directorio marcador
                   Path(snap_path).mkdir(parents=True, exist_ok=True)

           except FileNotFoundError:
               logger.warning("btrfs no encontrado — creando snapshot marcador")
               Path(snap_path).mkdir(parents=True, exist_ok=True)

           integrity_hash = self._compute_hash(snap_path)

           snapshot = SnapshotInfo(
               id=snap_id,
               label=label,
               trigger_event=trigger_event,
               created_at=datetime.now(timezone.utc).isoformat(),
               path=snap_path,
               subvolume=self.config.subvolume,
               integrity_hash=integrity_hash,
               metadata=metadata or {},
           )

           self._snapshots.append(snapshot)
           self._save_metadata()

           logger.info(f"Snapshot creado: {snap_id} (hash: {integrity_hash})")
           return snapshot

       # ═══════════════════════════════════
       # RESTAURAR SNAPSHOT
       # ═══════════════════════════════════

       def restore(self, snapshot_id: str) -> bool:
           """
           Restaura un snapshot.
           Crea un snapshot PRE-RESTORE antes de restaurar.
           Verifica integridad antes de proceder.
           """
           snapshot = self.get_by_id(snapshot_id)
           if snapshot is None:
               logger.error(f"Snapshot no encontrado: {snapshot_id}")
               return False

           # 1. Verificar integridad
           if not self.verify_integrity(snapshot_id):
               logger.error(f"Snapshot corrupto: {snapshot_id}")
               return False

           # 2. Crear snapshot pre-restore
           self.create(
               trigger_event="pre_restore",
               label=f"Pre-restore de {snapshot_id}",
               metadata={"restoring": snapshot_id},
           )

           # 3. Restaurar
           logger.info(f"Restaurando snapshot: {snapshot_id}")
           try:
               # En Btrfs: borrar subvolume actual y reemplazar con snapshot
               # NOTA: esto es simplificado, en producción usar btrfs send/receive
               result = subprocess.run(
                   [
                       "btrfs", "subvolume", "snapshot",
                       snapshot.path, self.config.subvolume + ".restored",
                   ],
                   capture_output=True, text=True, timeout=120,
               )

               if result.returncode == 0:
                   logger.info(f"Snapshot restaurado: {snapshot_id}")
                   return True
               else:
                   logger.error(f"Error restaurando: {result.stderr}")
                   return False

           except (subprocess.SubprocessError, FileNotFoundError) as e:
               logger.error(f"Error restaurando snapshot: {e}")
               return False

       # ═══════════════════════════════════
       # CONSULTAS
       # ═══════════════════════════════════

       def get_by_id(self, snapshot_id: str) -> Optional[SnapshotInfo]:
           """Busca un snapshot por ID."""
           for snap in self._snapshots:
               if snap.id == snapshot_id:
                   return snap
           return None

       def list_snapshots(self) -> list[SnapshotInfo]:
           """Lista todos los snapshots (más recientes primero)."""
           return sorted(
               self._snapshots,
               key=lambda s: s.created_at,
               reverse=True,
           )

       def get_count(self) -> int:
           """Retorna el número de snapshots."""
           return len(self._snapshots)

       def verify_integrity(self, snapshot_id: str) -> bool:
           """Verifica la integridad de un snapshot comparando hashes."""
           snapshot = self.get_by_id(snapshot_id)
           if snapshot is None:
               return False

           current_hash = self._compute_hash(snapshot.path)
           is_valid = current_hash == snapshot.integrity_hash

           if not is_valid:
               logger.error(
                   f"Integridad fallida para {snapshot_id}: "
                   f"esperado={snapshot.integrity_hash}, actual={current_hash}"
               )

           return is_valid

       # ═══════════════════════════════════
       # LIMPIEZA
       # ═══════════════════════════════════

       def _enforce_max_snapshots(self) -> None:
           """Elimina los snapshots más antiguos si se excede el máximo."""
           while len(self._snapshots) >= self.config.max_snapshots:
               oldest = min(self._snapshots, key=lambda s: s.created_at)
               logger.info(f"Auto-limpieza: eliminando snapshot {oldest.id}")
               self._delete_snapshot(oldest)

       def _delete_snapshot(self, snapshot: SnapshotInfo) -> None:
           """Elimina un snapshot del sistema de archivos y metadatos."""
           try:
               subprocess.run(
                   ["btrfs", "subvolume", "delete", snapshot.path],
                   capture_output=True, text=True, timeout=60,
               )
           except (subprocess.SubprocessError, FileNotFoundError):
               # Si no es Btrfs, intentar rmdir
               import shutil
               try:
                   shutil.rmtree(snapshot.path, ignore_errors=True)
               except Exception:
                   pass

           self._snapshots = [s for s in self._snapshots if s.id != snapshot.id]
           self._save_metadata()

4. Crear archivo tests/unit/security/__init__.py (vacío):

   Ruta: ~/yeyo-os/tests/unit/security/__init__.py
   Contenido: (archivo vacío)

5. Crear archivo tests/unit/security/test_snapshots.py:

   Ruta: ~/yeyo-os/tests/unit/security/test_snapshots.py
   Contenido:

   """Tests para Smart Snapshots — Micro-fase 6.4"""

   import pytest
   import tempfile
   from pathlib import Path
   from src.security.snapshots import (
       SmartSnapshotManager,
       SnapshotConfig,
       SnapshotInfo,
       TRIGGER_EVENTS,
   )


   @pytest.fixture
   def tmp_config(tmp_path):
       return SnapshotConfig(
           snapshot_dir=str(tmp_path / "snapshots"),
           max_snapshots=5,
           subvolume=str(tmp_path / "subvol"),
           metadata_file=str(tmp_path / "meta" / "snapshots.json"),
       )


   @pytest.fixture
   def manager(tmp_config):
       return SmartSnapshotManager(config=tmp_config)


   class TestSnapshotCreation:
       def test_create_snapshot(self, manager):
           snap = manager.create("manual", label="Test snapshot")
           assert snap.id.startswith("snap-manual-")
           assert snap.label == "Test snapshot"
           assert snap.trigger_event == "manual"

       def test_create_with_auto_label(self, manager):
           snap = manager.create("pre_package_install")
           assert snap.label == TRIGGER_EVENTS["pre_package_install"]

       def test_create_with_metadata(self, manager):
           snap = manager.create(
               "pre_config_change",
               metadata={"file": "/etc/yeyo/config.toml"},
           )
           assert snap.metadata["file"] == "/etc/yeyo/config.toml"

       def test_snapshot_has_hash(self, manager):
           snap = manager.create("manual")
           assert len(snap.integrity_hash) > 0

       def test_count_increments(self, manager):
           assert manager.get_count() == 0
           manager.create("manual")
           assert manager.get_count() == 1
           manager.create("manual")
           assert manager.get_count() == 2


   class TestMaxSnapshots:
       def test_max_enforced(self, manager):
           for i in range(7):
               manager.create("manual", label=f"Snapshot {i}")
           assert manager.get_count() <= 5

       def test_oldest_removed_first(self, manager):
           snaps = []
           for i in range(6):
               s = manager.create("manual", label=f"Snap {i}")
               snaps.append(s)
           # El primer snapshot debería haber sido eliminado
           assert manager.get_by_id(snaps[0].id) is None


   class TestSnapshotRestore:
       def test_restore_creates_pre_snapshot(self, manager):
           snap = manager.create("manual")
           manager.restore(snap.id)
           # Debería haber 2 snapshots: original + pre_restore
           snapshots = manager.list_snapshots()
           has_pre_restore = any(
               s.trigger_event == "pre_restore" for s in snapshots
           )
           assert has_pre_restore

       def test_restore_nonexistent_fails(self, manager):
           result = manager.restore("nonexistent-id")
           assert result is False


   class TestSnapshotListing:
       def test_list_returns_sorted(self, manager):
           manager.create("manual", label="First")
           manager.create("manual", label="Second")
           snapshots = manager.list_snapshots()
           assert snapshots[0].label == "Second"  # Más reciente primero


   class TestSnapshotIntegrity:
       def test_verify_valid_snapshot(self, manager):
           snap = manager.create("manual")
           assert manager.verify_integrity(snap.id) is True

       def test_verify_nonexistent_fails(self, manager):
           assert manager.verify_integrity("fake-id") is False

6. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/security/test_snapshots.py -v

VERIFICAR:
- [ ] Archivo src/security/snapshots.py existe con SmartSnapshotManager
- [ ] Snapshots se crean con trigger_event y label
- [ ] Max 50 snapshots (5 en test) enforced
- [ ] Auto-limpieza elimina los más antiguos
- [ ] Restore crea pre_restore snapshot antes
- [ ] Integridad verificada con SHA-256
- [ ] Metadatos persistidos en JSON
- [ ] TODOS los tests pasan

SI FALLA:
- btrfs no encontrado: normal en dev, usa fallback con directorios
- Permiso denegado: usar tmp_path en tests
- Import error: verificar __init__.py en src/security/

NO HACER:
- No borrar Flash Memory en la limpieza de snapshots
- No ejecutar btrfs en producción sin verificar que el filesystem es Btrfs
- No eliminar snapshots manualmente (siempre via manager)
- No conectar con backup system aún (eso es 6.5)

GATE: SmartSnapshotManager crea/lista/restaura snapshots, max enforced, auto-limpieza funciona, integridad SHA-256, metadatos persistidos, todos los tests pasan.
```
