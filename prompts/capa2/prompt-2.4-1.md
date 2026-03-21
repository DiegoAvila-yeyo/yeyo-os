## ═══════════════════════════════════════
## MICRO-FASE 2.4 — Memory Tier Manager
## Tipo: VSCODE | Prompts: 1 | Complejidad: Simple
## ═══════════════════════════════════════

### PROMPT 2.4-1 [VSCODE] — Implementar gestor automático de tiers de memoria

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 2.4 de Capa 2 (Cerebro): implementar el TierManager que promueve y degrada memorias automáticamente según patrones de acceso.

CONTEXTO:
- Micro-fases 2.0-2.2 completadas: Flash Memory + Redis Cache funcionando
- Tiers: HOT (Redis) / WARM (PG activo) / COLD (PG archivo)
- Reglas de promoción/degradación:
  - WARM → HOT: access_count >= 5 en últimas 24h
  - HOT → WARM: sin acceso en 2 horas
  - WARM → COLD: sin acceso en 7 días
  - COLD → WARM: cualquier acceso promueve de vuelta
- Las memorias NUNCA se borran — solo cambian de tier
- Hardware: GTX 1060 3GB VRAM, 16GB RAM, WSL2 Ubuntu

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/memory/tier_manager.py:

   Ruta: ~/yeyo-os/src/memory/tier_manager.py
   Contenido:

   """
   YeyoOS — TierManager (Gestor de Tiers de Memoria)
   Micro-fase 2.4 — Capa 2: Cerebro

   Gestiona la promoción y degradación automática de memorias
   entre tiers HOT/WARM/COLD basándose en patrones de acceso.

   REGLA: Las memorias NUNCA se borran. Solo se mueven entre tiers.
   """

   import logging
   from datetime import datetime, timedelta, timezone

   import asyncpg

   from .models import Memory
   from .flash_memory import FlashMemory
   from .cache import MemoryCache

   logger = logging.getLogger("yeyoos.tier_manager")

   # Umbrales de promoción/degradación
   HOT_PROMOTION_MIN_ACCESS = 5           # accesos mínimos para WARM→HOT
   HOT_PROMOTION_WINDOW_HOURS = 24        # ventana de tiempo para contar accesos
   HOT_DEMOTION_INACTIVITY_HOURS = 2      # horas sin acceso para HOT→WARM
   COLD_DEMOTION_INACTIVITY_DAYS = 7      # días sin acceso para WARM→COLD


   class TierManager:
       """
       Evalúa y ajusta los tiers de las memorias automáticamente.
       Reglas:
       - WARM → HOT: access_count >= 5 en últimas 24h
       - HOT → WARM: sin acceso en 2 horas
       - WARM → COLD: sin acceso en 7 días
       - COLD → WARM: cualquier acceso promueve de vuelta (manejado en FlashMemory)
       """

       def __init__(self, flash_memory: FlashMemory, cache: MemoryCache):
           self.memory = flash_memory
           self.cache = cache

       async def evaluate_all(self) -> dict:
           """
           Evalúa todas las memorias y ajusta tiers según reglas.
           Retorna estadísticas de cambios realizados.
           """
           stats = {"promoted": 0, "demoted": 0, "unchanged": 0, "errors": 0}

           async with self.memory.pool.acquire() as conn:
               rows = await conn.fetch(
                   """
                   SELECT id, content, type, tier, access_count, accessed_at,
                          checksum, metadata, source, created_at, updated_at
                   FROM flash_memories
                   ORDER BY accessed_at DESC
                   """
               )

           for row in rows:
               try:
                   memory = self.memory._row_to_memory(row)
                   new_tier = await self.evaluate_memory(memory)

                   if new_tier != memory.tier:
                       if self._is_promotion(memory.tier, new_tier):
                           await self.memory.promote_tier(memory.id)
                           if new_tier == "HOT":
                               updated = await self.memory.get_by_id(memory.id)
                               if updated:
                                   await self.cache.set(updated)
                           stats["promoted"] += 1
                       else:
                           await self.memory.demote_tier(memory.id)
                           if memory.tier == "HOT":
                               await self.cache.invalidate(memory.id)
                           stats["demoted"] += 1
                       logger.info(
                           f"Tier cambió: {memory.id} {memory.tier}→{new_tier}"
                       )
                   else:
                       stats["unchanged"] += 1
               except Exception as e:
                   logger.error(f"Error evaluando memoria {row['id']}: {e}")
                   stats["errors"] += 1

           logger.info(
               f"TierManager evaluación completada: "
               f"promoted={stats['promoted']}, demoted={stats['demoted']}, "
               f"unchanged={stats['unchanged']}, errors={stats['errors']}"
           )
           return stats

       async def evaluate_memory(self, memory: Memory) -> str:
           """
           Evalúa una memoria individual y retorna el tier recomendado.
           No modifica la memoria, solo retorna el tier que debería tener.
           """
           now = datetime.now(timezone.utc)

           if memory.tier == "HOT":
               # HOT → WARM: sin acceso en 2 horas
               if memory.accessed_at:
                   accessed = memory.accessed_at
                   if accessed.tzinfo is None:
                       accessed = accessed.replace(tzinfo=timezone.utc)
                   inactivity = now - accessed
                   if inactivity > timedelta(hours=HOT_DEMOTION_INACTIVITY_HOURS):
                       return "WARM"
               return "HOT"

           elif memory.tier == "WARM":
               # WARM → HOT: access_count >= 5 en últimas 24h
               if memory.access_count >= HOT_PROMOTION_MIN_ACCESS:
                   if memory.accessed_at:
                       accessed = memory.accessed_at
                       if accessed.tzinfo is None:
                           accessed = accessed.replace(tzinfo=timezone.utc)
                       recency = now - accessed
                       if recency < timedelta(hours=HOT_PROMOTION_WINDOW_HOURS):
                           return "HOT"

               # WARM → COLD: sin acceso en 7 días
               if memory.accessed_at:
                   accessed = memory.accessed_at
                   if accessed.tzinfo is None:
                       accessed = accessed.replace(tzinfo=timezone.utc)
                   inactivity = now - accessed
                   if inactivity > timedelta(days=COLD_DEMOTION_INACTIVITY_DAYS):
                       return "COLD"
               return "WARM"

           elif memory.tier == "COLD":
               # COLD → WARM: cualquier acceso reciente promueve de vuelta
               if memory.accessed_at:
                   accessed = memory.accessed_at
                   if accessed.tzinfo is None:
                       accessed = accessed.replace(tzinfo=timezone.utc)
                   recency = now - accessed
                   if recency < timedelta(hours=1):
                       return "WARM"
               return "COLD"

           return memory.tier

       @staticmethod
       def _is_promotion(current_tier: str, new_tier: str) -> bool:
           """Determina si un cambio de tier es una promoción."""
           tier_order = {"COLD": 0, "WARM": 1, "HOT": 2}
           return tier_order.get(new_tier, 0) > tier_order.get(current_tier, 0)

2. Actualizar src/memory/__init__.py:

   Ruta: ~/yeyo-os/src/memory/__init__.py
   Contenido:

   from .flash_memory import FlashMemory
   from .models import Memory
   from .cache import MemoryCache
   from .tier_manager import TierManager

3. Crear tests:

   Ruta: ~/yeyo-os/tests/unit/memory/test_tier_manager.py
   Contenido:

   """
   Tests para TierManager — Micro-fase 2.4
   Tests unitarios con mocks para no depender de PG/Redis.
   """

   import pytest
   from datetime import datetime, timedelta, timezone
   from unittest.mock import AsyncMock, MagicMock, patch
   from src.memory.tier_manager import (
       TierManager,
       HOT_PROMOTION_MIN_ACCESS,
       HOT_DEMOTION_INACTIVITY_HOURS,
       COLD_DEMOTION_INACTIVITY_DAYS,
   )
   from src.memory.models import Memory


   @pytest.fixture
   def mock_flash_memory():
       fm = AsyncMock()
       fm.pool = MagicMock()
       fm._row_to_memory = MagicMock()
       return fm


   @pytest.fixture
   def mock_cache():
       return AsyncMock()


   @pytest.fixture
   def tier_manager(mock_flash_memory, mock_cache):
       return TierManager(mock_flash_memory, mock_cache)


   class TestEvaluateMemory:
       """Tests de evaluación individual de memorias."""

       @pytest.mark.asyncio
       async def test_warm_to_hot_frequent_access(self, tier_manager):
           """WARM con 5+ accesos en 24h debe promover a HOT."""
           now = datetime.now(timezone.utc)
           memory = Memory(
               content="Frecuente",
               type="preference",
               tier="WARM",
               access_count=6,
               accessed_at=now - timedelta(hours=1),
               checksum="a" * 64,
           )
           result = await tier_manager.evaluate_memory(memory)
           assert result == "HOT"

       @pytest.mark.asyncio
       async def test_warm_stays_warm_low_access(self, tier_manager):
           """WARM con pocos accesos se mantiene WARM."""
           now = datetime.now(timezone.utc)
           memory = Memory(
               content="Poco acceso",
               type="fact",
               tier="WARM",
               access_count=2,
               accessed_at=now - timedelta(hours=1),
               checksum="b" * 64,
           )
           result = await tier_manager.evaluate_memory(memory)
           assert result == "WARM"

       @pytest.mark.asyncio
       async def test_hot_to_warm_inactivity(self, tier_manager):
           """HOT sin acceso en 2h debe degradar a WARM."""
           now = datetime.now(timezone.utc)
           memory = Memory(
               content="Inactivo",
               type="fact",
               tier="HOT",
               access_count=10,
               accessed_at=now - timedelta(hours=3),
               checksum="c" * 64,
           )
           result = await tier_manager.evaluate_memory(memory)
           assert result == "WARM"

       @pytest.mark.asyncio
       async def test_hot_stays_hot_recent_access(self, tier_manager):
           """HOT con acceso reciente se mantiene HOT."""
           now = datetime.now(timezone.utc)
           memory = Memory(
               content="Reciente",
               type="preference",
               tier="HOT",
               access_count=10,
               accessed_at=now - timedelta(minutes=30),
               checksum="d" * 64,
           )
           result = await tier_manager.evaluate_memory(memory)
           assert result == "HOT"

       @pytest.mark.asyncio
       async def test_warm_to_cold_inactivity(self, tier_manager):
           """WARM sin acceso en 7 días debe degradar a COLD."""
           now = datetime.now(timezone.utc)
           memory = Memory(
               content="Muy inactivo",
               type="conversation",
               tier="WARM",
               access_count=1,
               accessed_at=now - timedelta(days=10),
               checksum="e" * 64,
           )
           result = await tier_manager.evaluate_memory(memory)
           assert result == "COLD"

       @pytest.mark.asyncio
       async def test_cold_to_warm_recent_access(self, tier_manager):
           """COLD con acceso reciente (<1h) debe promover a WARM."""
           now = datetime.now(timezone.utc)
           memory = Memory(
               content="Revivido",
               type="fact",
               tier="COLD",
               access_count=1,
               accessed_at=now - timedelta(minutes=30),
               checksum="f" * 64,
           )
           result = await tier_manager.evaluate_memory(memory)
           assert result == "WARM"

       @pytest.mark.asyncio
       async def test_cold_stays_cold_no_access(self, tier_manager):
           """COLD sin acceso reciente se mantiene COLD."""
           now = datetime.now(timezone.utc)
           memory = Memory(
               content="Fría",
               type="fact",
               tier="COLD",
               access_count=0,
               accessed_at=now - timedelta(days=30),
               checksum="0" * 64,
           )
           result = await tier_manager.evaluate_memory(memory)
           assert result == "COLD"

       @pytest.mark.asyncio
       async def test_never_deletes(self, tier_manager):
           """Ninguna evaluación debe resultar en eliminación."""
           tiers = ["HOT", "WARM", "COLD"]
           now = datetime.now(timezone.utc)
           for tier in tiers:
               memory = Memory(
                   content="No delete test",
                   type="fact",
                   tier=tier,
                   access_count=0,
                   accessed_at=now - timedelta(days=365),
                   checksum="1" * 64,
               )
               result = await tier_manager.evaluate_memory(memory)
               assert result in tiers  # Siempre retorna un tier válido


   class TestTierManagerHelpers:
       """Tests para métodos auxiliares."""

       def test_is_promotion_cold_to_warm(self):
           assert TierManager._is_promotion("COLD", "WARM") is True

       def test_is_promotion_warm_to_hot(self):
           assert TierManager._is_promotion("WARM", "HOT") is True

       def test_is_not_promotion_hot_to_warm(self):
           assert TierManager._is_promotion("HOT", "WARM") is False

       def test_is_not_promotion_same_tier(self):
           assert TierManager._is_promotion("WARM", "WARM") is False

       def test_thresholds_configured(self):
           assert HOT_PROMOTION_MIN_ACCESS == 5
           assert HOT_DEMOTION_INACTIVITY_HOURS == 2
           assert COLD_DEMOTION_INACTIVITY_DAYS == 7

4. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/memory/test_tier_manager.py -v

VERIFICAR:
- [ ] Archivo src/memory/tier_manager.py existe
- [ ] WARM→HOT cuando access_count >= 5 en últimas 24h
- [ ] HOT→WARM cuando sin acceso en 2 horas
- [ ] WARM→COLD cuando sin acceso en 7 días
- [ ] COLD→WARM cuando hay acceso reciente
- [ ] NUNCA resulta en eliminación — siempre retorna un tier válido
- [ ] Umbrales configurables como constantes
- [ ] evaluate_all() procesa todas las memorias
- [ ] TODOS los tests pasan

SI FALLA:
- Import error: verificar src/memory/__init__.py incluye TierManager
- datetime timezone: asegurar que accessed_at tiene timezone info
- Mock errors: verificar que los mocks tienen las interfaces correctas

NO HACER:
- No borrar memorias que lleven mucho tiempo en COLD
- No agregar un tier "DELETED" o "ARCHIVED_DELETED"
- No ejecutar evaluate_all() en cada request (usar background task, micro-fase 2.17)
- No modificar los triggers de PostgreSQL

GATE: TierManager evalúa y cambia tiers correctamente, nunca elimina memorias, umbrales configurados, todos los tests pasan.
```
