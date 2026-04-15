"""Tests para YeyoNet resource_monitor."""
import sys

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.yeyonet.resource_monitor import ResourceMonitor, _detect_gpu, _detect_ollama_models
from src.yeyonet.models import NodeResources


class TestResourceMonitor:
    """Tests for ResourceMonitor."""

    def test_initial_state(self):
        mon = ResourceMonitor()
        assert isinstance(mon.last_resources, NodeResources)
        assert mon.last_resources.cpu_percent == 0.0

    @pytest.mark.asyncio
    async def test_snapshot_returns_node_resources(self):
        mon = ResourceMonitor()

        mock_psutil = MagicMock()
        mock_psutil.cpu_percent.return_value = 25.0
        mock_mem = MagicMock()
        mock_mem.available = 8 * (1024 ** 3)  # 8 GB
        mock_psutil.virtual_memory.return_value = mock_mem

        with patch.dict(sys.modules, {"psutil": mock_psutil}), \
             patch("src.yeyonet.resource_monitor._detect_gpu", return_value=(None, 0, 0.0)), \
             patch("src.yeyonet.resource_monitor._detect_ollama_models", new_callable=AsyncMock, return_value=[]):
            result = await mon.snapshot()

            assert isinstance(result, NodeResources)
            assert result.cpu_percent == 25.0
            assert result.ram_free_gb == 8.0

    @pytest.mark.asyncio
    async def test_snapshot_handles_psutil_import_error(self):
        """If psutil is not available, snapshot still returns defaults."""
        mon = ResourceMonitor()

        with patch.dict(sys.modules, {"psutil": None}), \
             patch("src.yeyonet.resource_monitor._detect_gpu", return_value=(None, 0, 0.0)), \
             patch("src.yeyonet.resource_monitor._detect_ollama_models", new_callable=AsyncMock, return_value=[]):
            result = await mon.snapshot()
            assert isinstance(result, NodeResources)

    @pytest.mark.asyncio
    async def test_snapshot_updates_last_resources(self):
        mon = ResourceMonitor()

        mock_psutil = MagicMock()
        mock_psutil.cpu_percent.return_value = 10.0
        mock_mem = MagicMock()
        mock_mem.available = 16 * (1024 ** 3)
        mock_psutil.virtual_memory.return_value = mock_mem

        with patch.dict(sys.modules, {"psutil": mock_psutil}), \
             patch("src.yeyonet.resource_monitor._detect_gpu", return_value=("Apple M2", 0, 0.0)), \
             patch("src.yeyonet.resource_monitor._detect_ollama_models", new_callable=AsyncMock, return_value=["llama3"]):
            await mon.snapshot()

            assert mon.last_resources.cpu_percent == 10.0
            assert mon.last_resources.gpu_name == "Apple M2"
            assert mon.last_resources.ollama_models == ["llama3"]

    def test_set_callback(self):
        mon = ResourceMonitor()
        cb = AsyncMock()
        mon.set_callback(cb)
        assert mon._callback is cb


class TestDetectGpu:
    """Tests for _detect_gpu function."""

    def test_darwin_apple_silicon(self):
        mock_subprocess = MagicMock()
        result = MagicMock()
        result.stdout = "Chipset Model: Apple M2 Pro\n"
        mock_subprocess.run.return_value = result

        with patch("src.yeyonet.resource_monitor.platform") as mock_platform, \
             patch.dict(sys.modules, {"subprocess": mock_subprocess}):
            mock_platform.system.return_value = "Darwin"

            name, vram, usage = _detect_gpu()
            assert name == "Apple M2 Pro"
            assert vram == 0
            assert usage == 0.0

    def test_nvidia_gpu(self):
        mock_subprocess = MagicMock()
        nvidia_result = MagicMock()
        nvidia_result.returncode = 0
        nvidia_result.stdout = "NVIDIA GeForce RTX 4090, 24576, 35\n"
        mock_subprocess.run.return_value = nvidia_result

        with patch("src.yeyonet.resource_monitor.platform") as mock_platform, \
             patch.dict(sys.modules, {"subprocess": mock_subprocess}):
            mock_platform.system.return_value = "Linux"

            name, vram, usage = _detect_gpu()
            assert name == "NVIDIA GeForce RTX 4090"
            assert vram == 24576
            assert usage == 35.0

    def test_no_gpu(self):
        mock_subprocess = MagicMock()
        mock_subprocess.run.side_effect = FileNotFoundError

        with patch("src.yeyonet.resource_monitor.platform") as mock_platform, \
             patch.dict(sys.modules, {"subprocess": mock_subprocess}):
            mock_platform.system.return_value = "Linux"

            name, vram, usage = _detect_gpu()
            assert name is None
            assert vram == 0
            assert usage == 0.0


class TestDetectOllamaModels:
    """Tests for _detect_ollama_models function."""

    @pytest.mark.asyncio
    async def test_detect_models_success(self):
        mock_httpx = MagicMock()
        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "models": [{"name": "llama3"}, {"name": "mistral"}]
        }
        mock_client.get.return_value = mock_resp
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_client)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_httpx.AsyncClient.return_value = mock_ctx

        with patch.dict(sys.modules, {"httpx": mock_httpx}):
            models = await _detect_ollama_models()
            assert models == ["llama3", "mistral"]

    @pytest.mark.asyncio
    async def test_detect_models_connection_error(self):
        mock_httpx = MagicMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(side_effect=Exception("Connection refused"))
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_httpx.AsyncClient.return_value = mock_ctx

        with patch.dict(sys.modules, {"httpx": mock_httpx}):
            models = await _detect_ollama_models()
            assert models == []
