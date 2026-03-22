"""Tests para Mining Node — Micro-fase 5.15"""

import pytest
from src.nodes.mining.service import MiningNode


class TestGPUMiningBlocked:
    """Tests CRÍTICOS: GPU NUNCA para minería."""

    def test_gpu_mining_blocked_flag(self):
        """GPU mining debe estar bloqueado SIEMPRE."""
        assert MiningNode.GPU_MINING_BLOCKED is True

    @pytest.mark.asyncio
    async def test_gpu_request_always_denied(self):
        """Mining Node NUNCA puede solicitar GPU."""
        node = MiningNode()
        result = await node.request_gpu(vram_mb=1024, priority=1)
        assert result is False

    @pytest.mark.asyncio
    async def test_gpu_request_denied_any_amount(self):
        """Incluso 1MB de VRAM es denegado."""
        node = MiningNode()
        assert await node.request_gpu(vram_mb=1) is False

    @pytest.mark.asyncio
    async def test_gpu_mine_action_blocked(self):
        """Intentar minar con GPU retorna error."""
        node = MiningNode()
        result = await node.process({"action": "gpu_mine"})
        assert "error" in result
        assert result["gpu_mining_blocked"] is True

    def test_container_config_no_gpu(self):
        """Container config debe tener gpu_required=False."""
        node = MiningNode()
        assert node.container_config.get("gpu_required") is False

    @pytest.mark.asyncio
    async def test_render_ui_shows_gpu_blocked(self):
        node = MiningNode()
        ui = await node.render_ui()
        assert ui["props"]["gpu_mining_blocked"] is True


class TestASICMonitoring:

    def test_add_device(self):
        node = MiningNode()
        result = node._add_device({"name": "Antminer S19", "model": "S19 Pro"})
        assert "device_id" in result
        assert len(node._devices) == 1

    def test_add_multiple_devices(self):
        node = MiningNode()
        node._add_device({"name": "ASIC 1"})
        node._add_device({"name": "ASIC 2"})
        assert len(node._devices) == 2

    def test_remove_device(self):
        node = MiningNode()
        result = node._add_device({"name": "ASIC 1"})
        remove_result = node._remove_device(result["device_id"])
        assert "removed" in remove_result
        assert len(node._devices) == 0

    def test_remove_nonexistent_device(self):
        node = MiningNode()
        result = node._remove_device("nonexistent")
        assert "error" in result

    def test_calculate_stats_empty(self):
        node = MiningNode()
        stats = node._calculate_stats()
        assert stats.devices_total == 0
        assert stats.total_hashrate == 0.0

    def test_calculate_stats_with_devices(self):
        node = MiningNode()
        node._add_device({"name": "ASIC 1"})
        stats = node._calculate_stats()
        assert stats.devices_total == 1
        assert stats.devices_online == 0  # Default is offline

    @pytest.mark.asyncio
    async def test_refresh_devices(self):
        node = MiningNode()
        node._add_device({"name": "ASIC 1"})
        result = await node._refresh_devices()
        assert result["refreshed"] is True
        assert result["devices"] == 1

    @pytest.mark.asyncio
    async def test_cleanup_clears_devices(self):
        node = MiningNode()
        node._add_device({"name": "ASIC 1"})
        await node.cleanup()
        assert len(node._devices) == 0
