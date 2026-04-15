"""Tests para YeyoNet invite_manager."""
import re
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.yeyonet.invite_manager import InviteManager, generate_invite_code, _CODE_CHARS
from src.yeyonet.models import Permission


def _make_pool():
    pool = MagicMock()
    conn = AsyncMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=conn)
    ctx.__aexit__ = AsyncMock(return_value=False)
    pool.acquire.return_value = ctx
    return pool, conn


class TestGenerateInviteCode:
    """Tests for generate_invite_code."""

    def test_format_matches_pattern(self):
        code = generate_invite_code()
        assert re.match(r"^YEYO-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$", code)

    def test_length_is_19(self):
        assert len(generate_invite_code()) == 19

    def test_no_ambiguous_characters(self):
        """Codes should not contain O, I, L, 0, 1."""
        for _ in range(50):
            code = generate_invite_code()
            # Strip the prefix and dashes to check only generated chars
            chars = code.replace("YEYO-", "").replace("-", "")
            for c in chars:
                assert c in _CODE_CHARS, f"Unexpected char '{c}' in code {code}"

    def test_codes_are_unique(self):
        codes = {generate_invite_code() for _ in range(200)}
        assert len(codes) == 200


class TestInviteManager:
    """Tests for InviteManager."""

    @pytest.mark.asyncio
    async def test_create_invitation(self):
        pool, conn = _make_pool()
        now = datetime.utcnow()
        conn.fetchrow.return_value = {
            "id": uuid.uuid4(),
            "code": "YEYO-TEST-CODE-ABCD",
            "satellite_name": "MySat",
            "permissions": '["chat"]',
            "visibility_level": 1,
            "used": False,
            "used_by_node_id": None,
            "used_at": None,
            "expires_at": now + timedelta(days=7),
            "created_at": now,
        }

        mgr = InviteManager(pool)
        inv = await mgr.create_invitation("MySat")

        assert inv.satellite_name == "MySat"
        assert not inv.used
        conn.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_code_found(self):
        pool, conn = _make_pool()
        now = datetime.utcnow()
        conn.fetchrow.return_value = {
            "id": uuid.uuid4(),
            "code": "YEYO-ABCD-EFGH-JKLM",
            "satellite_name": "TestSat",
            "permissions": '["chat"]',
            "visibility_level": 1,
            "used": False,
            "used_by_node_id": None,
            "used_at": None,
            "expires_at": now + timedelta(days=7),
            "created_at": now,
        }

        mgr = InviteManager(pool)
        result = await mgr.validate_code("YEYO-ABCD-EFGH-JKLM")

        assert result is not None
        assert result.code == "YEYO-ABCD-EFGH-JKLM"

    @pytest.mark.asyncio
    async def test_validate_code_not_found(self):
        pool, conn = _make_pool()
        conn.fetchrow.return_value = None

        mgr = InviteManager(pool)
        result = await mgr.validate_code("YEYO-XXXX-XXXX-XXXX")
        assert result is None

    @pytest.mark.asyncio
    async def test_validate_code_already_used(self):
        pool, conn = _make_pool()
        now = datetime.utcnow()
        conn.fetchrow.return_value = {
            "id": uuid.uuid4(),
            "code": "YEYO-USED-CODE-AAAA",
            "satellite_name": "UsedSat",
            "permissions": '["chat"]',
            "visibility_level": 1,
            "used": True,
            "used_by_node_id": uuid.uuid4(),
            "used_at": now,
            "expires_at": now + timedelta(days=7),
            "created_at": now,
        }

        mgr = InviteManager(pool)
        result = await mgr.validate_code("YEYO-USED-CODE-AAAA")
        assert result is None

    @pytest.mark.asyncio
    async def test_validate_code_expired(self):
        pool, conn = _make_pool()
        now = datetime.utcnow()
        conn.fetchrow.return_value = {
            "id": uuid.uuid4(),
            "code": "YEYO-EXPI-REDD-BBBB",
            "satellite_name": "ExpiredSat",
            "permissions": '["chat"]',
            "visibility_level": 1,
            "used": False,
            "used_by_node_id": None,
            "used_at": None,
            "expires_at": now - timedelta(days=1),
            "created_at": now - timedelta(days=8),
        }

        mgr = InviteManager(pool)
        result = await mgr.validate_code("YEYO-EXPI-REDD-BBBB")
        assert result is None

    @pytest.mark.asyncio
    async def test_mark_used_success(self):
        pool, conn = _make_pool()
        conn.execute.return_value = "UPDATE 1"

        mgr = InviteManager(pool)
        result = await mgr.mark_used("YEYO-ABCD-EFGH-JKLM", str(uuid.uuid4()))
        assert result is True

    @pytest.mark.asyncio
    async def test_mark_used_not_found(self):
        pool, conn = _make_pool()
        conn.execute.return_value = "UPDATE 0"

        mgr = InviteManager(pool)
        result = await mgr.mark_used("YEYO-NOOO-OOOO-OOOO", str(uuid.uuid4()))
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_invitation(self):
        pool, conn = _make_pool()
        conn.execute.return_value = "DELETE 1"

        mgr = InviteManager(pool)
        result = await mgr.delete_invitation(str(uuid.uuid4()))
        assert result is True
