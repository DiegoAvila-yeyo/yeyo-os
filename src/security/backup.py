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


class BackupPriority(int, Enum):
    FLASH_MEMORY = 1
    CONFIG = 2
    USER_FILES = 3
    FULL_SYSTEM = 4


@dataclass
class BackupTarget:
    name: str
    priority: BackupPriority
    paths: list[str]
    interval_hours: int
    exclude_patterns: list[str] = field(default_factory=list)
    last_backup: Optional[str] = None


@dataclass
class BackupDestination:
    name: str
    repo_path: str
    medium_type: str
    is_offsite: bool = False
    initialized: bool = False


@dataclass
class BackupRecord:
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
    restic_binary: str = "restic"
    password_file: str = "/etc/yeyo/backup-password"
    metadata_file: str = "/var/lib/yeyo/backups.json"
    max_records: int = 1000


DEFAULT_TARGETS = [
    BackupTarget(
        name="flash_memory",
        priority=BackupPriority.FLASH_MEMORY,
        paths=["/var/lib/yeyo/flash_memory/", "/var/lib/yeyo/memories/"],
        interval_hours=1,
    ),
    BackupTarget(
        name="config",
        priority=BackupPriority.CONFIG,
        paths=["/etc/yeyo/", "/var/lib/yeyo/config/"],
        interval_hours=6,
        exclude_patterns=["*.tmp", "*.log"],
    ),
    BackupTarget(
        name="user_files",
        priority=BackupPriority.USER_FILES,
        paths=["/home/"],
        interval_hours=12,
        exclude_patterns=["*.tmp", "*.log", ".cache/", "node_modules/", ".venv/", "__pycache__/", "target/"],
    ),
    BackupTarget(
        name="full_system",
        priority=BackupPriority.FULL_SYSTEM,
        paths=["/"],
        interval_hours=24,
        exclude_patterns=[
            "/proc/*", "/sys/*", "/dev/*", "/tmp/*", "/run/*", "/mnt/*", "/media/*",
            "*.tmp", "*.log", ".cache/", "node_modules/", ".venv/", "__pycache__/", "target/",
        ],
    ),
]

DEFAULT_DESTINATIONS = [
    BackupDestination(name="local", repo_path="/backup/yeyo/local", medium_type="local"),
    BackupDestination(name="usb", repo_path="/mnt/usb-backup/yeyo", medium_type="usb"),
    BackupDestination(name="cloud", repo_path="s3:yeyo-backup/restic", medium_type="cloud", is_offsite=True),
]


class BackupManager:
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
        path = Path(self.config.metadata_file)
        if path.exists():
            try:
                data = json.loads(path.read_text())
                self._records = [BackupRecord(**r) for r in data.get("records", [])]
                for target_data in data.get("targets", []):
                    for target in self.targets:
                        if target.name == target_data.get("name"):
                            target.last_backup = target_data.get("last_backup")
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Error cargando metadatos de backup: {e}")

    def _save_metadata(self) -> None:
        path = Path(self.config.metadata_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "records": [asdict(r) for r in self._records[-self.config.max_records:]],
            "targets": [{"name": t.name, "last_backup": t.last_backup} for t in self.targets],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        path.write_text(json.dumps(data, indent=2))

    def init_repo(self, destination: BackupDestination) -> bool:
        logger.info(f"Inicializando repo restic: {destination.name} ({destination.repo_path})")
        try:
            result = subprocess.run(
                [self.config.restic_binary, "init", "--repo", destination.repo_path,
                 "--password-file", self.config.password_file],
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
        results = {}
        for dest in self.destinations:
            results[dest.name] = self.init_repo(dest)
        return results

    def backup(self, target: BackupTarget, destination: BackupDestination) -> BackupRecord:
        record_id = f"bk-{target.name}-{destination.name}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        record = BackupRecord(
            id=record_id,
            target_name=target.name,
            destination_name=destination.name,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        logger.info(f"Iniciando backup: {target.name} -> {destination.name} (prioridad: {target.priority.name})")

        cmd = [
            self.config.restic_binary, "backup",
            "--repo", destination.repo_path,
            "--password-file", self.config.password_file,
            "--json", "--tag", target.name,
            "--tag", f"priority-{target.priority.value}",
        ]
        for pattern in target.exclude_patterns:
            cmd.extend(["--exclude", pattern])
        cmd.extend(target.paths)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            record.completed_at = datetime.now(timezone.utc).isoformat()
            if result.returncode == 0:
                record.success = True
                target.last_backup = record.completed_at
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
                logger.info(f"Backup completado: {record_id} ({record.files_new} nuevos, {record.files_changed} modificados)")
            else:
                record.success = False
                record.error = result.stderr
                logger.error(f"Backup fallo: {record_id} -- {result.stderr}")
        except subprocess.TimeoutExpired:
            record.success = False
            record.error = "Timeout (>1h)"
            record.completed_at = datetime.now(timezone.utc).isoformat()
        except FileNotFoundError:
            record.success = False
            record.error = "restic no encontrado"
            record.completed_at = datetime.now(timezone.utc).isoformat()

        self._records.append(record)
        self._save_metadata()
        return record

    def run_scheduled(self) -> list[BackupRecord]:
        records = []
        now = datetime.now(timezone.utc)
        sorted_targets = sorted(self.targets, key=lambda t: t.priority.value)
        for target in sorted_targets:
            if self._needs_backup(target, now):
                for dest in self.destinations:
                    if dest.initialized:
                        record = self.backup(target, dest)
                        records.append(record)
        return records

    def _needs_backup(self, target: BackupTarget, now: datetime) -> bool:
        if target.last_backup is None:
            return True
        try:
            last = datetime.fromisoformat(target.last_backup)
            elapsed = now - last
            return elapsed >= timedelta(hours=target.interval_hours)
        except (ValueError, TypeError):
            return True

    def restore(self, destination: BackupDestination, snapshot_id: str, target_path: str) -> bool:
        logger.info(f"Restaurando {snapshot_id} de {destination.name} -> {target_path}")
        try:
            result = subprocess.run(
                [self.config.restic_binary, "restore", snapshot_id,
                 "--repo", destination.repo_path,
                 "--password-file", self.config.password_file,
                 "--target", target_path],
                capture_output=True, text=True, timeout=3600,
            )
            if result.returncode == 0:
                logger.info(f"Restauracion completada: {snapshot_id}")
                return True
            else:
                logger.error(f"Restauracion fallo: {result.stderr}")
                return False
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.error(f"Error restaurando: {e}")
            return False

    def get_records(self) -> list[BackupRecord]:
        return self._records.copy()

    def get_status(self) -> dict:
        return {
            "targets": [
                {
                    "name": t.name, "priority": t.priority.name,
                    "interval_hours": t.interval_hours,
                    "last_backup": t.last_backup,
                    "needs_backup": self._needs_backup(t, datetime.now(timezone.utc)),
                }
                for t in sorted(self.targets, key=lambda t: t.priority.value)
            ],
            "destinations": [
                {"name": d.name, "medium_type": d.medium_type, "is_offsite": d.is_offsite, "initialized": d.initialized}
                for d in self.destinations
            ],
            "total_backups": len(self._records),
            "successful_backups": sum(1 for r in self._records if r.success),
        }

    def verify_321_rule(self) -> dict:
        media_types = set(d.medium_type for d in self.destinations if d.initialized)
        has_offsite = any(d.is_offsite and d.initialized for d in self.destinations)
        copies = len([d for d in self.destinations if d.initialized])
        return {
            "copies": copies,
            "copies_ok": copies >= 3,
            "media_types": list(media_types),
            "media_ok": len(media_types) >= 2,
            "offsite": has_offsite,
            "offsite_ok": has_offsite,
            "rule_satisfied": copies >= 3 and len(media_types) >= 2 and has_offsite,
        }
