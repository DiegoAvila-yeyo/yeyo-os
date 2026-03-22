"""Tests para PackageDatabase — Micro-fase 4.8"""

import os
import pytest
import tempfile
from src.pkg.database import PackageDatabase


@pytest.fixture
async def db():
    with tempfile.TemporaryDirectory() as tmpdir:
        database = PackageDatabase(db_path=os.path.join(tmpdir, "test.db"))
        await database.connect()
        yield database
        await database.close()


SAMPLE_PACKAGE = {
    "name": "test-pkg",
    "version": "1.0.0",
    "author": "Test Author",
    "description": "Test package",
    "type": "node",
    "privilege_level": "L2",
}


class TestPackageDatabaseBasic:

    @pytest.mark.asyncio
    async def test_connect_creates_tables(self, db):
        packages = await db.list_all()
        assert packages == []

    @pytest.mark.asyncio
    async def test_register_package(self, db):
        await db.register(SAMPLE_PACKAGE)
        pkg = await db.get("test-pkg")
        assert pkg["name"] == "test-pkg"
        assert pkg["version"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_register_duplicate_raises(self, db):
        await db.register(SAMPLE_PACKAGE)
        with pytest.raises(ValueError, match="ya está registrado"):
            await db.register(SAMPLE_PACKAGE)

    @pytest.mark.asyncio
    async def test_get_nonexistent_raises(self, db):
        with pytest.raises(ValueError):
            await db.get("nonexistent")

    @pytest.mark.asyncio
    async def test_list_all_returns_all(self, db):
        pkg2 = {**SAMPLE_PACKAGE, "name": "pkg-2"}
        await db.register(SAMPLE_PACKAGE)
        await db.register(pkg2)
        all_pkgs = await db.list_all()
        assert len(all_pkgs) == 2

    @pytest.mark.asyncio
    async def test_unregister_package(self, db):
        await db.register(SAMPLE_PACKAGE)
        await db.unregister("test-pkg")
        packages = await db.list_all()
        assert len(packages) == 0

    @pytest.mark.asyncio
    async def test_unregister_nonexistent_raises(self, db):
        with pytest.raises(ValueError):
            await db.unregister("nonexistent")

    @pytest.mark.asyncio
    async def test_update_status(self, db):
        await db.register(SAMPLE_PACKAGE)
        await db.update_status("test-pkg", "updating")
        pkg = await db.get("test-pkg")
        assert pkg["status"] == "updating"


class TestPackageDatabasePermissions:

    @pytest.mark.asyncio
    async def test_grant_permission(self, db):
        await db.register(SAMPLE_PACKAGE)
        await db.grant_permission("test-pkg", "memory.read")
        assert await db.has_permission("test-pkg", "memory.read") is True

    @pytest.mark.asyncio
    async def test_revoke_permission(self, db):
        await db.register(SAMPLE_PACKAGE)
        await db.grant_permission("test-pkg", "memory.read")
        await db.revoke_permission("test-pkg", "memory.read")
        assert await db.has_permission("test-pkg", "memory.read") is False

    @pytest.mark.asyncio
    async def test_has_permission_false_by_default(self, db):
        await db.register(SAMPLE_PACKAGE)
        assert await db.has_permission("test-pkg", "memory.read") is False

    @pytest.mark.asyncio
    async def test_get_permissions_returns_only_granted(self, db):
        await db.register(SAMPLE_PACKAGE)
        await db.grant_permission("test-pkg", "memory.read")
        await db.grant_permission("test-pkg", "clipboard")
        perms = await db.get_permissions("test-pkg")
        assert len(perms) == 2
        perm_names = [p["permission"] for p in perms]
        assert "memory.read" in perm_names
        assert "clipboard" in perm_names
