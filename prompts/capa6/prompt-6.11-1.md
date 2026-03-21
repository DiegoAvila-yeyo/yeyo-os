## ═══════════════════════════════════════
## MICRO-FASE 6.11 — Integration Test Capa 6
## Tipo: MIXTA | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 6.11-1 [MIXTA] — Test de integración completo de Capa 6

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 6.11 de Capa 6 (Sistema Inmune): test de integración completo que verifica que TODOS los componentes de seguridad funcionan juntos.

CONTEXTO:
- Micro-fases 6.0-6.10 completadas: Guardian Daemon, Anomaly Detection, Auto-Response, Kill Switch, Smart Snapshots, Backup 3-2-1, Anti-Ransomware, Honeypots, Network Firewall, Security Dashboard, Audit System
- Este test verifica la integración entre TODOS los componentes
- También verifica regresión con Capas 0-5
- Guardian debe estar compilado y funcional
- Python tests cubren los módulos de seguridad
- Frontend se verifica que compila

Abre el directorio ~/yeyo-os en VS Code y también una terminal.

CREAR:

1. Crear archivo tests/integration/test_capa6_integration.py:

   Ruta: ~/yeyo-os/tests/integration/test_capa6_integration.py
   Contenido:

   """
   YeyoOS — Integration Test Capa 6: Sistema Inmune
   Micro-fase 6.11

   Verifica que TODOS los componentes de seguridad funcionan juntos:
   - Guardian Daemon (Rust) compilable
   - Anomaly Detection → Auto-Response pipeline
   - Kill Switch state management
   - Snapshots + Backup integration
   - Anti-Ransomware detection
   - Honeypot alerting
   - Firewall rules management
   - Audit trail integrity
   """

   import pytest
   import json
   import subprocess
   import tempfile
   import time
   from pathlib import Path

   # ═══════════════════════════════════
   # IMPORTS DE MÓDULOS DE SEGURIDAD
   # ═══════════════════════════════════

   from src.security.snapshots import SmartSnapshotManager, SnapshotConfig
   from src.security.backup import BackupManager, BackupConfig, BackupPriority, BackupDestination
   from src.security.anti_ransomware import RansomwareDetector, AntiRansomwareConfig, calculate_entropy
   from src.security.honeypots import HoneypotManager, HoneypotConfig, HoneypotFile
   from src.security.firewall import FirewallManager, FirewallAction
   from src.security.audit import AuditTrail, AuditConfig


   # ═══════════════════════════════════
   # TEST: GUARDIAN COMPILA
   # ═══════════════════════════════════

   class TestGuardianCompiles:
       """Verifica que el Guardian Daemon en Rust compila."""

       def test_cargo_check(self):
           """Guardian debe compilar sin errores."""
           guardian_dir = Path.home() / "yeyo-os" / "rust" / "guardian"
           if not guardian_dir.exists():
               pytest.skip("Guardian directory not found")

           result = subprocess.run(
               ["cargo", "check"],
               cwd=str(guardian_dir),
               capture_output=True, text=True, timeout=120,
           )
           assert result.returncode == 0, f"cargo check falló: {result.stderr}"

       def test_cargo_test(self):
           """Tests de Guardian deben pasar."""
           guardian_dir = Path.home() / "yeyo-os" / "rust" / "guardian"
           if not guardian_dir.exists():
               pytest.skip("Guardian directory not found")

           result = subprocess.run(
               ["cargo", "test"],
               cwd=str(guardian_dir),
               capture_output=True, text=True, timeout=120,
           )
           assert result.returncode == 0, f"cargo test falló: {result.stderr}"


   # ═══════════════════════════════════
   # TEST: PIPELINE ANOMALY → RESPONSE
   # ═══════════════════════════════════

   class TestAnomalyResponsePipeline:
       """Verifica que anomalía detectada → auto-response funciona."""

       def test_anomaly_to_audit_trail(self, tmp_path):
           """Una anomalía debe generar entrada en audit trail."""
           audit = AuditTrail(config=AuditConfig(
               log_file=str(tmp_path / "audit.jsonl"),
           ))

           # Simular detección de anomalía
           audit.append(
               actor="guardian",
               actor_type="service",
               action="anomaly_detected",
               description="CPU anomaly score 0.95",
               resource="cpu_monitor",
               result="alert_triggered",
               metadata={"score": 0.95, "level": "critical"},
           )

           entries = audit.search(action="anomaly_detected")
           assert len(entries) == 1
           assert entries[0].metadata["score"] == 0.95


   # ═══════════════════════════════════
   # TEST: KILL SWITCH + AUDIT
   # ═══════════════════════════════════

   class TestKillSwitchAudit:
       """Kill Switch debe registrarse en audit trail."""

       def test_kill_switch_logged(self, tmp_path):
           audit = AuditTrail(config=AuditConfig(
               log_file=str(tmp_path / "audit.jsonl"),
           ))

           # Simular Kill Switch activation
           audit.append(
               actor="user",
               actor_type="user",
               action="kill_switch",
               description="Kill Switch activado via Ctrl+Alt+K",
               resource="all_ai_processes",
               result="paused",
           )

           audit.append(
               actor="user",
               actor_type="user",
               action="kill_switch",
               description="Kill Switch desactivado",
               resource="all_ai_processes",
               result="resumed",
           )

           entries = audit.search(action="kill_switch")
           assert len(entries) == 2

           # Cadena íntegra
           valid, broken = audit.verify_chain()
           assert valid is True


   # ═══════════════════════════════════
   # TEST: SNAPSHOT + BACKUP
   # ═══════════════════════════════════

   class TestSnapshotBackupIntegration:
       """Snapshots y backups trabajan juntos."""

       def test_snapshot_before_backup(self, tmp_path):
           """Snapshot se crea antes de backup."""
           snap_mgr = SmartSnapshotManager(config=SnapshotConfig(
               snapshot_dir=str(tmp_path / "snaps"),
               max_snapshots=10,
               subvolume=str(tmp_path / "vol"),
               metadata_file=str(tmp_path / "snap-meta.json"),
           ))

           # Crear snapshot pre-backup
           snap = snap_mgr.create(
               trigger_event="pre_system_update",
               label="Before backup",
           )
           assert snap.trigger_event == "pre_system_update"

       def test_flash_memory_highest_priority(self):
           """Flash Memory debe ser la prioridad más alta."""
           assert BackupPriority.FLASH_MEMORY.value == 1
           assert BackupPriority.FLASH_MEMORY < BackupPriority.CONFIG
           assert BackupPriority.FLASH_MEMORY < BackupPriority.FULL_SYSTEM


   # ═══════════════════════════════════
   # TEST: ANTI-RANSOMWARE + HONEYPOT
   # ═══════════════════════════════════

   class TestSecurityDetection:
       """Anti-ransomware y honeypots detectan amenazas."""

       def test_ransomware_extension_detected(self, tmp_path):
           detector = RansomwareDetector(config=AntiRansomwareConfig(
               file_threshold=3,
               time_window_secs=10.0,
               watch_dirs=[str(tmp_path)],
               ignore_dirs=[],
           ))

           f = tmp_path / "important.encrypted"
           f.write_text("ransomware payload")

           alert = detector.on_file_event(str(f), "created")
           assert alert is not None
           assert alert.severity == "critical"

       @pytest.mark.asyncio
       async def test_honeypot_triggers_alert(self, tmp_path):
           hp_file = HoneypotFile(
               path=str(tmp_path / "fake_key"),
               description="Test honeypot",
               fake_content="FAKE HONEYPOT DATA",
           )

           mgr = HoneypotManager(
               config=HoneypotConfig(
                   alert_log_file=str(tmp_path / "hp-alerts.json"),
               ),
               honeypot_files=[hp_file],
           )
           mgr.deploy_file_honeypots()

           alert = await mgr.on_file_accessed(str(tmp_path / "fake_key"), "test")
           assert alert is not None
           assert alert.severity == "critical"

       def test_entropy_distinguishes_encrypted(self, tmp_path):
           """La entropía distingue archivos normales de cifrados."""
           normal = tmp_path / "normal.txt"
           normal.write_text("Hello World! Normal text content here. " * 100)

           encrypted = tmp_path / "encrypted.bin"
           import os
           encrypted.write_bytes(os.urandom(4096))

           normal_entropy = calculate_entropy(normal.read_bytes())
           encrypted_entropy = calculate_entropy(encrypted.read_bytes())

           assert normal_entropy < 5.0
           assert encrypted_entropy > 7.0


   # ═══════════════════════════════════
   # TEST: FIREWALL + AUDIT
   # ═══════════════════════════════════

   class TestFirewallAudit:
       """Firewall se integra con audit trail."""

       def test_ip_block_audited(self, tmp_path):
           fw = FirewallManager()
           audit = AuditTrail(config=AuditConfig(
               log_file=str(tmp_path / "audit.jsonl"),
           ))

           # Bloquear IP
           fw.block_ip("10.0.0.1", "anomaly detected")

           # Registrar en audit
           audit.append(
               actor="guardian",
               actor_type="service",
               action="ip_blocked",
               description="IP 10.0.0.1 bloqueada por anomalía",
               resource="firewall",
               result="success",
               metadata={"ip": "10.0.0.1"},
           )

           entries = audit.search(action="ip_blocked")
           assert len(entries) == 1

       def test_container_isolation(self):
           fw = FirewallManager()
           fw.isolate_container("suspicious-container", "critical anomaly")

           rules = fw.get_rules()
           isolate_rules = [r for r in rules if "isolate" in r.id]
           assert len(isolate_rules) == 1


   # ═══════════════════════════════════
   # TEST: AUDIT TRAIL INTEGRITY
   # ═══════════════════════════════════

   class TestFullAuditIntegrity:
       """Cadena completa de audit trail es íntegra."""

       def test_full_security_audit_chain(self, tmp_path):
           """Simula una sesión completa de seguridad y verifica cadena."""
           audit = AuditTrail(config=AuditConfig(
               log_file=str(tmp_path / "audit.jsonl"),
           ))

           # Secuencia de eventos de seguridad
           events = [
               ("guardian", "service", "daemon_start", "Guardian iniciado", "system", "success"),
               ("guardian", "service", "baseline_learning", "Aprendiendo baseline", "anomaly", "success"),
               ("guardian", "service", "anomaly_detected", "CPU anomaly 0.85", "cpu", "alert"),
               ("guardian", "service", "auto_response", "Increased monitoring", "monitor", "success"),
               ("user", "user", "kill_switch", "Kill Switch activado", "ai_processes", "paused"),
               ("user", "user", "kill_switch", "Kill Switch desactivado", "ai_processes", "resumed"),
               ("guardian", "service", "snapshot_created", "Pre-update snapshot", "btrfs", "success"),
               ("guardian", "service", "backup_completed", "Flash Memory backup", "restic", "success"),
               ("guardian", "service", "honeypot_alert", "SSH honeypot accessed", "honeypot", "alert"),
               ("guardian", "service", "ip_blocked", "Blocked 10.0.0.1", "firewall", "success"),
           ]

           for actor, atype, action, desc, resource, result in events:
               audit.append(actor, atype, action, desc, resource, result)

           # Verificar que todos se registraron
           assert audit.get_count() == 10

           # Verificar cadena íntegra
           valid, broken = audit.verify_chain()
           assert valid is True
           assert broken is None

           # Verificar exportación
           json_export = audit.export_json()
           data = json.loads(json_export)
           assert len(data) == 10

           csv_export = audit.export_csv()
           assert "guardian" in csv_export
           assert "kill_switch" in csv_export


   # ═══════════════════════════════════
   # TEST: FLASH MEMORY PROTECTION
   # ═══════════════════════════════════

   class TestFlashMemoryProtection:
       """Flash Memory es lo más valioso — NUNCA se borra."""

       def test_flash_memory_backup_priority(self):
           """Flash Memory tiene la prioridad más alta de backup."""
           assert BackupPriority.FLASH_MEMORY.value == 1

       def test_firewall_no_delete_action(self):
           """Firewall no tiene acción de borrado."""
           actions = [a.value for a in FirewallAction]
           assert "delete" not in actions
           assert "remove" not in actions

       def test_audit_no_delete(self):
           """AuditTrail no tiene métodos de borrado."""
           trail = AuditTrail.__dict__
           assert "delete" not in trail
           assert "remove" not in trail
           assert "update" not in trail

2. Crear directorio si no existe:
   mkdir -p tests/integration

3. Crear archivo tests/integration/__init__.py (vacío):

   Ruta: ~/yeyo-os/tests/integration/__init__.py
   Contenido: (archivo vacío)

4. Ejecutar todos los tests de Capa 6:

   # Tests Python
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/security/ tests/integration/test_capa6_integration.py -v 2>&1

   # Tests Rust (Guardian)
   cd ~/yeyo-os/rust/guardian
   cargo test 2>&1

5. Verificar que Guardian compila en release:
   cd ~/yeyo-os/rust/guardian
   cargo build --release 2>&1

VERIFICAR:
- [ ] TODOS los tests unitarios de src/security/ pasan
- [ ] Test de integración pasa
- [ ] Guardian compila con cargo check
- [ ] Guardian tests pasan con cargo test
- [ ] Guardian compila en release con cargo build --release
- [ ] Pipeline anomaly → auto-response → audit funciona
- [ ] Kill Switch se registra en audit trail
- [ ] Snapshot se crea antes de backup
- [ ] Flash Memory es prioridad 1 (más alta)
- [ ] Anti-ransomware detecta extensiones + cifrado masivo
- [ ] Honeypots generan alertas CRITICAL
- [ ] Firewall aísla containers y bloquea IPs
- [ ] Cadena SHA-256 del audit trail es íntegra (10+ entradas)
- [ ] Export JSON y CSV funcionan
- [ ] No existen métodos delete/update en AuditTrail
- [ ] Flash Memory NUNCA se borra

SI FALLA:
- Import errors: verificar todos los __init__.py
- Guardian no compila: verificar Cargo.toml dependencias
- pytest-asyncio: pip install pytest-asyncio
- Timeout en cargo build: es normal para la primera compilación
- No Btrfs: los tests usan fallback con directorios

NO HACER:
- No saltarse tests que fallan — TODOS deben pasar
- No modificar Capas anteriores (0-5) para que pasen los tests
- No borrar Flash Memory en ningún test
- No desactivar la verificación de cadena SHA-256

GATE FINAL CAPA 6:
✅ Guardian Daemon compilado en Rust con heartbeat, monitoreo, API HTTP
✅ Anomaly Detection estadístico con z-score, baseline learning
✅ Auto-Response: CRITICAL → snapshot + aislar + pausar + alertar
✅ Kill Switch: Ctrl+Alt+K pausa toda IA (SIGSTOP, no SIGKILL)
✅ Smart Snapshots: Btrfs, por eventos, max 50, integridad SHA-256
✅ Backup 3-2-1: restic cifrado AES-256, Flash Memory cada 1h
✅ Anti-Ransomware: entropía + extensiones + cifrado masivo
✅ Honeypots: archivos falsos + SSH fake, alerta inmediata
✅ Firewall: nftables, per-container, rate limiting, DDoS básico
✅ Security Dashboard: React, real-time, Kill Switch button
✅ Audit System: append-only, cadena SHA-256, NO UPDATE/DELETE
✅ Flash Memory = lo más valioso, NUNCA se borra
✅ Todos los tests pasan (Rust + Python + integración)
```
