"""
YeyoOS — Integration Test Capa 6: Sistema Inmune
Micro-fase 6.11

Verifies all security components work together.
"""

import pytest
import json
import os
import shutil
import subprocess
from pathlib import Path

from src.security.backup import BackupManager, BackupConfig, BackupPriority, BackupDestination
from src.security.anti_ransomware import RansomwareDetector, AntiRansomwareConfig, calculate_entropy
from src.security.honeypots import HoneypotManager, HoneypotConfig, HoneypotFile
from src.security.firewall import FirewallManager, FirewallAction
from src.security.audit import AuditTrail, AuditConfig


class TestGuardianCompiles:
    def test_cargo_check(self):
        if not shutil.which("cargo"):
            pytest.skip("cargo no está instalado en este entorno")
        guardian_dir = Path(__file__).resolve().parents[2] / "rust" / "guardian"
        if not guardian_dir.exists():
            pytest.skip("Guardian directory not found")
        result = subprocess.run(
            ["cargo", "check"],
            cwd=str(guardian_dir),
            capture_output=True, text=True, timeout=120,
        )
        assert result.returncode == 0, f"cargo check failed: {result.stderr}"

    def test_cargo_test(self):
        if not shutil.which("cargo"):
            pytest.skip("cargo no está instalado en este entorno")
        guardian_dir = Path(__file__).resolve().parents[2] / "rust" / "guardian"
        if not guardian_dir.exists():
            pytest.skip("Guardian directory not found")
        result = subprocess.run(
            ["cargo", "test"],
            cwd=str(guardian_dir),
            capture_output=True, text=True, timeout=120,
        )
        assert result.returncode == 0, f"cargo test failed: {result.stderr}"


class TestAnomalyResponsePipeline:
    def test_anomaly_to_audit_trail(self, tmp_path):
        audit = AuditTrail(config=AuditConfig(log_file=str(tmp_path / "audit.jsonl")))
        audit.append(
            actor="guardian", actor_type="service",
            action="anomaly_detected",
            description="CPU anomaly score 0.95",
            resource="cpu_monitor", result="alert_triggered",
            metadata={"score": 0.95, "level": "critical"},
        )
        entries = audit.search(action="anomaly_detected")
        assert len(entries) == 1
        assert entries[0].metadata["score"] == 0.95


class TestKillSwitchAudit:
    def test_kill_switch_logged(self, tmp_path):
        audit = AuditTrail(config=AuditConfig(log_file=str(tmp_path / "audit.jsonl")))
        audit.append("user", "user", "kill_switch", "Kill Switch activado", "all_ai_processes", "paused")
        audit.append("user", "user", "kill_switch", "Kill Switch desactivado", "all_ai_processes", "resumed")
        entries = audit.search(action="kill_switch")
        assert len(entries) == 2
        valid, broken = audit.verify_chain()
        assert valid is True


class TestBackupPriority:
    def test_flash_memory_highest_priority(self):
        assert BackupPriority.FLASH_MEMORY.value == 1
        assert BackupPriority.FLASH_MEMORY < BackupPriority.CONFIG
        assert BackupPriority.FLASH_MEMORY < BackupPriority.FULL_SYSTEM


class TestSecurityDetection:
    def test_ransomware_extension_detected(self, tmp_path):
        detector = RansomwareDetector(config=AntiRansomwareConfig(
            file_threshold=3, time_window_secs=10.0,
            watch_dirs=[str(tmp_path)], ignore_dirs=[],
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
            config=HoneypotConfig(alert_log_file=str(tmp_path / "hp-alerts.json")),
            honeypot_files=[hp_file],
        )
        mgr.deploy_file_honeypots()
        alert = await mgr.on_file_accessed(str(tmp_path / "fake_key"), "test")
        assert alert is not None
        assert alert.severity == "critical"

    def test_entropy_distinguishes_encrypted(self, tmp_path):
        normal = tmp_path / "normal.txt"
        normal.write_text("Hello World! Normal text content here. " * 100)
        encrypted = tmp_path / "encrypted.bin"
        encrypted.write_bytes(os.urandom(4096))
        normal_entropy = calculate_entropy(normal.read_bytes())
        encrypted_entropy = calculate_entropy(encrypted.read_bytes())
        assert normal_entropy < 5.0
        assert encrypted_entropy > 7.0


class TestFirewallAudit:
    def test_ip_block_audited(self, tmp_path):
        fw = FirewallManager()
        audit = AuditTrail(config=AuditConfig(log_file=str(tmp_path / "audit.jsonl")))
        fw.block_ip("10.0.0.1", "anomaly detected")
        audit.append("guardian", "service", "ip_blocked", "IP 10.0.0.1 bloqueada", "firewall", "success", metadata={"ip": "10.0.0.1"})
        entries = audit.search(action="ip_blocked")
        assert len(entries) == 1

    def test_container_isolation(self):
        fw = FirewallManager()
        fw.isolate_container("suspicious-container", "critical anomaly")
        rules = fw.get_rules()
        isolate_rules = [r for r in rules if "isolate" in r.id]
        assert len(isolate_rules) == 1


class TestFullAuditIntegrity:
    def test_full_security_audit_chain(self, tmp_path):
        audit = AuditTrail(config=AuditConfig(log_file=str(tmp_path / "audit.jsonl")))
        events = [
            ("guardian", "service", "daemon_start", "Guardian iniciado", "system", "success"),
            ("guardian", "service", "baseline_learning", "Aprendiendo baseline", "anomaly", "success"),
            ("guardian", "service", "anomaly_detected", "CPU anomaly 0.85", "cpu", "alert"),
            ("guardian", "service", "auto_response", "Increased monitoring", "monitor", "success"),
            ("user", "user", "kill_switch", "Kill Switch activado", "ai_processes", "paused"),
            ("user", "user", "kill_switch", "Kill Switch desactivado", "ai_processes", "resumed"),
            ("guardian", "service", "backup_completed", "Flash Memory backup", "restic", "success"),
            ("guardian", "service", "honeypot_alert", "SSH honeypot accessed", "honeypot", "alert"),
            ("guardian", "service", "ip_blocked", "Blocked 10.0.0.1", "firewall", "success"),
            ("guardian", "service", "ransomware_detected", "Extension .encrypted found", "anti_ransomware", "alert"),
        ]
        for actor, atype, action, desc, resource, result in events:
            audit.append(actor, atype, action, desc, resource, result)
        assert audit.get_count() == 10
        valid, broken = audit.verify_chain()
        assert valid is True
        assert broken is None
        json_export = audit.export_json()
        data = json.loads(json_export)
        assert len(data) == 10
        csv_export = audit.export_csv()
        assert "guardian" in csv_export
        assert "kill_switch" in csv_export


class TestFlashMemoryProtection:
    def test_flash_memory_backup_priority(self):
        assert BackupPriority.FLASH_MEMORY.value == 1

    def test_firewall_no_delete_action(self):
        actions = [a.value for a in FirewallAction]
        assert "delete" not in actions
        assert "remove" not in actions

    def test_audit_no_delete(self):
        trail = AuditTrail.__dict__
        assert "delete" not in trail
        assert "remove" not in trail
        assert "update" not in trail
