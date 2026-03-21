"""
Tests de integración para FlashMemory CRUD — Micro-fase 2.1
Requieren PostgreSQL corriendo con schema de Flash Memory.
Ejecutar con: pytest tests/integration/memory/test_flash_memory_crud.py -v
"""

import pytest
import os
from src.memory.flash_memory import FlashMemory
from src.memory.models import Memory


pytestmark = pytest.mark.integration

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://yeyo:yeyo_dev_2026@127.0.0.1:5432/yeyo_db"
)


@pytest.fixture
async def flash_memory():
    fm = await FlashMemory.create(DATABASE_URL)
    yield fm
    await fm.close()


@pytest.mark.asyncio
async def test_store_creates_memory(flash_memory):
    """store() debe crear una memoria y retornar Memory con todos los campos."""
    mem = await flash_memory.store(
        content="Python es mi lenguaje favorito",
        type="preference",
        metadata={"language": "python"},
    )
    assert isinstance(mem, Memory)
    assert mem.content == "Python es mi lenguaje favorito"
    assert mem.type == "preference"
    assert mem.tier == "WARM"
    assert len(mem.checksum) == 64
    assert mem.id is not None
    assert mem.created_at is not None


@pytest.mark.asyncio
async def test_store_generates_checksum(flash_memory):
    """store() debe auto-generar checksum SHA-256 via trigger."""
    mem = await flash_memory.store(content="Test checksum", type="fact")
    assert len(mem.checksum) == 64
    assert mem.checksum != ""
    assert mem.checksum != "placeholder"


@pytest.mark.asyncio
async def test_store_different_types(flash_memory):
    """store() debe aceptar todos los tipos válidos."""
    for t in ["conversation", "preference", "fact", "correction", "skill"]:
        mem = await flash_memory.store(content=f"Test {t}", type=t)
        assert mem.type == t


@pytest.mark.asyncio
async def test_recall_returns_memories(flash_memory):
    """recall() debe retornar memorias ordenadas por acceso."""
    await flash_memory.store(content="Memoria recall test 1", type="fact")
    await flash_memory.store(content="Memoria recall test 2", type="fact")
    results = await flash_memory.recall("test", limit=5)
    assert isinstance(results, list)
    assert len(results) > 0
    assert all(isinstance(m, Memory) for m in results)


@pytest.mark.asyncio
async def test_recall_by_type_filters(flash_memory):
    """recall_by_type() debe filtrar por tipo."""
    await flash_memory.store(content="Preference test", type="preference")
    results = await flash_memory.recall_by_type("preference", limit=10)
    assert all(m.type == "preference" for m in results)


@pytest.mark.asyncio
async def test_get_by_id_returns_memory(flash_memory):
    """get_by_id() debe retornar la memoria correcta."""
    mem = await flash_memory.store(content="Get by ID test", type="fact")
    found = await flash_memory.get_by_id(mem.id)
    assert found is not None
    assert found.content == "Get by ID test"
    assert found.id == mem.id


@pytest.mark.asyncio
async def test_get_by_id_not_found(flash_memory):
    """get_by_id() con ID inexistente retorna None."""
    result = await flash_memory.get_by_id("00000000-0000-0000-0000-000000000000")
    assert result is None


@pytest.mark.asyncio
async def test_promote_tier_cold_to_warm(flash_memory):
    """promote_tier() debe mover COLD→WARM."""
    mem = await flash_memory.store(content="Promote test", type="fact")
    await flash_memory.demote_tier(mem.id)
    demoted = await flash_memory.demote_tier(mem.id)
    assert demoted.tier == "COLD"
    promoted = await flash_memory.promote_tier(mem.id)
    assert promoted.tier == "WARM"


@pytest.mark.asyncio
async def test_promote_tier_warm_to_hot(flash_memory):
    """promote_tier() debe mover WARM→HOT."""
    mem = await flash_memory.store(content="Promote HOT test", type="fact")
    assert mem.tier == "WARM"
    promoted = await flash_memory.promote_tier(mem.id)
    assert promoted.tier == "HOT"


@pytest.mark.asyncio
async def test_promote_tier_hot_stays_hot(flash_memory):
    """promote_tier() en HOT se mantiene en HOT."""
    mem = await flash_memory.store(content="HOT stays HOT", type="fact")
    await flash_memory.promote_tier(mem.id)
    promoted = await flash_memory.promote_tier(mem.id)
    assert promoted.tier == "HOT"


@pytest.mark.asyncio
async def test_demote_tier_hot_to_warm(flash_memory):
    """demote_tier() debe mover HOT→WARM."""
    mem = await flash_memory.store(content="Demote test", type="fact")
    await flash_memory.promote_tier(mem.id)
    demoted = await flash_memory.demote_tier(mem.id)
    assert demoted.tier == "WARM"


@pytest.mark.asyncio
async def test_demote_tier_cold_stays_cold(flash_memory):
    """demote_tier() en COLD se mantiene en COLD."""
    mem = await flash_memory.store(content="COLD stays COLD", type="fact")
    await flash_memory.demote_tier(mem.id)
    demoted = await flash_memory.demote_tier(mem.id)
    assert demoted.tier == "COLD"


@pytest.mark.asyncio
async def test_get_stats_returns_dict(flash_memory):
    """get_stats() debe retornar estadísticas válidas."""
    stats = await flash_memory.get_stats()
    assert isinstance(stats, dict)
    assert "total_memories" in stats
    assert "by_tier" in stats
    assert "by_type" in stats
    assert "total_associations" in stats
    assert isinstance(stats["total_memories"], int)


@pytest.mark.asyncio
async def test_health_check_returns_true(flash_memory):
    """health_check() debe retornar True cuando PG está activo."""
    result = await flash_memory.health_check()
    assert result is True


@pytest.mark.asyncio
async def test_no_delete_method_exists(flash_memory):
    """FlashMemory NO debe tener método delete."""
    assert not hasattr(flash_memory, "delete")
    assert not hasattr(flash_memory, "remove")
    assert not hasattr(flash_memory, "destroy")
    assert not hasattr(flash_memory, "erase")


@pytest.mark.asyncio
async def test_access_count_increments(flash_memory):
    """Cada acceso a una memoria debe incrementar access_count."""
    mem = await flash_memory.store(content="Access count test", type="fact")
    initial_count = mem.access_count
    found = await flash_memory.get_by_id(mem.id)
    assert found.access_count > initial_count
