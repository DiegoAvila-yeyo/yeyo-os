"""Tests para NodeBase Template — Micro-fase 5.0"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.nodes.base import NodeBase, NodeStatus, PrivilegeLevel, NodeEvent


class ConcreteNode(NodeBase):
    """Implementación concreta para testing."""

    async def initialize(self):
        pass

    async def render_ui(self) -> dict:
        return {"component": "TestNode", "props": {}}

    async def process(self, input_data: dict) -> dict:
        return {"result": "processed", **input_data}

    async def cleanup(self):
        pass


class TestNodeBaseAbstract:
    """Tests para verificar que NodeBase es abstracta."""

    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            NodeBase(name="test", version="1.0")

    def test_all_abstract_methods_present(self):
        abstract_methods = NodeBase.__abstractmethods__
        expected = {"initialize", "render_ui", "process", "cleanup"}
        assert abstract_methods == expected

    def test_has_four_abstract_methods(self):
        assert len(NodeBase.__abstractmethods__) == 4


class TestNodeBaseLifecycle:
    """Tests para el lifecycle del nodo."""

    def test_concrete_node_instantiates(self):
        node = ConcreteNode(name="Test", version="1.0")
        assert node.name == "Test"
        assert node.version == "1.0"
        assert node.status == NodeStatus.CREATED

    def test_node_has_unique_id(self):
        node1 = ConcreteNode(name="A", version="1.0")
        node2 = ConcreteNode(name="B", version="1.0")
        assert node1.id != node2.id

    def test_default_privilege_is_sandbox(self):
        node = ConcreteNode(name="Test", version="1.0")
        assert node.privilege_level == PrivilegeLevel.SANDBOX

    def test_custom_privilege_level(self):
        node = ConcreteNode(
            name="Test", version="1.0",
            privilege_level=PrivilegeLevel.USER,
        )
        assert node.privilege_level == PrivilegeLevel.USER

    @pytest.mark.asyncio
    async def test_open_sets_ready(self):
        node = ConcreteNode(name="Test", version="1.0")
        await node.open()
        assert node.status == NodeStatus.READY

    @pytest.mark.asyncio
    async def test_close_sets_closed(self):
        node = ConcreteNode(name="Test", version="1.0")
        await node.open()
        await node.close()
        assert node.status == NodeStatus.CLOSED

    @pytest.mark.asyncio
    async def test_process_returns_result(self):
        node = ConcreteNode(name="Test", version="1.0")
        result = await node.process({"key": "value"})
        assert result["result"] == "processed"
        assert result["key"] == "value"

    @pytest.mark.asyncio
    async def test_render_ui_returns_component(self):
        node = ConcreteNode(name="Test", version="1.0")
        ui = await node.render_ui()
        assert "component" in ui

    @pytest.mark.asyncio
    async def test_get_status_returns_info(self):
        node = ConcreteNode(name="Test", version="1.0")
        status = await node.get_status()
        assert status["name"] == "Test"
        assert status["status"] == "created"
        assert status["gpu_allocated"] is False

    @pytest.mark.asyncio
    async def test_emit_event_stores_event(self):
        node = ConcreteNode(name="Test", version="1.0")
        await node.emit_event("test_event", {"data": 123})
        assert len(node._events) == 1
        assert node._events[0].event_type == "test_event"


class TestNodeBaseGPU:
    """Tests para solicitud de GPU."""

    @pytest.mark.asyncio
    async def test_request_gpu_calls_scheduler(self):
        node = ConcreteNode(name="Test", version="1.0")
        mock_scheduler = MagicMock()
        mock_scheduler.allocate = AsyncMock(return_value=True)
        mock_scheduler.get_instance = MagicMock(return_value=mock_scheduler)

        mock_module = MagicMock()
        mock_module.GPUScheduler = mock_scheduler
        with patch.dict("sys.modules", {"src.core.gpu_scheduler": mock_module}):
            result = await node.request_gpu(vram_mb=1024, priority=3)
            assert result is True
            assert node._gpu_allocated is True
            assert node._gpu_vram_mb == 1024

    @pytest.mark.asyncio
    async def test_release_gpu_frees_resources(self):
        node = ConcreteNode(name="Test", version="1.0")
        node._gpu_allocated = True
        node._gpu_vram_mb = 1024
        mock_scheduler = MagicMock()
        mock_scheduler.release = AsyncMock()
        mock_scheduler.get_instance = MagicMock(return_value=mock_scheduler)

        mock_module = MagicMock()
        mock_module.GPUScheduler = mock_scheduler
        with patch.dict("sys.modules", {"src.core.gpu_scheduler": mock_module}):
            await node.release_gpu()
            assert node._gpu_allocated is False
            assert node._gpu_vram_mb == 0


class TestNodeBasePermissions:
    """Tests para verificación de permisos."""

    @pytest.mark.asyncio
    async def test_check_permission_calls_manager(self):
        node = ConcreteNode(name="Test", version="1.0")
        mock_manager = MagicMock()
        mock_manager.check = AsyncMock(return_value=True)
        mock_manager.get_instance = MagicMock(return_value=mock_manager)

        mock_module = MagicMock()
        mock_module.PermissionManager = mock_manager
        with patch.dict("sys.modules", {"src.security.permissions": mock_module}):
            result = await node.check_permission("file.read")
            assert result is True
            assert "file.read" in node._permissions_granted
