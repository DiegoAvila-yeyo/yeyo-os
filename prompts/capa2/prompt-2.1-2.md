## ═══════════════════════════════════════
## MICRO-FASE 2.1 — Flash Memory Tests
## Tipo: VSCODE | Prompts: 2 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 2.1-2 [VSCODE] — Tests de FlashMemory CRUD

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 2.1, Prompt 2 de 2: tests completos para FlashMemory CRUD.

CONTEXTO:
- Micro-fase 2.0 completada: Schema flash_memories creado con triggers
- Prompt 2.1-1 completado: FlashMemory implementado en src/memory/flash_memory.py
- PostgreSQL corriendo con pgvector habilitado
- Trigger anti-DELETE activo: DELETE lanza excepción
- Trigger auto-checksum activo: SHA-256 se genera automáticamente
- FlashMemory NO tiene método delete() — y NUNCA lo tendrá

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Instalar dependencias de test si no existen:
   cd ~/yeyo-os
   source .venv/bin/activate
   pip install pytest pytest-asyncio asyncpg

2. Crear archivo tests/unit/memory/__init__.py:

   Ruta: ~/yeyo-os/tests/unit/memory/__init__.py
   Contenido: (archivo vacío)

3. Crear archivo tests/unit/memory/test_memory_models.py:

   Ruta: ~/yeyo-os/tests/unit/memory/test_memory_models.py
   Contenido:

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

4. Crear archivo tests/integration/memory/test_flash_memory_crud.py:

   Ruta: ~/yeyo-os/tests/integration/memory/test_flash_memory_crud.py
   Contenido:

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
       "postgresql://yeyo:yeyo@localhost:5432/yeyoos"
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
       assert len(mem.checksum) == 64  # SHA-256
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
       # Primero degradar a COLD
       await flash_memory.demote_tier(mem.id)
       demoted = await flash_memory.demote_tier(mem.id)
       assert demoted.tier == "COLD"
       # Ahora promover a WARM
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
       await flash_memory.promote_tier(mem.id)  # WARM→HOT
       promoted = await flash_memory.promote_tier(mem.id)  # HOT→HOT
       assert promoted.tier == "HOT"


   @pytest.mark.asyncio
   async def test_demote_tier_hot_to_warm(flash_memory):
       """demote_tier() debe mover HOT→WARM."""
       mem = await flash_memory.store(content="Demote test", type="fact")
       await flash_memory.promote_tier(mem.id)  # WARM→HOT
       demoted = await flash_memory.demote_tier(mem.id)
       assert demoted.tier == "WARM"


   @pytest.mark.asyncio
   async def test_demote_tier_cold_stays_cold(flash_memory):
       """demote_tier() en COLD se mantiene en COLD."""
       mem = await flash_memory.store(content="COLD stays COLD", type="fact")
       await flash_memory.demote_tier(mem.id)  # WARM→COLD
       demoted = await flash_memory.demote_tier(mem.id)  # COLD→COLD
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

5. Ejecutar tests unitarios:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/memory/test_memory_models.py -v

6. Ejecutar tests de integración:
   python -m pytest tests/integration/memory/test_flash_memory_crud.py -v

VERIFICAR:
- [ ] Tests unitarios de Memory model: TODOS pasan
- [ ] Tests de integración FlashMemory CRUD: TODOS pasan
- [ ] store() crea memoria con checksum automático
- [ ] recall() retorna memorias ordenadas
- [ ] recall_by_type() filtra correctamente
- [ ] get_by_id() retorna memoria o None
- [ ] promote_tier() y demote_tier() funcionan correctamente
- [ ] get_stats() retorna estadísticas válidas
- [ ] NO existe método delete en FlashMemory ni en Memory
- [ ] access_count se incrementa en cada acceso

SI FALLA:
- Schema no creado: ejecutar migración 002_flash_memory.sql primero
- asyncpg error: verificar DATABASE_URL y que PostgreSQL está corriendo
- Import error: verificar __init__.py en src/memory/
- Trigger error: verificar que pgcrypto está habilitado

NO HACER:
- No agregar método delete() aunque los tests lo "necesiten"
- No desactivar triggers para "limpiar" datos de test
- No mockear la base de datos en tests de integración

GATE: Todos los tests unitarios y de integración pasan, FlashMemory no tiene delete(), access_count se incrementa, audit log registra operaciones.
```
