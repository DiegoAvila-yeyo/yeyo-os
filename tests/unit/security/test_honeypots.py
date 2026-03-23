"""Tests para Honeypots — Micro-fase 6.7"""

import pytest
from pathlib import Path
from src.security.honeypots import (
    HoneypotManager,
    HoneypotConfig,
    HoneypotFile,
    HONEYPOT_FILES,
)


@pytest.fixture
def tmp_config(tmp_path):
    return HoneypotConfig(alert_log_file=str(tmp_path / "alerts.json"), ssh_honeypot_port=2222)


@pytest.fixture
def tmp_honeypots(tmp_path):
    return [
        HoneypotFile(path=str(tmp_path / ".ssh" / "id_rsa.fake"), description="Clave SSH falsa", fake_content="FAKE KEY CONTENT"),
        HoneypotFile(path=str(tmp_path / "shadow.fake"), description="Shadow falso", fake_content="FAKE SHADOW"),
    ]


@pytest.fixture
def manager(tmp_config, tmp_honeypots):
    return HoneypotManager(config=tmp_config, honeypot_files=tmp_honeypots)


class TestHoneypotDeployment:
    def test_deploy_creates_files(self, manager, tmp_honeypots):
        deployed = manager.deploy_file_honeypots()
        assert len(deployed) == 2
        for hp in tmp_honeypots:
            assert Path(hp.path).exists()

    def test_deploy_marks_created(self, manager, tmp_honeypots):
        manager.deploy_file_honeypots()
        for hp in tmp_honeypots:
            assert hp.created is True

    def test_remove_deletes_files(self, manager, tmp_honeypots):
        manager.deploy_file_honeypots()
        manager.remove_file_honeypots()
        for hp in tmp_honeypots:
            assert not Path(hp.path).exists()

    def test_fake_content_not_real(self, tmp_honeypots):
        for hp in tmp_honeypots:
            assert "FAKE" in hp.fake_content or "HONEYPOT" in hp.fake_content


class TestHoneypotAlerts:
    @pytest.mark.asyncio
    async def test_file_access_triggers_alert(self, manager, tmp_honeypots):
        manager.deploy_file_honeypots()
        alert = await manager.on_file_accessed(tmp_honeypots[0].path, source_info="pid:1234")
        assert alert is not None
        assert alert.honeypot_type == "file"
        assert alert.severity == "critical"

    @pytest.mark.asyncio
    async def test_non_honeypot_no_alert(self, manager):
        alert = await manager.on_file_accessed("/etc/passwd", "pid:1234")
        assert alert is None

    @pytest.mark.asyncio
    async def test_ssh_connection_triggers_alert(self, manager):
        alert = await manager.on_ssh_connection(source_ip="192.168.1.100", source_port=54321, username="root", password="admin123")
        assert alert is not None
        assert alert.honeypot_type == "service"
        assert "192.168.1.100" in alert.source_info
        assert "root" in alert.details

    @pytest.mark.asyncio
    async def test_alert_includes_full_details(self, manager, tmp_honeypots):
        manager.deploy_file_honeypots()
        alert = await manager.on_file_accessed(tmp_honeypots[0].path, source_info="user:attacker pid:9999 cmd:cat")
        assert "attacker" in alert.source_info or "attacker" in alert.details

    @pytest.mark.asyncio
    async def test_alert_logged_to_file(self, manager, tmp_config, tmp_honeypots):
        manager.deploy_file_honeypots()
        await manager.on_file_accessed(tmp_honeypots[0].path, "test")
        log_path = Path(tmp_config.alert_log_file)
        assert log_path.exists()

    @pytest.mark.asyncio
    async def test_callback_called(self, tmp_config, tmp_honeypots):
        callback_called = []
        async def on_alert(alert):
            callback_called.append(alert)
        mgr = HoneypotManager(config=tmp_config, honeypot_files=tmp_honeypots, on_alert=on_alert)
        mgr.deploy_file_honeypots()
        await mgr.on_file_accessed(tmp_honeypots[0].path, "test")
        assert len(callback_called) == 1


class TestHoneypotStatus:
    def test_status_shows_deployed(self, manager):
        manager.deploy_file_honeypots()
        status = manager.get_status()
        assert status["files_deployed"] == 2
        assert status["enabled"] is True

    def test_no_real_data_exposed(self):
        for hp in HONEYPOT_FILES:
            content = hp.fake_content.upper()
            assert "HONEYPOT" in content or "FAKE" in content or "NOT REAL" in content.replace("-", " ")
