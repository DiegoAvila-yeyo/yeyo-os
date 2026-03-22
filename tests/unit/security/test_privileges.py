"""Tests para PrivilegeLevel y PrivilegeEnforcer — Micro-fase 4.5"""

import pytest
from src.security.privileges import (
    PrivilegeLevel,
    PrivilegeEnforcer,
    EscalationError,
    LEVEL_PERMISSIONS,
)


@pytest.fixture
def enforcer():
    return PrivilegeEnforcer()


class TestPrivilegeLevelDefinition:

    def test_l5_is_sandbox(self):
        assert PrivilegeLevel.SANDBOX == 5

    def test_l0_is_root(self):
        assert PrivilegeLevel.ROOT == 0

    def test_l5_has_minimal_permissions(self):
        perms = LEVEL_PERMISSIONS[5]
        assert "memory.read" in perms
        assert "memory.write" not in perms
        assert "gpu.inference" not in perms
        assert "network.internet" not in perms


class TestRegisterPackage:

    def test_register_user_level(self, enforcer):
        enforcer.register_package("my-pkg", PrivilegeLevel.USER)
        assert enforcer.get_level("my-pkg") == PrivilegeLevel.USER

    def test_ia_node_forced_to_l5(self, enforcer):
        enforcer.register_package("ai-node", PrivilegeLevel.ADMIN, ia_generated=True)
        assert enforcer.get_level("ai-node") == PrivilegeLevel.SANDBOX

    def test_root_level_rejected(self, enforcer):
        with pytest.raises(EscalationError):
            enforcer.register_package("evil-pkg", PrivilegeLevel.ROOT)

    def test_ia_node_always_l5_regardless_of_requested_level(self, enforcer):
        for level in [PrivilegeLevel.ADMIN, PrivilegeLevel.USER, PrivilegeLevel.LIMITED]:
            enforcer.register_package(f"ai-{level.name}", level, ia_generated=True)
            assert enforcer.get_level(f"ai-{level.name}") == PrivilegeLevel.SANDBOX


class TestEnforcePermissions:

    @pytest.mark.asyncio
    async def test_l5_can_read_memory(self, enforcer):
        enforcer.register_package("sandbox-pkg", PrivilegeLevel.SANDBOX)
        assert await enforcer.enforce("sandbox-pkg", "memory.read") is True

    @pytest.mark.asyncio
    async def test_l5_cannot_write_memory(self, enforcer):
        enforcer.register_package("sandbox-pkg", PrivilegeLevel.SANDBOX)
        assert await enforcer.enforce("sandbox-pkg", "memory.write") is False

    @pytest.mark.asyncio
    async def test_l5_cannot_access_network(self, enforcer):
        enforcer.register_package("sandbox-pkg", PrivilegeLevel.SANDBOX)
        assert await enforcer.enforce("sandbox-pkg", "network.internet") is False

    @pytest.mark.asyncio
    async def test_l2_can_use_gpu_inference(self, enforcer):
        enforcer.register_package("user-pkg", PrivilegeLevel.USER)
        assert await enforcer.enforce("user-pkg", "gpu.inference") is True

    @pytest.mark.asyncio
    async def test_unregistered_package_denied(self, enforcer):
        assert await enforcer.enforce("unknown-pkg", "memory.read") is False


class TestEscalation:

    @pytest.mark.asyncio
    async def test_l5_escalation_always_blocked(self, enforcer):
        enforcer.register_package("sandbox-pkg", PrivilegeLevel.SANDBOX)
        for target in [PrivilegeLevel.ADMIN, PrivilegeLevel.USER, PrivilegeLevel.LIMITED]:
            with pytest.raises(EscalationError):
                await enforcer.try_escalate("sandbox-pkg", target)

    @pytest.mark.asyncio
    async def test_ia_node_escalation_always_blocked(self, enforcer):
        enforcer.register_package("ai-node", PrivilegeLevel.ADMIN, ia_generated=True)
        with pytest.raises(EscalationError):
            await enforcer.try_escalate("ai-node", PrivilegeLevel.USER)

    @pytest.mark.asyncio
    async def test_escalation_to_root_always_blocked(self, enforcer):
        enforcer.register_package("user-pkg", PrivilegeLevel.USER)
        with pytest.raises(EscalationError):
            await enforcer.try_escalate("user-pkg", PrivilegeLevel.ROOT)
