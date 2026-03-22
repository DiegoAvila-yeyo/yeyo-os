"""Tests para PermissionManager — Micro-fase 4.3"""

import pytest
from src.security.permissions import Permission, PermissionManager, PermissionGrant


@pytest.fixture
def manager():
    return PermissionManager()


class TestPermissionManagerBasic:

    @pytest.mark.asyncio
    async def test_check_returns_false_by_default(self, manager):
        result = await manager.check("app-1", Permission.MEMORY_READ)
        assert result is False

    @pytest.mark.asyncio
    async def test_request_grants_permissions(self, manager):
        result = await manager.request("app-1", [Permission.MEMORY_READ])
        assert Permission.MEMORY_READ.value in result["granted"]
        assert await manager.check("app-1", Permission.MEMORY_READ) is True

    @pytest.mark.asyncio
    async def test_allowlist_no_implicit_grants(self, manager):
        await manager.request("app-1", [Permission.MEMORY_READ])
        assert await manager.check("app-1", Permission.MEMORY_WRITE) is False
        assert await manager.check("app-1", Permission.GPU_INFERENCE) is False

    @pytest.mark.asyncio
    async def test_revoke_removes_permission(self, manager):
        await manager.request("app-1", [Permission.CLIPBOARD])
        assert await manager.check("app-1", Permission.CLIPBOARD) is True
        await manager.revoke("app-1", Permission.CLIPBOARD)
        assert await manager.check("app-1", Permission.CLIPBOARD) is False

    @pytest.mark.asyncio
    async def test_revoke_all_removes_all_permissions(self, manager):
        await manager.request("app-1", [Permission.MEMORY_READ, Permission.CLIPBOARD])
        await manager.revoke_all("app-1")
        assert await manager.check("app-1", Permission.MEMORY_READ) is False
        assert await manager.check("app-1", Permission.CLIPBOARD) is False

    @pytest.mark.asyncio
    async def test_multiple_packages_independent(self, manager):
        await manager.request("app-1", [Permission.MEMORY_READ])
        await manager.request("app-2", [Permission.GPU_INFERENCE])
        assert await manager.check("app-1", Permission.MEMORY_READ) is True
        assert await manager.check("app-1", Permission.GPU_INFERENCE) is False
        assert await manager.check("app-2", Permission.GPU_INFERENCE) is True
        assert await manager.check("app-2", Permission.MEMORY_READ) is False

    @pytest.mark.asyncio
    async def test_get_grants_returns_active_permissions(self, manager):
        await manager.request("app-1", [Permission.MEMORY_READ, Permission.CLIPBOARD])
        grants = await manager.get_grants("app-1")
        assert Permission.MEMORY_READ in grants
        assert Permission.CLIPBOARD in grants

    @pytest.mark.asyncio
    async def test_remove_package_cleans_all(self, manager):
        await manager.request("app-1", [Permission.MEMORY_READ])
        await manager.remove_package("app-1")
        assert await manager.check("app-1", Permission.MEMORY_READ) is False

    @pytest.mark.asyncio
    async def test_all_permissions_denied_by_default(self, manager):
        for perm in Permission:
            assert await manager.check("new-app", perm) is False
