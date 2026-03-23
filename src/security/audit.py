"""
YeyoOS — Security Audit System
Micro-fase 6.10 — Capa 6: Sistema Inmune

Log append-only con cadena SHA-256.
NO UPDATE, NO DELETE — cada entrada es inmutable.
"""

import csv
import hashlib
import io
import json
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional
from threading import Lock

logger = logging.getLogger("yeyo.security.audit")


@dataclass
class AuditEntry:
    sequence: int
    timestamp: str
    actor: str
    actor_type: str
    action: str
    description: str
    resource: str
    result: str
    previous_hash: str
    entry_hash: str
    metadata: dict = field(default_factory=dict)


@dataclass
class AuditConfig:
    log_file: str = "/var/log/yeyo/audit/audit.jsonl"
    max_entries_memory: int = 10000
    hash_algorithm: str = "sha256"


class AuditTrail:
    GENESIS_HASH = "0" * 64

    def __init__(self, config: Optional[AuditConfig] = None):
        self.config = config or AuditConfig()
        self._entries: list[AuditEntry] = []
        self._lock = Lock()
        self._sequence = 0
        self._last_hash = self.GENESIS_HASH
        self._load_existing()

    def _load_existing(self) -> None:
        path = Path(self.config.log_file)
        if not path.exists():
            return
        try:
            with open(path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        entry = AuditEntry(**data)
                        self._entries.append(entry)
                        self._sequence = entry.sequence
                        self._last_hash = entry.entry_hash
                    except (json.JSONDecodeError, TypeError):
                        continue
            logger.info(f"Cargadas {len(self._entries)} entradas de audit trail")
        except OSError as e:
            logger.warning(f"Error cargando audit trail: {e}")

    def append(self, actor: str, actor_type: str, action: str, description: str, resource: str, result: str, metadata: Optional[dict] = None) -> AuditEntry:
        with self._lock:
            self._sequence += 1
            timestamp = datetime.now(timezone.utc).isoformat()
            previous_hash = self._last_hash
            entry_data = {
                "sequence": self._sequence, "timestamp": timestamp,
                "actor": actor, "actor_type": actor_type,
                "action": action, "description": description,
                "resource": resource, "result": result,
                "previous_hash": previous_hash, "metadata": metadata or {},
            }
            entry_hash = self._compute_hash(entry_data)
            entry_data["entry_hash"] = entry_hash
            entry = AuditEntry(**entry_data)
            self._entries.append(entry)
            self._last_hash = entry_hash
            if len(self._entries) > self.config.max_entries_memory:
                self._entries = self._entries[-self.config.max_entries_memory:]
            self._persist_entry(entry)
            logger.debug(f"Audit #{self._sequence}: [{action}] {actor} -> {resource} = {result}")
            return entry

    def _compute_hash(self, data: dict) -> str:
        content = json.dumps(data, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _persist_entry(self, entry: AuditEntry) -> None:
        try:
            path = Path(self.config.log_file)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a") as f:
                f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
        except OSError as e:
            logger.error(f"Error persistiendo audit entry: {e}")

    def verify_chain(self) -> tuple[bool, Optional[int]]:
        expected_prev_hash = self.GENESIS_HASH
        for entry in self._entries:
            if entry.previous_hash != expected_prev_hash:
                logger.error(f"Cadena rota en #{entry.sequence}")
                return False, entry.sequence
            entry_data = {
                "sequence": entry.sequence, "timestamp": entry.timestamp,
                "actor": entry.actor, "actor_type": entry.actor_type,
                "action": entry.action, "description": entry.description,
                "resource": entry.resource, "result": entry.result,
                "previous_hash": entry.previous_hash, "metadata": entry.metadata,
            }
            computed_hash = self._compute_hash(entry_data)
            if computed_hash != entry.entry_hash:
                logger.error(f"Hash invalido en #{entry.sequence}")
                return False, entry.sequence
            expected_prev_hash = entry.entry_hash
        return True, None

    def search(self, actor: Optional[str] = None, action: Optional[str] = None, resource: Optional[str] = None, result: Optional[str] = None, from_date: Optional[str] = None, to_date: Optional[str] = None, limit: int = 100) -> list[AuditEntry]:
        results = []
        for entry in reversed(self._entries):
            if actor and actor.lower() not in entry.actor.lower():
                continue
            if action and action.lower() != entry.action.lower():
                continue
            if resource and resource.lower() not in entry.resource.lower():
                continue
            if result and result.lower() != entry.result.lower():
                continue
            if from_date and entry.timestamp < from_date:
                continue
            if to_date and entry.timestamp > to_date:
                continue
            results.append(entry)
            if len(results) >= limit:
                break
        return results

    def export_json(self, entries: Optional[list[AuditEntry]] = None) -> str:
        data = entries or self._entries
        return json.dumps([asdict(e) for e in data], indent=2, ensure_ascii=False)

    def export_csv(self, entries: Optional[list[AuditEntry]] = None) -> str:
        data = entries or self._entries
        if not data:
            return ""
        output = io.StringIO()
        fields = ["sequence", "timestamp", "actor", "actor_type", "action", "description", "resource", "result", "entry_hash"]
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for entry in data:
            row = {f: getattr(entry, f) for f in fields}
            writer.writerow(row)
        return output.getvalue()

    def get_entries(self, limit: int = 100) -> list[AuditEntry]:
        return list(reversed(self._entries[-limit:]))

    def get_count(self) -> int:
        return self._sequence

    def get_last_entry(self) -> Optional[AuditEntry]:
        return self._entries[-1] if self._entries else None
