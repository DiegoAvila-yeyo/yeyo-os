"""Tests para YeyoNet identity."""
import uuid

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.yeyonet.identity import NodeIdentity, _row_to_node
from src.yeyonet.models import NodeRole


def _make_pool():
    """Create a mock asyncpg pool with async context-manager acquire()."""
    pool = MagicMock()
    conn = AsyncMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=conn)
    ctx.__aexit__ = AsyncMock(return_value=False)
    pool.acquire.return_value = ctx
    return pool, conn


class TestNodeIdentity:
    """Tests for NodeIdentity."""

    def test_node_id_before_init_raises(self):
        pool, _ = _make_pool()
        identity = NodeIdentity(pool)
        with pytest.raises(RuntimeError, match="no inicializado"):
            _ = identity.node_id

    def test_default_role_is_central(self):
        pool, _ = _make_pool()
        identity = NodeIdentity(pool)
        assert identity.role == NodeRole.CENTRAL

    @pytest.mark.asyncio
    async def test_initialize_creates_new_node(self):
        pool, conn = _make_pool()
        conn.fetchrow.return_value = None  # no existing node
        conn.execute.return_value = "INSERT 0 1"

        identity = NodeIdentity(pool)
        node_id = await identity.initialize(role=NodeRole.CENTRAL, name="Central")

        assert node_id is not None
        uuid.UUID(node_id)  # validates UUID format
        assert identity.node_id == node_id
        assert identity.role == NodeRole.CENTRAL
        conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_recovers_existing_node(self):
        pool, conn = _make_pool()
        existing_id = str(uuid.uuid4())
        conn.fetchrow.return_value = {
            "id": existing_id,
            "name": "Central",
            "role": "central",
        }

        identity = NodeIdentity(pool)
        node_id = await identity.initialize()

        assert node_id == existing_id
        assert identity.node_id == existing_id
        assert identity.role == NodeRole.CENTRAL
        conn.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_node_id_consistent_after_init(self):
        pool, conn = _make_pool()
        conn.fetchrow.return_value = None
        conn.execute.return_value = "INSERT 0 1"

        identity = NodeIdentity(pool)
        first = await identity.initialize()
        assert identity.node_id == first
        # Accessing multiple times returns same value
        assert identity.node_id == first

    @pytest.mark.asyncio
    async def test_get_node_returns_none_before_init(self):
        pool, _ = _make_pool()
        identity = NodeIdentity(pool)
        result = await identity.get_node()
        assert result is None

    @pytest.mark.asyncio
    async def test_update_status(self):
        pool, conn = _make_pool()
        conn.fetchrow.return_value = None
        conn.execute.return_value = "INSERT 0 1"

        identity = NodeIdentity(pool)
        await identity.initialize()
        await identity.update_status("online")

        # Second execute call is the update_status one
        assert conn.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_update_status_noop_before_init(self):
        pool, conn = _make_pool()
        identity = NodeIdentity(pool)
        await identity.update_status("online")
        # Should not have called acquire at all since _node_id is None
        pool.acquire.assert_not_called()


class TestRowToNode:
    """Tests for _row_to_node helper."""

    def test_converts_row_with_string_permissions(self):
        from datetime import datetime
        row = {
            "id": uuid.uuid4(),
            "name": "TestNode",
            "role": "satellite",
            "mode": "completo",
            "status": "online",
            "auth_token": "tok-123",
            "permissions": '["chat", "grafos"]',
            "visibility_level": 2,
            "resources": '{}',
            "ollama_host": None,
            "ip_address": "192.168.1.10",
            "last_seen_at": datetime.utcnow(),
            "created_at": datetime.utcnow(),
        }
        node = _row_to_node(row)
        assert node.name == "TestNode"
        assert node.role == "satellite"
        assert node.permissions == ["chat", "grafos"]

    def test_converts_row_with_list_permissions(self):
        from datetime import datetime
        row = {
            "id": uuid.uuid4(),
            "name": "TestNode",
            "role": "central",
            "mode": "completo",
            "status": "online",
            "auth_token": "tok-456",
            "permissions": ["chat"],
            "visibility_level": 4,
            "resources": None,
            "ollama_host": None,
            "ip_address": None,
            "last_seen_at": None,
            "created_at": datetime.utcnow(),
        }
        node = _row_to_node(row)
        assert node.permissions == ["chat"]
        # resources=None → {} → NodeResources()
        from src.yeyonet.models import NodeResources
        assert node.resources == NodeResources()
