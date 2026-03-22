"""Tests para Config Node — Micro-fase 5.14"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.nodes.config.service import ConfigNode, CONFIG_SECTIONS


class TestConfigSections:

    def test_all_sections_defined(self):
        expected = {"models", "gpu", "memory", "security", "backups", "about"}
        assert set(CONFIG_SECTIONS) == expected

    @pytest.mark.asyncio
    async def test_render_ui_has_sections(self):
        node = ConfigNode()
        ui = await node.render_ui()
        assert "sections" in ui["props"]
        assert len(ui["props"]["sections"]) == 6


class TestConfigSettings:

    def test_update_setting(self):
        node = ConfigNode()
        result = node._update_setting("theme", "dark")
        assert result["updated"] is True
        assert node._settings["theme"] == "dark"

    def test_update_multiple_settings(self):
        node = ConfigNode()
        node._update_setting("theme", "dark")
        node._update_setting("language", "es")
        assert len(node._settings) == 2

    def test_update_empty_key_rejected(self):
        node = ConfigNode()
        result = node._update_setting("", "value")
        assert "error" in result

    def test_update_whitespace_key_rejected(self):
        node = ConfigNode()
        result = node._update_setting("   ", "value")
        assert "error" in result


class TestConfigAbout:

    def test_about_info(self):
        node = ConfigNode()
        about = node._get_about()
        assert about["name"] == "YeyoOS"
        assert "GTX 1060" in about["hardware"]
        assert about["author"] == "Yeyo"


class TestConfigModels:

    @pytest.mark.asyncio
    async def test_get_models_calls_ollama(self):
        node = ConfigNode()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "models": [{"name": "qwen2.5:3b", "size": 2000000000, "modified_at": ""}]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_instance

            result = await node._get_models()
            assert "models" in result

    @pytest.mark.asyncio
    async def test_pull_empty_name_rejected(self):
        node = ConfigNode()
        result = await node._pull_model("")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_empty_name_rejected(self):
        node = ConfigNode()
        result = await node._delete_model("")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_process_unknown_action(self):
        node = ConfigNode()
        result = await node.process({"action": "unknown"})
        assert "error" in result


class TestConfigFormatSize:

    def test_format_bytes(self):
        assert ConfigNode._format_size(500) == "500.0 B"

    def test_format_kb(self):
        result = ConfigNode._format_size(1024 * 5)
        assert "KB" in result

    def test_format_mb(self):
        result = ConfigNode._format_size(1024 * 1024 * 500)
        assert "MB" in result

    def test_format_gb(self):
        result = ConfigNode._format_size(1024 * 1024 * 1024 * 2)
        assert "GB" in result
