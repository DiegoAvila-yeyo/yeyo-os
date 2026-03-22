"""
Tests de Integración — Capa 5: Órganos
Micro-fase 5.21

Test completo de todos los nodos, registry, API, MiniChat, health monitor.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.nodes.base import NodeBase, NodeStatus, PrivilegeLevel
from src.nodes.registry import NodeRegistry, NodeNotFoundError
from src.nodes.health_monitor import NodeHealthMonitor, MAX_RESTART_ATTEMPTS


# ═══════════════════════════════════
# SECTION 1: NodeBase Contract
# ═══════════════════════════════════

class TestNodeBaseContract:

    def test_nodebase_is_abstract(self):
        with pytest.raises(TypeError):
            NodeBase(name="test", version="1.0")

    def test_abstract_methods_count(self):
        assert len(NodeBase.__abstractmethods__) == 4

    def test_abstract_methods_names(self):
        expected = {"initialize", "render_ui", "process", "cleanup"}
        assert NodeBase.__abstractmethods__ == expected


# ═══════════════════════════════════
# SECTION 2: Node Registry
# ═══════════════════════════════════

class ConcreteNode(NodeBase):
    async def initialize(self): pass
    async def render_ui(self) -> dict: return {"component": "Test"}
    async def process(self, input_data: dict) -> dict: return input_data
    async def cleanup(self): pass
    def __init__(self): super().__init__(name="Concrete", version="1.0")


class TestNodeRegistryIntegration:

    def setup_method(self):
        NodeRegistry.clear()

    def test_register_and_create(self):
        NodeRegistry.register("concrete", ConcreteNode)
        node = NodeRegistry.create("concrete")
        assert isinstance(node, ConcreteNode)
        assert isinstance(node, NodeBase)

    def test_create_unknown_raises(self):
        with pytest.raises(NodeNotFoundError):
            NodeRegistry.create("nonexistent")

    def test_list_types_after_register(self):
        NodeRegistry.register("a", ConcreteNode)
        NodeRegistry.register("b", ConcreteNode)
        types = NodeRegistry.list_types()
        assert len(types) == 2


# ═══════════════════════════════════
# SECTION 3: Node Lifecycle
# ═══════════════════════════════════

class TestNodeLifecycleIntegration:

    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        node = ConcreteNode()
        assert node.status == NodeStatus.CREATED

        await node.open()
        assert node.status == NodeStatus.READY

        result = await node.process({"test": True})
        assert result["test"] is True

        ui = await node.render_ui()
        assert "component" in ui

        await node.close()
        assert node.status == NodeStatus.CLOSED

    @pytest.mark.asyncio
    async def test_status_reporting(self):
        node = ConcreteNode()
        status = await node.get_status()
        assert status["name"] == "Concrete"
        assert status["gpu_allocated"] is False


# ═══════════════════════════════════
# SECTION 4: GPU Scheduling (Mock)
# ═══════════════════════════════════

class TestGPUSchedulingIntegration:

    @pytest.mark.asyncio
    async def test_mining_node_gpu_blocked(self):
        from src.nodes.mining.service import MiningNode
        mining = MiningNode()
        result = await mining.request_gpu(vram_mb=1024)
        assert result is False


# ═══════════════════════════════════
# SECTION 5: MiniChat Context
# ═══════════════════════════════════

class TestMiniChatContextIntegration:

    def test_context_changes_per_node_type(self):
        from src.minichat.service import MiniChatV2Service
        service = MiniChatV2Service()

        service.set_context("image", "node-1")
        image_suggestions = service.get_suggestions()

        service.set_context("code", "node-2")
        code_suggestions = service.get_suggestions()

        assert image_suggestions != code_suggestions


# ═══════════════════════════════════
# SECTION 6: MiniChat Actions
# ═══════════════════════════════════

class TestMiniChatActionsIntegration:

    def test_action_detection_per_node(self):
        from src.minichat.actions import ActionDetector, ActionType
        detector = ActionDetector()

        img_action = detector.detect("genera una imagen de un gato", "image")
        assert img_action.action_type == ActionType.GENERATE_IMAGE

        code_action = detector.detect("ejecuta este código", "code")
        assert code_action.action_type == ActionType.EXECUTE_CODE

        video_action = detector.detect("recorta del minuto 2 al 5", "video")
        assert video_action.action_type == ActionType.TRIM_VIDEO

        normal = detector.detect("hola mundo", "image")
        assert normal.action_type == ActionType.NONE

    def test_actions_require_confirmation(self):
        from src.minichat.actions import ActionDetector
        detector = ActionDetector()

        action = detector.detect("genera una imagen de un paisaje", "image")
        assert action.requires_confirmation is True


# ═══════════════════════════════════
# SECTION 7: Health Monitor
# ═══════════════════════════════════

class TestHealthMonitorIntegration:

    @pytest.mark.asyncio
    async def test_monitor_healthy_nodes(self):
        monitor = NodeHealthMonitor()
        node1 = ConcreteNode()
        node1.status = NodeStatus.READY
        node2 = ConcreteNode()
        node2.status = NodeStatus.READY

        results = await monitor.check_all({node1.id: node1, node2.id: node2})
        assert len(results) == 2
        assert all(r.is_healthy for r in results)

    @pytest.mark.asyncio
    async def test_monitor_detects_crash_and_restarts(self):
        monitor = NodeHealthMonitor()
        node = ConcreteNode()
        node.status = NodeStatus.ERROR
        node.close = AsyncMock()
        node.open = AsyncMock(side_effect=lambda: setattr(node, 'status', NodeStatus.READY))

        result = await monitor.check_node(node)
        assert result.restart_count >= 1

    def test_max_restart_is_three(self):
        assert MAX_RESTART_ATTEMPTS == 3

    @pytest.mark.asyncio
    async def test_health_report(self):
        monitor = NodeHealthMonitor()
        node = ConcreteNode()
        node.status = NodeStatus.READY
        await monitor.check_node(node)

        report = monitor.get_health_report()
        assert report["total_nodes"] == 1
        assert report["healthy"] == 1


# ═══════════════════════════════════
# SECTION 8: Security Checks
# ═══════════════════════════════════

class TestSecurityIntegration:

    def test_sandbox_code_config(self):
        from src.nodes.code.sandbox import SANDBOX_CONFIG
        assert SANDBOX_CONFIG["timeout_seconds"] == 30
        assert SANDBOX_CONFIG["memory_mb"] == 256

    def test_ffmpeg_validation_blocks_dangerous(self):
        from src.nodes.video.ffmpeg_validator import FFmpegValidator
        validator = FFmpegValidator()

        result = validator.validate("ffmpeg -y -i input.mp4 output.mp4")
        assert result.is_valid is False

        result = validator.validate("ffmpeg -i input.mp4 output.mp4; rm -rf /")
        assert result.is_valid is False

    def test_ffmpeg_validation_allows_safe(self):
        from src.nodes.video.ffmpeg_validator import FFmpegValidator
        validator = FFmpegValidator()

        result = validator.validate("ffmpeg -i input.mp4 -ss 00:02:00 -c copy output.mp4")
        assert result.is_valid is True

    def test_mining_node_gpu_flag(self):
        from src.nodes.mining.service import MiningNode
        assert MiningNode.GPU_MINING_BLOCKED is True
