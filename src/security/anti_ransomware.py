"""
YeyoOS — Anti-Ransomware
Micro-fase 6.6 — Capa 6: Sistema Inmune

Detecta comportamiento de ransomware:
- Cifrado masivo de archivos (>10 en <5s)
- Extensiones conocidas de ransomware
- Cambios de entropia (archivos cifrados tienen entropia alta)
Respuesta: pausa inmediata + snapshot + alerta.
"""

import math
import time
import logging
from collections import defaultdict
from datetime import datetime, timezone
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from threading import Lock

logger = logging.getLogger("yeyo.security.anti_ransomware")

RANSOMWARE_EXTENSIONS = {
    ".encrypted", ".locked", ".crypto", ".crypt",
    ".locky", ".cerber", ".zepto", ".thor",
    ".aaa", ".abc", ".zzz", ".micro", ".xxx",
    ".ttt", ".enc", ".crypted", ".crinf",
    ".r5a", ".XRNT", ".XTBL", ".R16M01D05",
    ".pzdc", ".good", ".LOL!", ".OMG!",
    ".rdm", ".rrk", ".encryptedRSA",
    ".crysis", ".dharma", ".wallet",
    ".onion", ".bip", ".combo", ".arrow",
}


@dataclass
class FileEvent:
    path: str
    event_type: str
    timestamp: float
    size: int = 0
    entropy: float = 0.0


@dataclass
class RansomwareAlert:
    timestamp: str
    alert_type: str
    severity: str
    details: str
    affected_files: list[str] = field(default_factory=list)
    entropy_avg: float = 0.0
    files_per_second: float = 0.0


@dataclass
class AntiRansomwareConfig:
    file_threshold: int = 10
    time_window_secs: float = 5.0
    entropy_threshold: float = 7.5
    watch_dirs: list[str] = field(default_factory=lambda: ["/home", "/var/lib/yeyo", "/etc/yeyo"])
    ignore_dirs: list[str] = field(default_factory=lambda: ["/tmp", "/proc", "/sys", "/dev"])


def calculate_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    byte_counts = defaultdict(int)
    for byte in data:
        byte_counts[byte] += 1
    length = len(data)
    entropy = 0.0
    for count in byte_counts.values():
        probability = count / length
        if probability > 0:
            entropy -= probability * math.log2(probability)
    return entropy


def calculate_file_entropy(filepath: str, sample_size: int = 4096) -> float:
    try:
        with open(filepath, "rb") as f:
            data = f.read(sample_size)
        return calculate_entropy(data)
    except (OSError, PermissionError):
        return 0.0


class RansomwareDetector:
    def __init__(self, config: Optional[AntiRansomwareConfig] = None):
        self.config = config or AntiRansomwareConfig()
        self._events: list[FileEvent] = []
        self._alerts: list[RansomwareAlert] = []
        self._lock = Lock()
        self._paused = False

    def on_file_event(self, path: str, event_type: str) -> Optional[RansomwareAlert]:
        if self._paused:
            return None
        for ignore_dir in self.config.ignore_dirs:
            if path.startswith(ignore_dir):
                return None

        now = time.time()
        entropy = calculate_file_entropy(path) if Path(path).exists() else 0.0

        event = FileEvent(path=path, event_type=event_type, timestamp=now, entropy=entropy)

        with self._lock:
            self._events.append(event)
            cutoff = now - self.config.time_window_secs
            self._events = [e for e in self._events if e.timestamp > cutoff]

        alert = self._check_patterns(event)
        if alert:
            self._alerts.append(alert)
            logger.critical(f"RANSOMWARE DETECTADO: {alert.details}")

        return alert

    def _check_patterns(self, latest_event: FileEvent) -> Optional[RansomwareAlert]:
        ext = Path(latest_event.path).suffix.lower()
        if ext in RANSOMWARE_EXTENSIONS:
            return RansomwareAlert(
                timestamp=datetime.now(timezone.utc).isoformat(),
                alert_type="known_extension",
                severity="critical",
                details=f"Extension de ransomware detectada: {ext} en {latest_event.path}",
                affected_files=[latest_event.path],
            )

        with self._lock:
            recent_events = [e for e in self._events if time.time() - e.timestamp < self.config.time_window_secs]

        if len(recent_events) > self.config.file_threshold:
            high_entropy_count = sum(1 for e in recent_events if e.entropy > self.config.entropy_threshold)
            files_per_sec = len(recent_events) / self.config.time_window_secs
            avg_entropy = sum(e.entropy for e in recent_events) / len(recent_events) if recent_events else 0.0

            if high_entropy_count > self.config.file_threshold // 2:
                return RansomwareAlert(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    alert_type="mass_encryption",
                    severity="critical",
                    details=(
                        f"Cifrado masivo detectado: {len(recent_events)} archivos "
                        f"en {self.config.time_window_secs}s con entropia alta (avg: {avg_entropy:.2f})"
                    ),
                    affected_files=[e.path for e in recent_events],
                    entropy_avg=avg_entropy,
                    files_per_second=files_per_sec,
                )

            if files_per_sec > self.config.file_threshold * 2:
                return RansomwareAlert(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    alert_type="rapid_modification",
                    severity="warning",
                    details=(
                        f"Modificacion rapida: {len(recent_events)} archivos "
                        f"en {self.config.time_window_secs}s ({files_per_sec:.1f}/s)"
                    ),
                    affected_files=[e.path for e in recent_events[-20:]],
                    files_per_second=files_per_sec,
                )

        return None

    def get_alerts(self) -> list[RansomwareAlert]:
        return self._alerts.copy()

    def get_recent_events(self) -> list[FileEvent]:
        with self._lock:
            return self._events.copy()

    def get_event_rate(self) -> float:
        with self._lock:
            if not self._events:
                return 0.0
            now = time.time()
            recent = [e for e in self._events if now - e.timestamp < 60]
            return len(recent) / 60.0

    def pause(self) -> None:
        self._paused = True
        logger.info("[ANTI-RANSOMWARE] Deteccion pausada")

    def resume(self) -> None:
        self._paused = False
        logger.info("[ANTI-RANSOMWARE] Deteccion reanudada")

    def is_paused(self) -> bool:
        return self._paused
