## ═══════════════════════════════════════
## MICRO-FASE 6.5 — Backup System (3-2-1)
## Tipo: CLI | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 6.5-1 [CLI] — Sistema de backups cifrados con restic (regla 3-2-1)

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 6.5 de Capa 6 (Sistema Inmune): implementar el sistema de backups cifrados siguiendo la regla 3-2-1.

CONTEXTO:
- Micro-fases 6.0-6.4 completadas: Guardian + Anomaly + Auto-Response + Kill Switch + Snapshots
- Regla 3-2-1: 3 copias, 2 medios diferentes, 1 offsite
- Restic para cifrado AES-256 y deduplicación
- PRIORIDAD de backup:
  1. Flash Memory (cada 1h) — LO MÁS VALIOSO
  2. Config (cada 6h)
  3. User Files (cada 12h)
  4. Full System (cada 24h)
- Flash Memory es MÁS VALIOSA que el propio OS
- Destinos: local, USB, (opcional) cloud

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/security/backup.py:

   Ruta: ~/yeyo-os/src/security/backup.py
   Contenido:

   """
   YeyoOS — Backup System (Regla 3-2-1)
   Micro-fase 6.5 — Capa 6: Sistema Inmune

   3 copias, 2 medios diferentes, 1 offsite.
   Restic cifrado AES-256 con deduplicación.
   Flash Memory = LO MÁS VALIOSO. Se respalda cada hora.
   """

   import json
   import subprocess
   import logging
   from datetime import datetime, timezone, timedelta
   from pathlib import Path
   from dataclasses import dataclass, field, asdict
   from typing import Optional
   from enum import Enum

   logger = logging.getLogger("yeyo.security.backup")

   # ═══════════════════════════════════
   # PRIORIDADES DE BACKUP
   # ═══════════════════════════════════

   class BackupPriority(int, Enum):
       """Prioridad de backup — Flash Memory es lo primero."""
       FLASH_MEMORY = 1    # Cada 1h — LO MÁS VALIOSO
       CONFIG = 2           # Cada 6h
       USER_FILES = 3       # Cada 12h
       FULL_SYSTEM = 4      # Cada 24h

   # ═══════════════════════════════════
   # TIPOS DE DATOS
   # ═══════════════════════════════════

   @dataclass
   class BackupTarget:
       """Define qué respaldar."""
       name: str
       priority: BackupPriority
       paths: list[str]
       interval_hours: int
       exclude_patterns: list[str] = field(default_factory=list)
       last_backup: Optional[str] = None

   @dataclass
   class BackupDestination:
       """Define dónde respaldar."""
       name: str
       repo_path: str
       medium_type: str   # "local", "usb", "cloud"
       is_offsite: bool = False
       initialized: bool = False

   @dataclass
   class BackupRecord:
       """Registro de un backup ejecutado."""
       id: str
       target_name: str
       destination_name: str
       started_at: str
       completed_at: Optional[str] = None
       success: bool = False
       snapshot_id: Optional[str] = None
       size_bytes: int = 0
       files_new: int = 0
       files_changed: int = 0
       error: Optional[str] = None

   @dataclass
   class BackupConfig:
       """Configuración del sistema de backups."""
       restic_binary: str = "restic"
       password_file: str = "/etc/yeyo/backup-password"
       metadata_file: str = "/var/lib/yeyo/backups.json"
       max_records: int = 1000

   # ═══════════════════════════════════
   # TARGETS POR DEFECTO
   # ═══════════════════════════════════

   DEFAULT_TARGETS = [
       BackupTarget(
           name="flash_memory",
           priority=BackupPriority.FLASH_MEMORY,
           paths=[
               "/var/lib/yeyo/flash_memory/",
               "/var/lib/yeyo/memories/",
           ],
           interval_hours=1,
           exclude_patterns=[],
       ),
       BackupTarget(
           name="config",
           priority=BackupPriority.CONFIG,
           paths=[
               "/etc/yeyo/",
               "/var/lib/yeyo/config/",
           ],
           interval_hours=6,
           exclude_patterns=["*.tmp", "*.log"],
       ),
       BackupTarget(
           name="user_files",
           priority=BackupPriority.USER_FILES,
           paths=[
               "/home/",
           ],
           interval_hours=12,
           exclude_patterns=[
               "*.tmp", "*.log", ".cache/", "node_modules/",
               ".venv/", "__pycache__/", "target/",
           ],
       ),
       BackupTarget(
           name="full_system",
           priority=BackupPriority.FULL_SYSTEM,
           paths=["/"],
           interval_hours=24,
           exclude_patterns=[
               "/proc/*", "/sys/*", "/dev/*", "/tmp/*",
               "/run/*", "/mnt/*", "/media/*",
               "*.tmp", "*.log", ".cache/",
               "node_modules/", ".venv/", "__pycache__/", "target/",
           ],
       ),
   ]

   DEFAULT_DESTINATIONS = [
       BackupDestination(
           name="local",
           repo_path="/backup/yeyo/local",
           medium_type="local",
       ),
       BackupDestination(
           name="usb",
           repo_path="/mnt/usb-backup/yeyo",
           medium_type="usb",
       ),
       BackupDestination(
           name="cloud",
           repo_path="s3:yeyo-backup/restic",
           medium_type="cloud",
           is_offsite=True,
       ),
   ]

   # ═══════════════════════════════════
   # BACKUP MANAGER
   # ═══════════════════════════════════

   class BackupManager:
       """Gestor de backups 3-2-1 con restic."""

       def __init__(
           self,
           config: Optional[BackupConfig] = None,
           targets: Optional[list[BackupTarget]] = None,
           destinations: Optional[list[BackupDestination]] = None,
       ):
           self.config = config or BackupConfig()
           self.targets = targets or DEFAULT_TARGETS
           self.destinations = destinations or DEFAULT_DESTINATIONS
           self._records: list[BackupRecord] = []
           self._load_metadata()

       def _load_metadata(self) -> None:
           """Carga historial de backups."""
           path = Path(self.config.metadata_file)
           if path.exists():
               try:
                   data = json.loads(path.read_text())
                   self._records = [
                       BackupRecord(**r) for r in data.get("records", [])
                   ]
                   # Restaurar last_backup de targets
                   for target_data in data.get("targets", []):
                       for target in self.targets:
                           if target.name == target_data.get("name"):
                               target.last_backup = target_data.get("last_backup")
               except (json.JSONDecodeError, TypeError) as e:
                   logger.warning(f"Error cargando metadatos de backup: {e}")

       def _save_metadata(self) -> None:
           """Guarda historial de backups."""
           path = Path(self.config.metadata_file)
           path.parent.mkdir(parents=True, exist_ok=True)
           data = {
               "records": [asdict(r) for r in self._records[-self.config.max_records:]],
               "targets": [
                   {"name": t.name, "last_backup": t.last_backup}
                   for t in self.targets
               ],
               "updated_at": datetime.now(timezone.utc).isoformat(),
           }
           path.write_text(json.dumps(data, indent=2))

       # ═══════════════════════════════════
       # INICIALIZAR REPOSITORIOS RESTIC
       # ═══════════════════════════════════

       def init_repo(self, destination: BackupDestination) -> bool:
           """Inicializa un repositorio restic en un destino."""
           logger.info(f"Inicializando repo restic: {destination.name} ({destination.repo_path})")

           try:
               result = subprocess.run(
                   [
                       self.config.restic_binary, "init",
                       "--repo", destination.repo_path,
                       "--password-file", self.config.password_file,
                   ],
                   capture_output=True, text=True, timeout=120,
               )

               if result.returncode == 0 or "already initialized" in result.stderr:
                   destination.initialized = True
                   logger.info(f"Repo inicializado: {destination.name}")
                   return True
               else:
                   logger.error(f"Error init repo {destination.name}: {result.stderr}")
                   return False

           except (subprocess.SubprocessError, FileNotFoundError) as e:
               logger.error(f"Error ejecutando restic init: {e}")
               return False

       def init_all_repos(self) -> dict[str, bool]:
           """Inicializa todos los repositorios."""
           results = {}
           for dest in self.destinations:
               results[dest.name] = self.init_repo(dest)
           return results

       # ═══════════════════════════════════
       # EJECUTAR BACKUP
       # ═══════════════════════════════════

       def backup(
           self,
           target: BackupTarget,
           destination: BackupDestination,
       ) -> BackupRecord:
           """Ejecuta un backup de un target a un destino con restic."""
           record_id = f"bk-{target.name}-{destination.name}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

           record = BackupRecord(
               id=record_id,
               target_name=target.name,
               destination_name=destination.name,
               started_at=datetime.now(timezone.utc).isoformat(),
           )

           logger.info(
               f"Iniciando backup: {target.name} → {destination.name} "
               f"(prioridad: {target.priority.name})"
           )

           # Construir comando restic
           cmd = [
               self.config.restic_binary, "backup",
               "--repo", destination.repo_path,
               "--password-file", self.config.password_file,
               "--json",
               "--tag", target.name,
               "--tag", f"priority-{target.priority.value}",
           ]

           # Agregar exclusiones
           for pattern in target.exclude_patterns:
               cmd.extend(["--exclude", pattern])

           # Agregar paths
           cmd.extend(target.paths)

           try:
               result = subprocess.run(
                   cmd,
                   capture_output=True, text=True, timeout=3600,
               )

               record.completed_at = datetime.now(timezone.utc).isoformat()

               if result.returncode == 0:
                   record.success = True
                   target.last_backup = record.completed_at

                   # Parsear salida JSON de restic
                   try:
                       for line in result.stdout.strip().split("\n"):
                           if line.strip():
                               data = json.loads(line)
                               if data.get("message_type") == "summary":
                                   record.snapshot_id = data.get("snapshot_id")
                                   record.files_new = data.get("files_new", 0)
                                   record.files_changed = data.get("files_changed", 0)
                                   record.size_bytes = data.get("data_added", 0)
                   except (json.JSONDecodeError, KeyError):
                       pass

                   logger.info(
                       f"Backup completado: {record_id} "
                       f"({record.files_new} nuevos, {record.files_changed} modificados)"
                   )
               else:
                   record.success = False
                   record.error = result.stderr
                   logger.error(f"Backup falló: {record_id} — {result.stderr}")

           except subprocess.TimeoutExpired:
               record.success = False
               record.error = "Timeout (>1h)"
               record.completed_at = datetime.now(timezone.utc).isoformat()
               logger.error(f"Backup timeout: {record_id}")

           except FileNotFoundError:
               record.success = False
               record.error = "restic no encontrado"
               record.completed_at = datetime.now(timezone.utc).isoformat()
               logger.error(f"restic no encontrado para: {record_id}")

           self._records.append(record)
           self._save_metadata()

           return record

       # ═══════════════════════════════════
       # BACKUP AUTOMÁTICO POR PRIORIDAD
       # ═══════════════════════════════════

       def run_scheduled(self) -> list[BackupRecord]:
           """
           Ejecuta backups según prioridad y schedule.
           Flash Memory primero, siempre.
           """
           records = []
           now = datetime.now(timezone.utc)

           # Ordenar por prioridad (Flash Memory = 1 = primero)
           sorted_targets = sorted(self.targets, key=lambda t: t.priority.value)

           for target in sorted_targets:
               if self._needs_backup(target, now):
                   for dest in self.destinations:
                       if dest.initialized:
                           record = self.backup(target, dest)
                           records.append(record)

           return records

       def _needs_backup(self, target: BackupTarget, now: datetime) -> bool:
           """Verifica si un target necesita backup."""
           if target.last_backup is None:
               return True

           try:
               last = datetime.fromisoformat(target.last_backup)
               elapsed = now - last
               return elapsed >= timedelta(hours=target.interval_hours)
           except (ValueError, TypeError):
               return True

       # ═══════════════════════════════════
       # RESTAURAR
       # ═══════════════════════════════════

       def restore(
           self,
           destination: BackupDestination,
           snapshot_id: str,
           target_path: str,
       ) -> bool:
           """Restaura un snapshot de restic."""
           logger.info(f"Restaurando {snapshot_id} de {destination.name} → {target_path}")

           try:
               result = subprocess.run(
                   [
                       self.config.restic_binary, "restore",
                       snapshot_id,
                       "--repo", destination.repo_path,
                       "--password-file", self.config.password_file,
                       "--target", target_path,
                   ],
                   capture_output=True, text=True, timeout=3600,
               )

               if result.returncode == 0:
                   logger.info(f"Restauración completada: {snapshot_id}")
                   return True
               else:
                   logger.error(f"Restauración falló: {result.stderr}")
                   return False

           except (subprocess.SubprocessError, FileNotFoundError) as e:
               logger.error(f"Error restaurando: {e}")
               return False

       # ═══════════════════════════════════
       # CONSULTAS
       # ═══════════════════════════════════

       def get_records(self) -> list[BackupRecord]:
           """Retorna historial de backups."""
           return self._records.copy()

       def get_status(self) -> dict:
           """Retorna estado de todos los targets y destinos."""
           return {
               "targets": [
                   {
                       "name": t.name,
                       "priority": t.priority.name,
                       "interval_hours": t.interval_hours,
                       "last_backup": t.last_backup,
                       "needs_backup": self._needs_backup(t, datetime.now(timezone.utc)),
                   }
                   for t in sorted(self.targets, key=lambda t: t.priority.value)
               ],
               "destinations": [
                   {
                       "name": d.name,
                       "medium_type": d.medium_type,
                       "is_offsite": d.is_offsite,
                       "initialized": d.initialized,
                   }
                   for d in self.destinations
               ],
               "total_backups": len(self._records),
               "successful_backups": sum(1 for r in self._records if r.success),
           }

       def verify_321_rule(self) -> dict:
           """Verifica que se cumple la regla 3-2-1."""
           media_types = set(d.medium_type for d in self.destinations if d.initialized)
           has_offsite = any(d.is_offsite and d.initialized for d in self.destinations)

           return {
               "copies": len([d for d in self.destinations if d.initialized]),
               "copies_ok": len([d for d in self.destinations if d.initialized]) >= 3,
               "media_types": list(media_types),
               "media_ok": len(media_types) >= 2,
               "offsite": has_offsite,
               "offsite_ok": has_offsite,
               "rule_satisfied": (
                   len([d for d in self.destinations if d.initialized]) >= 3
                   and len(media_types) >= 2
                   and has_offsite
               ),
           }

2. Crear archivo tests/unit/security/test_backup.py:

   Ruta: ~/yeyo-os/tests/unit/security/test_backup.py
   Contenido:

   """Tests para Backup System 3-2-1 — Micro-fase 6.5"""

   import pytest
   from pathlib import Path
   from src.security.backup import (
       BackupManager,
       BackupConfig,
       BackupTarget,
       BackupDestination,
       BackupPriority,
       DEFAULT_TARGETS,
   )


   @pytest.fixture
   def tmp_config(tmp_path):
       return BackupConfig(
           restic_binary="restic",
           password_file=str(tmp_path / "password"),
           metadata_file=str(tmp_path / "backups.json"),
       )


   @pytest.fixture
   def tmp_destinations(tmp_path):
       return [
           BackupDestination(
               name="local",
               repo_path=str(tmp_path / "repo-local"),
               medium_type="local",
               initialized=True,
           ),
           BackupDestination(
               name="usb",
               repo_path=str(tmp_path / "repo-usb"),
               medium_type="usb",
               initialized=True,
           ),
           BackupDestination(
               name="cloud",
               repo_path=str(tmp_path / "repo-cloud"),
               medium_type="cloud",
               is_offsite=True,
               initialized=True,
           ),
       ]


   @pytest.fixture
   def manager(tmp_config, tmp_destinations):
       return BackupManager(
           config=tmp_config,
           destinations=tmp_destinations,
       )


   class TestBackupPriority:
       def test_flash_memory_is_highest_priority(self):
           assert BackupPriority.FLASH_MEMORY.value == 1

       def test_priority_order(self):
           assert BackupPriority.FLASH_MEMORY < BackupPriority.CONFIG
           assert BackupPriority.CONFIG < BackupPriority.USER_FILES
           assert BackupPriority.USER_FILES < BackupPriority.FULL_SYSTEM

       def test_flash_memory_backed_up_first(self):
           sorted_targets = sorted(DEFAULT_TARGETS, key=lambda t: t.priority.value)
           assert sorted_targets[0].name == "flash_memory"

       def test_flash_memory_interval_1h(self):
           fm = next(t for t in DEFAULT_TARGETS if t.name == "flash_memory")
           assert fm.interval_hours == 1


   class TestBackupStatus:
       def test_get_status(self, manager):
           status = manager.get_status()
           assert "targets" in status
           assert "destinations" in status
           assert status["total_backups"] == 0

       def test_321_rule_verification(self, manager):
           rule = manager.verify_321_rule()
           assert rule["copies"] == 3
           assert rule["copies_ok"] is True
           assert rule["media_ok"] is True
           assert rule["offsite_ok"] is True
           assert rule["rule_satisfied"] is True

       def test_321_fails_without_offsite(self, tmp_config):
           dests = [
               BackupDestination(
                   name="local1", repo_path="/tmp/r1",
                   medium_type="local", initialized=True,
               ),
               BackupDestination(
                   name="local2", repo_path="/tmp/r2",
                   medium_type="local", initialized=True,
               ),
           ]
           mgr = BackupManager(config=tmp_config, destinations=dests)
           rule = mgr.verify_321_rule()
           assert rule["rule_satisfied"] is False
           assert rule["offsite_ok"] is False


   class TestBackupScheduling:
       def test_needs_backup_when_never_done(self, manager):
           fm = next(t for t in manager.targets if t.name == "flash_memory")
           assert fm.last_backup is None

       def test_flash_memory_always_backed_up_first(self, manager):
           sorted_targets = sorted(manager.targets, key=lambda t: t.priority.value)
           assert sorted_targets[0].name == "flash_memory"


   class TestBackupRecords:
       def test_records_initially_empty(self, manager):
           assert len(manager.get_records()) == 0

3. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/security/test_backup.py -v

VERIFICAR:
- [ ] Archivo src/security/backup.py existe con BackupManager
- [ ] Flash Memory es prioridad 1 (cada 1h)
- [ ] Regla 3-2-1 verificable: 3 copias, 2 medios, 1 offsite
- [ ] Restic cifrado AES-256 (via password-file)
- [ ] Backup incremental (deduplicación de restic)
- [ ] Restore funciona con snapshot_id
- [ ] Flash Memory se respalda PRIMERO siempre
- [ ] TODOS los tests pasan

SI FALLA:
- restic no instalado: `sudo apt install restic` (para producción)
- Tests no ejecutan restic real: verifican lógica, no el binario
- Import error: verificar __init__.py en src/security/

NO HACER:
- No borrar Flash Memory NUNCA, bajo ninguna circunstancia
- No usar cifrado débil (SIEMPRE AES-256 via restic)
- No hacer backup sin cifrar
- No saltarse Flash Memory en el schedule

GATE: BackupManager respalda por prioridad (Flash Memory primero), regla 3-2-1 verificable, restic cifrado, restore funciona, todos los tests pasan.
```
