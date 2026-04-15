"""Tests para YeyoNet satellite_manager."""
import uuid
from datetime import datetime

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.yeyonet.satellite_manager import SatelliteManager
from src.yeyonet.models import Permission, SatelliteMode, NodeResources


def _make_pool():
    pool = MagicMock()
    conn = AsyncMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=conn)
    ctx.__aexit__ = AsyncMock(return_value=False)
    pool.acquire.return_value = ctx
    return pool, conn


def _fake_node_row(**overrides):
    """Create a fake DB row dict that _row_to_node can consume."""
    defaults = {
        "id": uuid.uuid4(),
        "name": "TestSat",
        "role": "satellite",
        "mode": "completo",
        "status": "online",
        "auth_token": str(uuid.uuid4()),
        "permissions": '["chat"]',
        "visibility_level": 1,
        "resources": "{}",
        "ollama_host": None,
        "ip_address": None,
        "last_seen_at": datetime.utcnow(),
        "created_at": datetime.utcnow(),
    }
    defaults.update(overrides)
    return defaults


class TestSatelliteManagerAuthenticate:
    """Tests for authenticate method."""

    @pytest.mark.asyncio
    async def test_authenticate_valid_token(self):
        pool, conn = _make_pool()
        conn.fetchrow.return_value = _fake_node_row(name="MySatellite")

        mgr = SatelliteManager(pool)
        node = await mgr.authenticate("valid-token")

        assert node is not None
        assert node.name == "MySatellite"

    @pytest.mark.asyncio
    async def test_authenticate_invalid_token(self):
        pool, conn = _make_pool()
        conn.fetchrow.return_value = None

        mgr = SatelliteManager(pool)
        node = await mgr.authenticate("bad-token")
        assert node is None


class TestSatelliteManagerGetSatellite:
    """Tests for get_satellite method."""

    @pytest.mark.asyncio
    async def test_get_existing(self):
        pool, conn = _make_pool()
        node_id = str(uuid.uuid4())
        conn.fetchrow.return_value = _fake_node_row(id=uuid.UUID(node_id), name="FoundNode")

        mgr = SatelliteManager(pool)
        node = await mgr.get_satellite(node_id)

        assert node is not None
        assert node.name == "FoundNode"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self):
        pool, conn = _make_pool()
        conn.fetchrow.return_value = None

        mgr = SatelliteManager(pool)
        node = await mgr.get_satellite(str(uuid.uuid4()))
        assert node is None


class TestSatelliteManagerUpdate:
    """Tests for update_satellite method."""

    @pytest.mark.asyncio
    async def test_update_permissions(self):
        pool, conn = _make_pool()
        node_id = str(uuid.uuid4())
        conn.fetchrow.return_value = _fake_node_row(
            id=uuid.UUID(node_id),
            permissions='["chat", "grafos"]',
        )

        mgr = SatelliteManager(pool)
        node = await mgr.update_satellite(
            node_id,
            permissions=[Permission.CHAT, Permission.GRAFOS],
        )

        assert node is not None
        conn.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_no_changes_delegates_to_get(self):
        pool, conn = _make_pool()
        node_id = str(uuid.uuid4())
        conn.fetchrow.return_value = _fake_node_row(id=uuid.UUID(node_id))

        mgr = SatelliteManager(pool)
        node = await mgr.update_satellite(node_id)

        assert node is not None
        # When no changes, it calls get_satellite which uses fetchrow
        assert conn.fetchrow.call_count == 1


class TestSatelliteManagerRefreshStatuses:
    """Tests for refresh_statuses method."""

    @pytest.mark.asyncio
    async def test_refresh_statuses_counts(self):
        pool, conn = _make_pool()
        conn.execute.side_effect = ["UPDATE 2", "UPDATE 1"]

        mgr = SatelliteManager(pool)
        count = await mgr.refresh_statuses()

        assert count == 3
        assert conn.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_refresh_statuses_zero(self):
        pool, conn = _make_pool()
        conn.execute.side_effect = ["UPDATE 0", "UPDATE 0"]

        mgr = SatelliteManager(pool)
        count = await mgr.refresh_statuses()
        assert count == 0


class TestSatelliteManagerRemove:
    """Tests for remove_satellite method."""

    @pytest.mark.asyncio
    async def test_remove_success(self):
        pool, conn = _make_pool()
        conn.execute.return_value = "DELETE 1"

        mgr = SatelliteManager(pool)
        result = await mgr.remove_satellite(str(uuid.uuid4()))
        assert result is True

    @pytest.mark.asyncio
    async def test_remove_not_found(self):
        pool, conn = _make_pool()
        conn.execute.return_value = "DELETE 0"

        mgr = SatelliteManager(pool)
        result = await mgr.remove_satellite(str(uuid.uuid4()))
        assert result is False


class TestSatelliteManagerHeartbeat:
    """Tests for update_heartbeat method."""

    @pytest.mark.asyncio
    async def test_heartbeat_without_resources(self):
        pool, conn = _make_pool()

        mgr = SatelliteManager(pool)
        await mgr.update_heartbeat(str(uuid.uuid4()))

        conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_heartbeat_with_resources(self):
        pool, conn = _make_pool()
        resources = NodeResources(cpu_percent=30.0, ram_free_gb=12.0)

        mgr = SatelliteManager(pool)
        await mgr.update_heartbeat(str(uuid.uuid4()), resources)

        conn.execute.assert_called_once()
        call_args = conn.execute.call_args
        # The query should include resources JSON
        assert "resources" in call_args[0][0]
