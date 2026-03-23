"""Tests para Network Firewall Advanced — Micro-fase 6.8"""

import pytest
from src.security.firewall import (
    FirewallManager,
    FirewallConfig,
    FirewallRule,
    FirewallAction,
    Protocol,
    DEFAULT_RULES,
)


@pytest.fixture
def manager():
    return FirewallManager()


class TestFirewallRules:
    def test_default_rules_loaded(self, manager):
        rules = manager.get_rules()
        assert len(rules) > 0

    def test_add_rule(self, manager):
        initial = len(manager.get_rules())
        manager.add_rule(FirewallRule(id="test-rule", description="Test rule", direction="input", action=FirewallAction.DROP))
        assert len(manager.get_rules()) == initial + 1

    def test_remove_rule(self, manager):
        manager.add_rule(FirewallRule(id="to-remove", description="Will be removed", direction="input", action=FirewallAction.DROP))
        assert manager.remove_rule("to-remove") is True
        assert manager.remove_rule("nonexistent") is False


class TestContainerIsolation:
    def test_isolate_container(self, manager):
        manager.isolate_container("abc123", "anomaly detected")
        rules = manager.get_rules()
        isolate_rules = [r for r in rules if "isolate" in r.id]
        assert len(isolate_rules) == 1

    def test_unisolate_container(self, manager):
        manager.isolate_container("abc123")
        manager.unisolate_container("abc123")
        rules = manager.get_rules()
        isolate_rules = [r for r in rules if "isolate-abc123" in r.id]
        assert len(isolate_rules) == 0

    def test_container_whitelist(self, manager):
        manager.set_container_whitelist("node-1", ["10.0.0.1", "10.0.0.2"])
        rules = manager.get_rules()
        whitelist_rules = [r for r in rules if "node-1" in r.id]
        assert len(whitelist_rules) == 3


class TestDynamicBlocking:
    def test_block_ip(self, manager):
        manager.block_ip("192.168.1.100", "suspicious activity")
        assert "192.168.1.100" in manager.get_blocked_ips()

    def test_unblock_ip(self, manager):
        manager.block_ip("10.0.0.1")
        manager.unblock_ip("10.0.0.1")
        assert "10.0.0.1" not in manager.get_blocked_ips()

    def test_blocked_attempts_logged(self, manager):
        manager.log_blocked("1.2.3.4", 22, "tcp", "rule-1", "brute force")
        attempts = manager.get_blocked_attempts()
        assert len(attempts) == 1
        assert attempts[0].source_ip == "1.2.3.4"


class TestFirewallStatus:
    def test_status(self, manager):
        status = manager.get_status()
        assert status["total_rules"] > 0
        assert status["default_input"] == "drop"

    def test_rate_limit_rules_exist(self, manager):
        rules = manager.get_rules()
        rate_limited = [r for r in rules if r.rate_limit]
        assert len(rate_limited) > 0
