"""
Tests unitarios para modelos de Memory — Micro-fase 2.1
No requieren base de datos.
"""

import pytest
from pydantic import ValidationError
from src.memory.models import Memory


class TestMemoryModel:
    """Tests para el modelo Memory."""

    def test_valid_memory(self):
        mem = Memory(content="Python es mi lenguaje favorito", type="preference")
        assert mem.content == "Python es mi lenguaje favorito"
        assert mem.type == "preference"
        assert mem.tier == "WARM"
        assert mem.access_count == 0

    def test_all_valid_types(self):
        for t in ["conversation", "preference", "fact", "correction", "skill"]:
            mem = Memory(content="test", type=t)
            assert mem.type == t

    def test_invalid_type_rejected(self):
        with pytest.raises(ValidationError):
            Memory(content="test", type="invalid")

    def test_all_valid_tiers(self):
        for tier in ["HOT", "WARM", "COLD"]:
            mem = Memory(content="test", type="fact", tier=tier)
            assert mem.tier == tier

    def test_invalid_tier_rejected(self):
        with pytest.raises(ValidationError):
            Memory(content="test", type="fact", tier="INVALID")

    def test_default_tier_is_warm(self):
        mem = Memory(content="test", type="fact")
        assert mem.tier == "WARM"

    def test_default_metadata_is_empty_dict(self):
        mem = Memory(content="test", type="fact")
        assert mem.metadata == {}

    def test_default_source_is_user(self):
        mem = Memory(content="test", type="fact")
        assert mem.source == "user"

    def test_id_auto_generated(self):
        mem1 = Memory(content="test1", type="fact")
        mem2 = Memory(content="test2", type="fact")
        assert mem1.id != mem2.id

    def test_no_delete_method(self):
        """Verificar que Memory NO tiene un método delete."""
        mem = Memory(content="test", type="fact")
        assert not hasattr(mem, "delete")
