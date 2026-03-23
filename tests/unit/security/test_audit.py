"""Tests para Security Audit System — Micro-fase 6.10"""

import pytest
import json
from pathlib import Path
from src.security.audit import AuditTrail, AuditConfig, AuditEntry


@pytest.fixture
def tmp_config(tmp_path):
    return AuditConfig(log_file=str(tmp_path / "audit.jsonl"), max_entries_memory=100)


@pytest.fixture
def trail(tmp_config):
    return AuditTrail(config=tmp_config)


class TestAppendOnly:
    def test_append_creates_entry(self, trail):
        entry = trail.append(actor="admin", actor_type="user", action="login", description="Admin logged in", resource="/auth", result="success")
        assert entry.sequence == 1
        assert entry.actor == "admin"
        assert entry.action == "login"

    def test_no_update_method(self, trail):
        assert not hasattr(trail, 'update')

    def test_no_delete_method(self, trail):
        assert not hasattr(trail, 'delete')

    def test_no_remove_method(self, trail):
        assert not hasattr(trail, 'remove')

    def test_sequence_increments(self, trail):
        e1 = trail.append("a", "user", "login", "d", "/r", "success")
        e2 = trail.append("b", "user", "logout", "d", "/r", "success")
        assert e1.sequence == 1
        assert e2.sequence == 2

    def test_entry_persisted_to_file(self, trail, tmp_config):
        trail.append("admin", "user", "test", "d", "/r", "success")
        path = Path(tmp_config.log_file)
        assert path.exists()
        assert "admin" in path.read_text()


class TestHashChain:
    def test_first_entry_has_genesis_hash(self, trail):
        entry = trail.append("a", "user", "login", "d", "/r", "success")
        assert entry.previous_hash == AuditTrail.GENESIS_HASH

    def test_second_entry_links_to_first(self, trail):
        e1 = trail.append("a", "user", "login", "d", "/r", "success")
        e2 = trail.append("b", "user", "logout", "d", "/r", "success")
        assert e2.previous_hash == e1.entry_hash

    def test_chain_valid(self, trail):
        for i in range(10):
            trail.append(f"user_{i}", "user", "action", f"desc {i}", "/r", "success")
        is_valid, broken_at = trail.verify_chain()
        assert is_valid is True
        assert broken_at is None

    def test_tampered_entry_detected(self, trail):
        trail.append("a", "user", "login", "d", "/r", "success")
        trail.append("b", "user", "action", "d", "/r", "success")
        trail.append("c", "user", "logout", "d", "/r", "success")
        trail._entries[1].description = "TAMPERED"
        is_valid, broken_at = trail.verify_chain()
        assert is_valid is False
        assert broken_at == 2

    def test_entry_hash_is_sha256(self, trail):
        entry = trail.append("a", "user", "login", "d", "/r", "success")
        assert len(entry.entry_hash) == 64
        assert all(c in '0123456789abcdef' for c in entry.entry_hash)


class TestSearch:
    def test_search_by_actor(self, trail):
        trail.append("admin", "user", "login", "d", "/auth", "success")
        trail.append("guest", "user", "login", "d", "/auth", "failure")
        results = trail.search(actor="admin")
        assert len(results) == 1
        assert results[0].actor == "admin"

    def test_search_by_action(self, trail):
        trail.append("a", "user", "login", "d", "/r", "success")
        trail.append("a", "user", "logout", "d", "/r", "success")
        trail.append("a", "user", "login", "d", "/r", "success")
        results = trail.search(action="login")
        assert len(results) == 2

    def test_search_by_result(self, trail):
        trail.append("a", "user", "login", "d", "/r", "success")
        trail.append("b", "user", "login", "d", "/r", "failure")
        results = trail.search(result="failure")
        assert len(results) == 1

    def test_search_with_limit(self, trail):
        for i in range(20):
            trail.append("user", "user", "action", f"d{i}", "/r", "success")
        results = trail.search(limit=5)
        assert len(results) == 5


class TestExport:
    def test_export_json(self, trail):
        trail.append("admin", "user", "login", "Admin login", "/auth", "success")
        exported = trail.export_json()
        data = json.loads(exported)
        assert len(data) == 1
        assert data[0]["actor"] == "admin"

    def test_export_csv(self, trail):
        trail.append("admin", "user", "login", "Admin login", "/auth", "success")
        exported = trail.export_csv()
        assert "admin" in exported
        assert "login" in exported
        assert "sequence" in exported

    def test_export_empty(self, trail):
        assert trail.export_json() == "[]"
        assert trail.export_csv() == ""


class TestConsistency:
    def test_reload_preserves_chain(self, tmp_config):
        trail1 = AuditTrail(config=tmp_config)
        trail1.append("a", "user", "login", "d", "/r", "success")
        trail1.append("b", "user", "action", "d", "/r", "success")
        trail2 = AuditTrail(config=tmp_config)
        is_valid, _ = trail2.verify_chain()
        assert is_valid is True
        assert trail2.get_count() == 2

    def test_count_accurate(self, trail):
        assert trail.get_count() == 0
        trail.append("a", "user", "login", "d", "/r", "success")
        assert trail.get_count() == 1
