## ═══════════════════════════════════════
## MICRO-FASE 6.6 — Anti-Ransomware
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 6.6-1 [VSCODE] — Detección y prevención de ransomware

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 6.6 de Capa 6 (Sistema Inmune): implementar detección y prevención de comportamiento tipo ransomware.

CONTEXTO:
- Micro-fases 6.0-6.5 completadas: Guardian + Anomaly + Auto-Response + Kill Switch + Snapshots + Backup
- Anti-ransomware detecta: cifrado masivo de archivos, patrones de escritura inusuales, extensiones conocidas
- Respuesta: pausa inmediata, snapshot, alerta
- Monitorea file system events (inotify en Linux)
- Umbral: >10 archivos modificados en <5 segundos con cambio de entropía
- Integra con Guardian para respuesta automática

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/security/anti_ransomware.py:

   Ruta: ~/yeyo-os/src/security/anti_ransomware.py
   Contenido:

   """
   YeyoOS — Anti-Ransomware
   Micro-fase 6.6 — Capa 6: Sistema Inmune

   Detecta comportamiento de ransomware:
   - Cifrado masivo de archivos (>10 en <5s)
   - Extensiones conocidas de ransomware
   - Cambios de entropía (archivos cifrados tienen entropía alta)
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

   # ═══════════════════════════════════
   # EXTENSIONES CONOCIDAS DE RANSOMWARE
   # ═══════════════════════════════════

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

   # ═══════════════════════════════════
   # TIPOS DE DATOS
   # ═══════════════════════════════════

   @dataclass
   class FileEvent:
       """Evento de modificación de archivo."""
       path: str
       event_type: str  # "modified", "created", "renamed"
       timestamp: float
       size: int = 0
       entropy: float = 0.0

   @dataclass
   class RansomwareAlert:
       """Alerta de posible ransomware."""
       timestamp: str
       alert_type: str
       severity: str  # "warning", "critical"
       details: str
       affected_files: list[str] = field(default_factory=list)
       entropy_avg: float = 0.0
       files_per_second: float = 0.0

   @dataclass
   class AntiRansomwareConfig:
       """Configuración del detector."""
       # Umbral: archivos modificados en ventana de tiempo
       file_threshold: int = 10
       time_window_secs: float = 5.0
       # Umbral de entropía (archivos cifrados ~7.9+/8.0)
       entropy_threshold: float = 7.5
       # Directorios a monitorear
       watch_dirs: list[str] = field(default_factory=lambda: [
           "/home",
           "/var/lib/yeyo",
           "/etc/yeyo",
       ])
       # Directorios a ignorar
       ignore_dirs: list[str] = field(default_factory=lambda: [
           "/tmp", "/proc", "/sys", "/dev",
       ])

   # ═══════════════════════════════════
   # CALCULADOR DE ENTROPÍA
   # ═══════════════════════════════════

   def calculate_entropy(data: bytes) -> float:
       """
       Calcula la entropía de Shannon de datos binarios.
       Archivos normales: ~4-6 bits/byte
       Archivos cifrados: ~7.9-8.0 bits/byte
       Máximo teórico: 8.0 bits/byte
       """
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
       """Calcula entropía de un archivo (primeros N bytes)."""
       try:
           with open(filepath, "rb") as f:
               data = f.read(sample_size)
           return calculate_entropy(data)
       except (OSError, PermissionError):
           return 0.0

   # ═══════════════════════════════════
   # DETECTOR DE RANSOMWARE
   # ═══════════════════════════════════

   class RansomwareDetector:
       """Detecta comportamiento de ransomware en tiempo real."""

       def __init__(self, config: Optional[AntiRansomwareConfig] = None):
           self.config = config or AntiRansomwareConfig()
           self._events: list[FileEvent] = []
           self._alerts: list[RansomwareAlert] = []
           self._lock = Lock()
           self._paused = False

       def on_file_event(self, path: str, event_type: str) -> Optional[RansomwareAlert]:
           """
           Procesa un evento de archivo y verifica si es ransomware.
           Retorna alerta si se detecta comportamiento sospechoso.
           """
           if self._paused:
               return None

           # Ignorar directorios excluidos
           for ignore_dir in self.config.ignore_dirs:
               if path.startswith(ignore_dir):
                   return None

           now = time.time()
           entropy = calculate_file_entropy(path) if Path(path).exists() else 0.0

           event = FileEvent(
               path=path,
               event_type=event_type,
               timestamp=now,
               entropy=entropy,
           )

           with self._lock:
               self._events.append(event)
               # Limpiar eventos fuera de la ventana de tiempo
               cutoff = now - self.config.time_window_secs
               self._events = [e for e in self._events if e.timestamp > cutoff]

           # Verificar patrones de ransomware
           alert = self._check_patterns(event)
           if alert:
               self._alerts.append(alert)
               logger.critical(f"🚨 RANSOMWARE DETECTADO: {alert.details}")

           return alert

       def _check_patterns(self, latest_event: FileEvent) -> Optional[RansomwareAlert]:
           """Verifica todos los patrones de ransomware."""

           # 1. Extensión conocida de ransomware
           ext = Path(latest_event.path).suffix.lower()
           if ext in RANSOMWARE_EXTENSIONS:
               return RansomwareAlert(
                   timestamp=datetime.now(timezone.utc).isoformat(),
                   alert_type="known_extension",
                   severity="critical",
                   details=f"Extensión de ransomware detectada: {ext} en {latest_event.path}",
                   affected_files=[latest_event.path],
               )

           # 2. Cifrado masivo (>threshold archivos en <time_window)
           with self._lock:
               recent_events = [
                   e for e in self._events
                   if time.time() - e.timestamp < self.config.time_window_secs
               ]

           if len(recent_events) > self.config.file_threshold:
               # Verificar cambio de entropía
               high_entropy_count = sum(
                   1 for e in recent_events
                   if e.entropy > self.config.entropy_threshold
               )

               files_per_sec = len(recent_events) / self.config.time_window_secs
               avg_entropy = (
                   sum(e.entropy for e in recent_events) / len(recent_events)
                   if recent_events else 0.0
               )

               if high_entropy_count > self.config.file_threshold // 2:
                   return RansomwareAlert(
                       timestamp=datetime.now(timezone.utc).isoformat(),
                       alert_type="mass_encryption",
                       severity="critical",
                       details=(
                           f"Cifrado masivo detectado: {len(recent_events)} archivos "
                           f"en {self.config.time_window_secs}s con entropía alta "
                           f"(avg: {avg_entropy:.2f})"
                       ),
                       affected_files=[e.path for e in recent_events],
                       entropy_avg=avg_entropy,
                       files_per_second=files_per_sec,
                   )

               # Muchos archivos modificados sin entropía alta = posible backup/compilación
               if files_per_sec > self.config.file_threshold * 2:
                   return RansomwareAlert(
                       timestamp=datetime.now(timezone.utc).isoformat(),
                       alert_type="rapid_modification",
                       severity="warning",
                       details=(
                           f"Modificación rápida: {len(recent_events)} archivos "
                           f"en {self.config.time_window_secs}s ({files_per_sec:.1f}/s)"
                       ),
                       affected_files=[e.path for e in recent_events[-20:]],
                       files_per_second=files_per_sec,
                   )

           return None

       # ═══════════════════════════════════
       # CONSULTAS
       # ═══════════════════════════════════

       def get_alerts(self) -> list[RansomwareAlert]:
           """Retorna todas las alertas."""
           return self._alerts.copy()

       def get_recent_events(self) -> list[FileEvent]:
           """Retorna eventos recientes."""
           with self._lock:
               return self._events.copy()

       def get_event_rate(self) -> float:
           """Retorna la tasa de eventos por segundo."""
           with self._lock:
               if not self._events:
                   return 0.0
               now = time.time()
               recent = [e for e in self._events if now - e.timestamp < 60]
               return len(recent) / 60.0

       def pause(self) -> None:
           """Pausa la detección."""
           self._paused = True
           logger.info("[ANTI-RANSOMWARE] Detección pausada")

       def resume(self) -> None:
           """Reanuda la detección."""
           self._paused = False
           logger.info("[ANTI-RANSOMWARE] Detección reanudada")

       def is_paused(self) -> bool:
           """Retorna si la detección está pausada."""
           return self._paused

2. Crear archivo tests/unit/security/test_anti_ransomware.py:

   Ruta: ~/yeyo-os/tests/unit/security/test_anti_ransomware.py
   Contenido:

   """Tests para Anti-Ransomware — Micro-fase 6.6"""

   import pytest
   import tempfile
   import os
   from pathlib import Path
   from src.security.anti_ransomware import (
       RansomwareDetector,
       AntiRansomwareConfig,
       calculate_entropy,
       calculate_file_entropy,
       RANSOMWARE_EXTENSIONS,
   )


   @pytest.fixture
   def detector():
       config = AntiRansomwareConfig(
           file_threshold=5,
           time_window_secs=5.0,
           watch_dirs=["/tmp"],
           ignore_dirs=["/proc"],
       )
       return RansomwareDetector(config=config)


   class TestEntropy:
       def test_empty_data_zero_entropy(self):
           assert calculate_entropy(b"") == 0.0

       def test_uniform_data_low_entropy(self):
           data = b"\x00" * 1000
           assert calculate_entropy(data) == 0.0

       def test_random_data_high_entropy(self):
           data = bytes(range(256)) * 10
           entropy = calculate_entropy(data)
           assert entropy > 7.0

       def test_text_data_medium_entropy(self):
           data = b"Hello World! This is a normal text file with some content." * 20
           entropy = calculate_entropy(data)
           assert 3.0 < entropy < 6.0

       def test_file_entropy(self, tmp_path):
           f = tmp_path / "test.txt"
           f.write_text("Hello World " * 100)
           entropy = calculate_file_entropy(str(f))
           assert 0.0 < entropy < 5.0


   class TestRansomwareDetection:
       def test_known_extension_detected(self, detector, tmp_path):
           f = tmp_path / "document.encrypted"
           f.write_text("fake encrypted content")
           alert = detector.on_file_event(str(f), "created")
           assert alert is not None
           assert alert.alert_type == "known_extension"
           assert alert.severity == "critical"

       def test_normal_extension_not_flagged(self, detector, tmp_path):
           f = tmp_path / "document.txt"
           f.write_text("normal text content")
           alert = detector.on_file_event(str(f), "modified")
           assert alert is None

       def test_mass_modification_detected(self, detector, tmp_path):
           alert = None
           for i in range(20):
               f = tmp_path / f"file_{i}.dat"
               # Escribir datos de alta entropía (simula cifrado)
               f.write_bytes(bytes(range(256)) * 16)
               result = detector.on_file_event(str(f), "modified")
               if result is not None:
                   alert = result

           # Debería haber detectado algo
           assert alert is not None

       def test_normal_file_ops_not_flagged(self, detector, tmp_path):
           # Pocas modificaciones de archivos normales
           for i in range(3):
               f = tmp_path / f"normal_{i}.txt"
               f.write_text(f"Normal content {i}")
               alert = detector.on_file_event(str(f), "modified")
               assert alert is None

       def test_ignored_directory(self, detector):
           alert = detector.on_file_event("/proc/something", "modified")
           assert alert is None

       def test_paused_detection(self, detector, tmp_path):
           detector.pause()
           f = tmp_path / "file.encrypted"
           f.write_text("should not be detected")
           alert = detector.on_file_event(str(f), "created")
           assert alert is None
           assert detector.is_paused()

       def test_resume_detection(self, detector, tmp_path):
           detector.pause()
           detector.resume()
           assert not detector.is_paused()
           f = tmp_path / "file.locked"
           f.write_text("should be detected")
           alert = detector.on_file_event(str(f), "created")
           assert alert is not None


   class TestEntropyAnalysis:
       def test_encrypted_file_high_entropy(self, tmp_path):
           f = tmp_path / "encrypted.bin"
           f.write_bytes(os.urandom(4096))
           entropy = calculate_file_entropy(str(f))
           assert entropy > 7.5

       def test_text_file_low_entropy(self, tmp_path):
           f = tmp_path / "readme.txt"
           f.write_text("The quick brown fox jumps over the lazy dog. " * 100)
           entropy = calculate_file_entropy(str(f))
           assert entropy < 5.0

3. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/security/test_anti_ransomware.py -v

VERIFICAR:
- [ ] Archivo src/security/anti_ransomware.py existe con RansomwareDetector
- [ ] Extensiones de ransomware detectadas → alerta CRITICAL
- [ ] Cifrado masivo (>threshold archivos con entropía alta) → alerta CRITICAL
- [ ] Operaciones normales de archivos NO se flagean
- [ ] Cálculo de entropía correcto (texto ~4-6, cifrado ~7.9)
- [ ] Pause/resume funciona
- [ ] Directorios ignorados no generan alertas
- [ ] TODOS los tests pasan

SI FALLA:
- Entropía inesperada: verificar sample_size en calculate_file_entropy
- Timing issues: ajustar time_window_secs en test config
- Import error: verificar __init__.py

NO HACER:
- No borrar archivos sospechosos automáticamente (solo pausar y alertar)
- No desactivar la detección permanentemente
- No ignorar alertas CRITICAL
- No monitorear /proc, /sys, /dev

GATE: RansomwareDetector detecta extensiones conocidas, cifrado masivo por entropía, no genera falsos positivos en operaciones normales, pause/resume funciona, todos los tests pasan.
```
