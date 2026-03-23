"""Tests para Backup System 3-2-1 — Micro-fase 6.5"""

import pytest
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
        BackupDestination(name="local", repo_path=str(tmp_path / "repo-local"), medium_type="local", initialized=True),
        BackupDestination(name="usb", repo_path=str(tmp_path / "repo-usb"), medium_type="usb", initialized=True),
        BackupDestination(name="cloud", repo_path=str(tmp_path / "repo-cloud"), medium_type="cloud", is_offsite=True, initialized=True),
    ]


@pytest.fixture
def manager(tmp_config, tmp_destinations):
    return BackupManager(config=tmp_config, destinations=tmp_destinations)


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
            BackupDestination(name="local1", repo_path="/tmp/r1", medium_type="local", initialized=True),
            BackupDestination(name="local2", repo_path="/tmp/r2", medium_type="local", initialized=True),
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
