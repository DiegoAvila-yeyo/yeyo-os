"""Tests para YeyoNet relay."""
import time

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.yeyonet.relay import ConnectedNode, YeyoNetRelay, HEARTBEAT_TIMEOUT
from src.yeyonet.protocol import MessageType, NetMessage


class TestConnectedNode:
    """Tests for ConnectedNode."""

    def test_is_alive_true(self):
        ws = AsyncMock()
        node = ConnectedNode(node_id="node-1", ws=ws)
        assert node.is_alive is True

    def test_is_alive_false_after_timeout(self):
        ws = AsyncMock()
        node = ConnectedNode(node_id="node-1", ws=ws)
        node.last_seen = time.time() - HEARTBEAT_TIMEOUT - 1
        assert node.is_alive is False

    def test_touch_updates_last_seen(self):
        ws = AsyncMock()
        node = ConnectedNode(node_id="node-1", ws=ws)
        node.last_seen = 0
        node.touch()
        assert node.is_alive is True

    def test_authenticated_default_false(self):
        ws = AsyncMock()
        node = ConnectedNode(node_id="node-1", ws=ws)
        assert node.authenticated is False


class TestYeyoNetRelay:
    """Tests for YeyoNetRelay."""

    def _make_relay(self):
        sat_mgr = AsyncMock()
        relay = YeyoNetRelay(satellite_manager=sat_mgr, central_node_id="central-123")
        return relay, sat_mgr

    def test_initial_state(self):
        relay, _ = self._make_relay()
        assert relay.connected_count == 0
        assert relay.get_connected_ids() == []

    def test_on_message_registers_handler(self):
        relay, _ = self._make_relay()

        async def handler(msg, node_id):
            pass

        relay.on_message(MessageType.JOB_PROGRESS, handler)
        assert MessageType.JOB_PROGRESS in relay._handlers
        assert handler in relay._handlers[MessageType.JOB_PROGRESS]

    def test_on_message_multiple_handlers(self):
        relay, _ = self._make_relay()

        async def h1(msg, nid): pass
        async def h2(msg, nid): pass

        relay.on_message(MessageType.JOB_PROGRESS, h1)
        relay.on_message(MessageType.JOB_PROGRESS, h2)

        assert len(relay._handlers[MessageType.JOB_PROGRESS]) == 2

    def test_get_connected_ids(self):
        relay, _ = self._make_relay()
        ws = AsyncMock()
        relay._nodes["node-a"] = ConnectedNode("node-a", ws)
        relay._nodes["node-b"] = ConnectedNode("node-b", ws)

        ids = relay.get_connected_ids()
        assert set(ids) == {"node-a", "node-b"}

    @pytest.mark.asyncio
    async def test_send_to_node_success(self):
        relay, _ = self._make_relay()
        ws = AsyncMock()
        node = ConnectedNode("node-a", ws)
        node.authenticated = True
        relay._nodes["node-a"] = node

        msg = NetMessage(type=MessageType.HEARTBEAT, from_node="central-123")
        result = await relay.send_to_node("node-a", msg)

        assert result is True
        ws.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_to_node_not_connected(self):
        relay, _ = self._make_relay()
        msg = NetMessage(type=MessageType.HEARTBEAT)

        result = await relay.send_to_node("nonexistent", msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_send_to_node_not_authenticated(self):
        relay, _ = self._make_relay()
        ws = AsyncMock()
        node = ConnectedNode("node-a", ws)
        node.authenticated = False
        relay._nodes["node-a"] = node

        msg = NetMessage(type=MessageType.HEARTBEAT)
        result = await relay.send_to_node("node-a", msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_send_to_node_ws_error(self):
        relay, _ = self._make_relay()
        ws = AsyncMock()
        ws.send_text.side_effect = Exception("connection closed")
        node = ConnectedNode("node-a", ws)
        node.authenticated = True
        relay._nodes["node-a"] = node

        msg = NetMessage(type=MessageType.HEARTBEAT)
        result = await relay.send_to_node("node-a", msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_broadcast(self):
        relay, _ = self._make_relay()

        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws3 = AsyncMock()

        n1 = ConnectedNode("n1", ws1)
        n1.authenticated = True
        n2 = ConnectedNode("n2", ws2)
        n2.authenticated = True
        n3 = ConnectedNode("n3", ws3)
        n3.authenticated = False  # not authenticated

        relay._nodes = {"n1": n1, "n2": n2, "n3": n3}

        msg = NetMessage(type=MessageType.STATUS_UPDATE, from_node="central-123")
        sent = await relay.broadcast(msg)

        assert sent == 2  # only authenticated nodes
        ws1.send_text.assert_called_once()
        ws2.send_text.assert_called_once()
        ws3.send_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_broadcast_with_exclude(self):
        relay, _ = self._make_relay()

        ws1 = AsyncMock()
        ws2 = AsyncMock()

        n1 = ConnectedNode("n1", ws1)
        n1.authenticated = True
        n2 = ConnectedNode("n2", ws2)
        n2.authenticated = True

        relay._nodes = {"n1": n1, "n2": n2}

        msg = NetMessage(type=MessageType.STATUS_UPDATE)
        sent = await relay.broadcast(msg, exclude="n1")

        assert sent == 1
        ws1.send_text.assert_not_called()
        ws2.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_handles_send_errors(self):
        relay, _ = self._make_relay()

        ws1 = AsyncMock()
        ws1.send_text.side_effect = Exception("broken")
        ws2 = AsyncMock()

        n1 = ConnectedNode("n1", ws1)
        n1.authenticated = True
        n2 = ConnectedNode("n2", ws2)
        n2.authenticated = True

        relay._nodes = {"n1": n1, "n2": n2}

        msg = NetMessage(type=MessageType.STATUS_UPDATE)
        sent = await relay.broadcast(msg)

        assert sent == 1  # only n2 succeeded
