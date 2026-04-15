"""Tests para YeyoNet sync_manager."""
import uuid
from datetime import datetime, timezone

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.yeyonet.sync_manager import SyncManager
from src.yeyonet.models import Permission, YeyoNetNode, NodeRole, SatelliteMode, NodeStatus
from src.yeyonet.protocol import MessageType, NetMessage


def _make_pool():
    pool = MagicMock()
    conn = AsyncMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=conn)
    ctx.__aexit__ = AsyncMock(return_value=False)
    pool.acquire.return_value = ctx
    return pool, conn


def _make_node(node_id: str, visibility: int = 3, permissions=None):
    """Create a YeyoNetNode for testing."""
    return YeyoNetNode(
        id=node_id,
        name="TestSat",
        role=NodeRole.SATELLITE,
        mode=SatelliteMode.COMPLETO,
        status=NodeStatus.ONLINE,
        permissions=permissions or [Permission.CHAT, Permission.MEMORIA],
        visibility_level=visibility,
    )


class TestOfflineQueue:
    """Tests for offline queue operations."""

    def test_queue_offline_adds_item(self):
        pool, _ = _make_pool()
        mgr = SyncManager(pool)

        mgr.queue_offline("node-1", {"content": "hello"})
        assert mgr.get_offline_queue_size("node-1") == 1

    def test_queue_offline_multiple_items(self):
        pool, _ = _make_pool()
        mgr = SyncManager(pool)

        mgr.queue_offline("node-1", {"content": "a"})
        mgr.queue_offline("node-1", {"content": "b"})
        mgr.queue_offline("node-2", {"content": "c"})

        assert mgr.get_offline_queue_size("node-1") == 2
        assert mgr.get_offline_queue_size("node-2") == 1

    def test_get_all_queue_sizes(self):
        pool, _ = _make_pool()
        mgr = SyncManager(pool)

        mgr.queue_offline("n1", {"content": "a"})
        mgr.queue_offline("n2", {"content": "b"})
        mgr.queue_offline("n2", {"content": "c"})

        sizes = mgr.get_offline_queue_size()
        assert sizes == {"n1": 1, "n2": 2}

    def test_empty_queue_returns_zero(self):
        pool, _ = _make_pool()
        mgr = SyncManager(pool)
        assert mgr.get_offline_queue_size("nonexistent") == 0

    @pytest.mark.asyncio
    async def test_flush_offline_queue(self):
        pool, conn = _make_pool()
        mgr = SyncManager(pool)

        mgr.queue_offline("node-1", {"content": "hello", "type": "fact"})
        mgr.queue_offline("node-1", {"content": "world", "type": "fact"})

        # _store_synced_memory returns True (success)
        conn.fetchval.return_value = None  # no existing checksum
        conn.execute.return_value = "INSERT 0 1"

        count = await mgr.flush_offline_queue("node-1")
        assert count == 2
        assert mgr.get_offline_queue_size("node-1") == 0

    @pytest.mark.asyncio
    async def test_flush_empty_queue(self):
        pool, _ = _make_pool()
        mgr = SyncManager(pool)
        count = await mgr.flush_offline_queue("node-1")
        assert count == 0


class TestGetSyncStats:
    """Tests for get_sync_stats."""

    @pytest.mark.asyncio
    async def test_get_sync_stats(self):
        pool, conn = _make_pool()
        conn.fetchval.side_effect = [42, 1000]  # synced, total

        mgr = SyncManager(pool)
        mgr.queue_offline("n1", {"content": "pending"})

        stats = await mgr.get_sync_stats()

        assert stats["synced_memories"] == 42
        assert stats["total_memories"] == 1000
        assert stats["offline_queue_size"] == 1
        assert "n1" in stats["offline_queues"]


class TestHandleMemorySync:
    """Tests for handle_memory_sync."""

    @pytest.mark.asyncio
    async def test_empty_memories_sends_ack(self):
        pool, conn = _make_pool()
        relay = AsyncMock()

        mgr = SyncManager(pool, relay=relay)

        msg = NetMessage(
            type=MessageType.MEMORY_SYNC,
            from_node="sat-1",
            payload={"memories": [], "namespace": "chat"},
        )
        await mgr.handle_memory_sync(msg, "sat-1")

        relay.send_to_node.assert_called_once()
        sent_msg = relay.send_to_node.call_args[0][1]
        assert sent_msg.type == MessageType.MEMORY_SYNC_ACK
        assert sent_msg.payload["synced"] == 0

    @pytest.mark.asyncio
    async def test_permission_denied_low_visibility(self):
        """Nodes with visibility < 3 and no memoria permission are denied."""
        pool, conn = _make_pool()
        relay = AsyncMock()
        node_id = str(uuid.uuid4())

        # _get_node will find this node
        node_row = {
            "id": uuid.UUID(node_id),
            "name": "LowVis",
            "role": "satellite",
            "mode": "completo",
            "status": "online",
            "auth_token": "tok",
            "permissions": '["chat"]',  # no "memoria"
            "visibility_level": 1,
            "resources": "{}",
            "ollama_host": None,
            "ip_address": None,
            "last_seen_at": datetime.utcnow(),
            "created_at": datetime.utcnow(),
        }
        conn.fetchrow.return_value = node_row

        mgr = SyncManager(pool, relay=relay)
        msg = NetMessage(
            type=MessageType.MEMORY_SYNC,
            from_node=node_id,
            payload={"memories": [{"content": "test"}]},
        )
        await mgr.handle_memory_sync(msg, node_id)

        # Should send ack with permission denied error
        relay.send_to_node.assert_called_once()
        sent_msg = relay.send_to_node.call_args[0][1]
        assert sent_msg.payload["synced"] == 0
        assert "Permission denied" in sent_msg.payload["errors"][0]

    @pytest.mark.asyncio
    async def test_dedup_by_checksum(self):
        """Existing checksum skips storage if local is newer."""
        pool, conn = _make_pool()
        relay = AsyncMock()
        node_id = str(uuid.uuid4())

        # _get_node returns valid node with memoria permission
        node_row = {
            "id": uuid.UUID(node_id),
            "name": "PermittedSat",
            "role": "satellite",
            "mode": "completo",
            "status": "online",
            "auth_token": "tok",
            "permissions": '["chat", "memoria"]',
            "visibility_level": 3,
            "resources": "{}",
            "ollama_host": None,
            "ip_address": None,
            "last_seen_at": datetime.utcnow(),
            "created_at": datetime.utcnow(),
        }

        # First fetchrow is _get_node, then _store_synced_memory uses fetchval
        conn.fetchrow.return_value = node_row
        # fetchval for dedup check: existing ID found, then local_ts
        existing_id = uuid.uuid4()
        local_ts = datetime(2025, 6, 1, tzinfo=timezone.utc)
        conn.fetchval.side_effect = [existing_id, local_ts]

        mgr = SyncManager(pool, relay=relay)
        msg = NetMessage(
            type=MessageType.MEMORY_SYNC,
            from_node=node_id,
            payload={
                "memories": [{
                    "content": "hello",
                    "checksum": "abc123",
                    "updated_at": "2025-01-01T00:00:00",  # older than local
                }],
            },
        )
        await mgr.handle_memory_sync(msg, node_id)

        # Ack synced 0 because local is newer
        relay.send_to_node.assert_called_once()
        sent_msg = relay.send_to_node.call_args[0][1]
        assert sent_msg.payload["synced"] == 0

    @pytest.mark.asyncio
    async def test_conflict_resolution_remote_newer_wins(self):
        """When remote is newer than local, update metadata."""
        pool, conn = _make_pool()
        relay = AsyncMock()
        node_id = str(uuid.uuid4())

        node_row = {
            "id": uuid.UUID(node_id),
            "name": "Sat",
            "role": "satellite",
            "mode": "completo",
            "status": "online",
            "auth_token": "tok",
            "permissions": '["memoria"]',
            "visibility_level": 3,
            "resources": "{}",
            "ollama_host": None,
            "ip_address": None,
            "last_seen_at": datetime.utcnow(),
            "created_at": datetime.utcnow(),
        }
        conn.fetchrow.return_value = node_row

        existing_id = uuid.uuid4()
        local_ts = datetime(2025, 1, 1, tzinfo=timezone.utc)
        conn.fetchval.side_effect = [existing_id, local_ts]
        conn.execute.return_value = "UPDATE 1"

        mgr = SyncManager(pool, relay=relay)
        msg = NetMessage(
            type=MessageType.MEMORY_SYNC,
            from_node=node_id,
            payload={
                "memories": [{
                    "content": "updated",
                    "checksum": "abc123",
                    "updated_at": "2025-12-01T00:00:00",  # newer than local
                    "metadata": {"key": "val"},
                }],
            },
        )
        await mgr.handle_memory_sync(msg, node_id)

        sent_msg = relay.send_to_node.call_args[0][1]
        assert sent_msg.payload["synced"] == 1
