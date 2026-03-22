"""Tests para Node Health Monitor — Micro-fase 5.20"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.nodes.base import NodeBase, NodeStatus, PrivilegeLevel
from src.nodes.health_monitor import (
    NodeHealthMonitor, MAX_RESTART_ATTEMPTS, NodeHealthStatus,
)


class FakeNode(NodeBase):
    async def initialize(self): pass
    async def render_ui(self) -> dict: return {}
    async def process(self, input_data: dict) -> dict: return {}
    async def cleanup(self): pass

    def __init__(self, status=NodeStatus.READY):
        super().__init__(name="Fake", version="1.0")
        self.status = status


class TestHealthMonitorCheck:

    @pytest.mark.asyncio
    async def test_healthy_node_reports_ok(self):
        monitor = NodeHealthMonitor()
        node = FakeNode(status=NodeStatus.READY)
        result = await monitor.check_node(node)
        assert result.is_healthy is True
        assert result.status == "ready"

    @pytest.mark.asyncio
    async def test_crashed_node_detected(self):
        monitor = NodeHealthMonitor()
        node = FakeNode(status=NodeStatus.ERROR)
        node.close = AsyncMock()
        node.open = AsyncMock()
        result = await monitor.check_node(node)
        assert result.restart_count >= 1

    @pytest.mark.asyncio
    async def test_closed_node_not_healthy(self):
        monitor = NodeHealthMonitor()
        node = FakeNode(status=NodeStatus.CLOSED)
        result = await monitor.check_node(node)
        assert result.is_healthy is False
        assert result.status == "closed"


class TestHealthMonitorRestart:

    @pytest.mark.asyncio
    async def test_auto_restart_works(self):
        monitor = NodeHealthMonitor()
        node = FakeNode(status=NodeStatus.ERROR)
        node.close = AsyncMock()
        node.open = AsyncMock(side_effect=lambda: setattr(node, 'status', NodeStatus.READY))

        result = await monitor.check_node(node)
        assert result.restart_count == 1
        assert result.is_healthy is True

    @pytest.mark.asyncio
    async def test_max_restart_attempts_respected(self):
        monitor = NodeHealthMonitor()
        node = FakeNode(status=NodeStatus.ERROR)
        node.close = AsyncMock()
        node.open = AsyncMock()

        record = NodeHealthStatus(
            node_id=node.id, node_name=node.name,
            status="error", restart_count=MAX_RESTART_ATTEMPTS,
        )
        monitor._health_records[node.id] = record

        result = await monitor.check_node(node)
        assert result.status == "failed"
        assert result.is_healthy is False
        assert result.restart_count == MAX_RESTART_ATTEMPTS

    def test_max_restart_is_3(self):
        assert MAX_RESTART_ATTEMPTS == 3


class TestHealthMonitorReport:

    @pytest.mark.asyncio
    async def test_health_report(self):
        monitor = NodeHealthMonitor()
        node1 = FakeNode(status=NodeStatus.READY)
        node2 = FakeNode(status=NodeStatus.READY)

        await monitor.check_node(node1)
        await monitor.check_node(node2)

        report = monitor.get_health_report()
        assert report["total_nodes"] == 2
        assert report["healthy"] == 2
        assert report["unhealthy"] == 0

    def test_register_and_unregister(self):
        monitor = NodeHealthMonitor()
        node = FakeNode()
        monitor.register_node(node)
        assert node.id in monitor._health_records

        monitor.unregister_node(node.id)
        assert node.id not in monitor._health_records

    @pytest.mark.asyncio
    async def test_check_all(self):
        monitor = NodeHealthMonitor()
        node1 = FakeNode(status=NodeStatus.READY)
        node2 = FakeNode(status=NodeStatus.READY)

        results = await monitor.check_all({node1.id: node1, node2.id: node2})
        assert len(results) == 2
        assert all(r.is_healthy for r in results)

    def test_stop_monitoring(self):
        monitor = NodeHealthMonitor()
        monitor._running = True
        monitor.stop_monitoring()
        assert monitor._running is False
