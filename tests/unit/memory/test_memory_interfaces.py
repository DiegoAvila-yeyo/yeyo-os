"""Tests para MemoriaProvider Interface — Micro-fase 1.2"""

import pytest
from datetime import datetime
from pydantic import ValidationError
from src.memory.interfaces import (
    MemoriaProvider,
    Memory,
    MemoryTier,
    MemoryType,
)


class TestMemoryTier:
    def test_hot_value(self):
        assert MemoryTier.HOT == "HOT"

    def test_warm_value(self):
        assert MemoryTier.WARM == "WARM"

    def test_cold_value(self):
        assert MemoryTier.COLD == "COLD"

    def test_only_three_tiers(self):
        assert len(MemoryTier) == 3


class TestMemoryType:
    def test_conversation(self):
        assert MemoryType.CONVERSATION == "conversation"

    def test_preference(self):
        assert MemoryType.PREFERENCE == "preference"

    def test_fact(self):
        assert MemoryType.FACT == "fact"

    def test_correction(self):
        assert MemoryType.CORRECTION == "correction"

    def test_skill(self):
        assert MemoryType.SKILL == "skill"

    def test_only_five_types(self):
        assert len(MemoryType) == 5


class TestMemory:
    @pytest.fixture
    def valid_memory(self):
        return Memory(
            id="mem-001",
            content="El usuario prefiere respuestas concisas",
            type=MemoryType.PREFERENCE,
            tier=MemoryTier.HOT,
            checksum="a" * 64,
            created_at=datetime.now(),
            accessed_at=datetime.now(),
            access_count=5,
            metadata={"source": "chat"},
        )

    def test_valid_memory_creates(self, valid_memory):
        assert valid_memory.id == "mem-001"
        assert valid_memory.type == MemoryType.PREFERENCE
        assert valid_memory.tier == MemoryTier.HOT

    def test_default_tier_is_warm(self):
        mem = Memory(
            id="mem-002", content="test", type=MemoryType.FACT,
            checksum="b" * 64, created_at=datetime.now(), accessed_at=datetime.now(),
        )
        assert mem.tier == MemoryTier.WARM

    def test_default_access_count_is_zero(self):
        mem = Memory(
            id="mem-003", content="test", type=MemoryType.FACT,
            checksum="c" * 64, created_at=datetime.now(), accessed_at=datetime.now(),
        )
        assert mem.access_count == 0

    def test_default_metadata_is_empty_dict(self):
        mem = Memory(
            id="mem-004", content="test", type=MemoryType.FACT,
            checksum="d" * 64, created_at=datetime.now(), accessed_at=datetime.now(),
        )
        assert mem.metadata == {}

    def test_embedding_optional(self):
        mem = Memory(
            id="mem-005", content="test", type=MemoryType.FACT,
            checksum="e" * 64, created_at=datetime.now(), accessed_at=datetime.now(),
        )
        assert mem.embedding is None

    def test_checksum_required(self):
        with pytest.raises(ValidationError):
            Memory(
                id="mem-006", content="test", type=MemoryType.FACT,
                created_at=datetime.now(), accessed_at=datetime.now(),
            )

    def test_checksum_must_be_64_chars(self):
        with pytest.raises(ValidationError):
            Memory(
                id="mem-007", content="test", type=MemoryType.FACT,
                checksum="short", created_at=datetime.now(), accessed_at=datetime.now(),
            )

    def test_empty_content_rejected(self):
        with pytest.raises(ValidationError):
            Memory(
                id="mem-008", content="", type=MemoryType.FACT,
                checksum="f" * 64, created_at=datetime.now(), accessed_at=datetime.now(),
            )

    def test_negative_access_count_rejected(self):
        with pytest.raises(ValidationError):
            Memory(
                id="mem-009", content="test", type=MemoryType.FACT,
                checksum="g" * 64, created_at=datetime.now(), accessed_at=datetime.now(),
                access_count=-1,
            )


class TestMemoriaProvider:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            MemoriaProvider()

    def test_all_methods_are_abstract(self):
        expected = {
            "store", "recall", "recall_by_type", "get_by_id",
            "search_semantic", "promote_tier", "demote_tier",
            "get_stats", "health_check",
        }
        assert MemoriaProvider.__abstractmethods__ == expected

    def test_has_nine_abstract_methods(self):
        assert len(MemoriaProvider.__abstractmethods__) == 9

    def test_no_delete_method_exists(self):
        """FUNDAMENTAL: La memoria NUNCA se elimina."""
        assert not hasattr(MemoriaProvider, "delete")
        assert not hasattr(MemoriaProvider, "remove")
        assert not hasattr(MemoriaProvider, "drop")
        assert not hasattr(MemoriaProvider, "purge")
