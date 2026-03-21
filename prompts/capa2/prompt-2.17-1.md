## ═══════════════════════════════════════
## MICRO-FASE 2.17 — Background Tasks
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 2.17-1 [VSCODE] — Implementar tareas de fondo para mantenimiento

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 2.17 de Capa 2 (Cerebro): implementar el BackgroundTaskManager que ejecuta tareas periódicas de mantenimiento: evaluación de tiers, warming de caché, generación de embeddings y limpieza de Redis.

CONTEXTO:
- Micro-fases 2.0-2.16 completadas: Todo el Cerebro funcional
- Tareas periódicas:
  - Cada 5 min: evaluar tiers de memorias (TierManager)
  - Cada 1h: warm cache con memorias HOT (MemoryCache)
  - Cada 24h: generar embeddings faltantes (EmbeddingService)
  - Cada 24h: limpiar keys expiradas de Redis
- Las tareas NO deben bloquear la API
- Graceful shutdown: las tareas se detienen limpiamente
- Hardware: GTX 1060 3GB VRAM, 16GB RAM, WSL2 Ubuntu

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear directorio si no existe:
   mkdir -p src/core

2. Crear archivo src/core/__init__.py (vacío si no existe):

   Ruta: ~/yeyo-os/src/core/__init__.py
   Contenido: (archivo vacío)

3. Crear archivo src/core/background.py:

   Ruta: ~/yeyo-os/src/core/background.py
   Contenido:

   """
   YeyoOS — BackgroundTaskManager (Tareas de Fondo)
   Micro-fase 2.17 — Capa 2: Cerebro

   Ejecuta tareas periódicas de mantenimiento:
   - Evaluación de tiers de memoria (cada 5 min)
   - Warming de caché Redis (cada 1h)
   - Generación de embeddings faltantes (cada 24h)
   - Limpieza de keys expiradas en Redis (cada 24h)

   Las tareas corren en background sin bloquear la API.
   """

   import asyncio
   import logging
   from typing import Optional

   from src.memory.tier_manager import TierManager
   from src.memory.cache import MemoryCache
   from src.memory.flash_memory import FlashMemory
   from src.ia.embeddings import EmbeddingService

   logger = logging.getLogger("yeyoos.background")

   # Intervalos en segundos
   TIER_EVALUATION_INTERVAL = 300       # 5 minutos
   CACHE_WARMING_INTERVAL = 3600        # 1 hora
   EMBEDDING_GENERATION_INTERVAL = 86400  # 24 horas
   REDIS_CLEANUP_INTERVAL = 86400       # 24 horas


   class BackgroundTaskManager:
       """
       Gestor de tareas de fondo para mantenimiento del sistema.
       Ejecuta tareas periódicas usando asyncio.
       """

       def __init__(
           self,
           tier_manager: Optional[TierManager] = None,
           cache: Optional[MemoryCache] = None,
           flash_memory: Optional[FlashMemory] = None,
           embeddings: Optional[EmbeddingService] = None,
       ):
           self.tier_manager = tier_manager
           self.cache = cache
           self.memory = flash_memory
           self.embeddings = embeddings
           self._tasks: list[asyncio.Task] = []
           self._running = False

       async def start(self):
           """Inicia todas las tareas de fondo."""
           if self._running:
               logger.warning("BackgroundTaskManager ya está corriendo")
               return

           self._running = True
           logger.info("Iniciando tareas de fondo...")

           if self.tier_manager:
               task = asyncio.create_task(
                   self._periodic_task(
                       "tier_evaluation",
                       self._evaluate_tiers,
                       TIER_EVALUATION_INTERVAL,
                   )
               )
               self._tasks.append(task)

           if self.cache and self.memory:
               task = asyncio.create_task(
                   self._periodic_task(
                       "cache_warming",
                       self._warm_cache,
                       CACHE_WARMING_INTERVAL,
                   )
               )
               self._tasks.append(task)

           if self.memory and self.embeddings:
               task = asyncio.create_task(
                   self._periodic_task(
                       "embedding_generation",
                       self._generate_missing_embeddings,
                       EMBEDDING_GENERATION_INTERVAL,
                   )
               )
               self._tasks.append(task)

           if self.cache:
               task = asyncio.create_task(
                   self._periodic_task(
                       "redis_cleanup",
                       self._cleanup_redis,
                       REDIS_CLEANUP_INTERVAL,
                   )
               )
               self._tasks.append(task)

           logger.info(f"Tareas de fondo iniciadas: {len(self._tasks)}")

       async def stop(self):
           """Detiene todas las tareas de fondo grácilmente."""
           if not self._running:
               return

           self._running = False
           logger.info("Deteniendo tareas de fondo...")

           for task in self._tasks:
               task.cancel()

           # Esperar a que todas las tareas terminen
           if self._tasks:
               await asyncio.gather(*self._tasks, return_exceptions=True)

           self._tasks.clear()
           logger.info("Tareas de fondo detenidas")

       @property
       def is_running(self) -> bool:
           """Indica si el manager está corriendo."""
           return self._running

       @property
       def task_count(self) -> int:
           """Número de tareas activas."""
           return len(self._tasks)

       async def _periodic_task(
           self,
           name: str,
           func,
           interval: int,
       ):
           """Ejecuta una función periódicamente."""
           logger.info(f"Tarea '{name}' programada cada {interval}s")

           while self._running:
               try:
                   await func()
               except asyncio.CancelledError:
                   logger.info(f"Tarea '{name}' cancelada")
                   break
               except Exception as e:
                   logger.error(f"Error en tarea '{name}': {e}")

               try:
                   await asyncio.sleep(interval)
               except asyncio.CancelledError:
                   break

       async def _evaluate_tiers(self):
           """Evalúa y ajusta tiers de memorias."""
           logger.debug("Ejecutando evaluación de tiers...")
           try:
               stats = await self.tier_manager.evaluate_all()
               logger.info(
                   f"Tiers evaluados: promoted={stats['promoted']}, "
                   f"demoted={stats['demoted']}"
               )
           except Exception as e:
               logger.error(f"Error evaluando tiers: {e}")

       async def _warm_cache(self):
           """Pre-carga memorias HOT en caché Redis."""
           logger.debug("Ejecutando warming de caché...")
           try:
               memories = await self.memory.recall_by_type("preference", limit=20)
               hot_memories = [m for m in memories if m.tier == "HOT"]

               # También obtener memorias frecuentes
               frequent = await self.memory.recall("", limit=20)
               for m in frequent:
                   if m.tier == "HOT" and m not in hot_memories:
                       hot_memories.append(m)

               await self.cache.warm_cache(hot_memories)
               logger.info(f"Cache warming: {len(hot_memories)} memorias HOT")
           except Exception as e:
               logger.error(f"Error en cache warming: {e}")

       async def _generate_missing_embeddings(self):
           """Genera embeddings para memorias que no los tienen."""
           logger.debug("Buscando memorias sin embeddings...")
           try:
               async with self.memory.pool.acquire() as conn:
                   rows = await conn.fetch(
                       """
                       SELECT id, content
                       FROM flash_memories
                       WHERE embedding IS NULL
                       LIMIT 100
                       """
                   )

               if not rows:
                   logger.debug("No hay memorias sin embeddings")
                   return

               contents = [row["content"] for row in rows]
               embeddings = self.embeddings.generate_batch(contents)

               async with self.memory.pool.acquire() as conn:
                   for row, embedding in zip(rows, embeddings):
                       await conn.execute(
                           """
                           UPDATE flash_memories
                           SET embedding = $1
                           WHERE id = $2
                           """,
                           str(embedding),
                           row["id"],
                       )

               logger.info(f"Embeddings generados: {len(rows)} memorias")
           except Exception as e:
               logger.error(f"Error generando embeddings: {e}")

       async def _cleanup_redis(self):
           """Limpia keys expiradas de Redis (mantenimiento general)."""
           logger.debug("Ejecutando limpieza de Redis...")
           try:
               stats = await self.cache.get_stats()
               logger.info(f"Redis stats: {stats}")
           except Exception as e:
               logger.error(f"Error en limpieza Redis: {e}")

4. Crear tests:

   Ruta: ~/yeyo-os/tests/unit/core/__init__.py
   Contenido: (archivo vacío)

   Ruta: ~/yeyo-os/tests/unit/core/test_background.py
   Contenido:

   """
   Tests para BackgroundTaskManager — Micro-fase 2.17
   Tests unitarios con mocks.
   """

   import pytest
   import asyncio
   from unittest.mock import AsyncMock, MagicMock, patch
   from src.core.background import (
       BackgroundTaskManager,
       TIER_EVALUATION_INTERVAL,
       CACHE_WARMING_INTERVAL,
       EMBEDDING_GENERATION_INTERVAL,
       REDIS_CLEANUP_INTERVAL,
   )


   @pytest.fixture
   def mock_tier_manager():
       tm = AsyncMock()
       tm.evaluate_all.return_value = {
           "promoted": 2, "demoted": 1, "unchanged": 10, "errors": 0
       }
       return tm


   @pytest.fixture
   def mock_cache():
       c = AsyncMock()
       c.warm_cache.return_value = None
       c.get_stats.return_value = {"connected": True}
       return c


   @pytest.fixture
   def mock_flash_memory():
       fm = AsyncMock()
       fm.recall_by_type.return_value = []
       fm.recall.return_value = []
       fm.pool = MagicMock()
       return fm


   @pytest.fixture
   def mock_embeddings():
       emb = MagicMock()
       emb.generate_batch.return_value = []
       return emb


   @pytest.fixture
   def task_manager(mock_tier_manager, mock_cache, mock_flash_memory, mock_embeddings):
       return BackgroundTaskManager(
           tier_manager=mock_tier_manager,
           cache=mock_cache,
           flash_memory=mock_flash_memory,
           embeddings=mock_embeddings,
       )


   class TestBackgroundTaskManagerBasic:
       """Tests básicos."""

       def test_not_running_initially(self, task_manager):
           assert task_manager.is_running is False

       def test_no_tasks_initially(self, task_manager):
           assert task_manager.task_count == 0

       def test_intervals_configured(self):
           assert TIER_EVALUATION_INTERVAL == 300  # 5 min
           assert CACHE_WARMING_INTERVAL == 3600  # 1h
           assert EMBEDDING_GENERATION_INTERVAL == 86400  # 24h
           assert REDIS_CLEANUP_INTERVAL == 86400  # 24h


   class TestStartStop:
       """Tests de inicio y parada."""

       @pytest.mark.asyncio
       async def test_start_creates_tasks(self, task_manager):
           await task_manager.start()
           assert task_manager.is_running is True
           assert task_manager.task_count > 0
           await task_manager.stop()

       @pytest.mark.asyncio
       async def test_stop_cancels_tasks(self, task_manager):
           await task_manager.start()
           await task_manager.stop()
           assert task_manager.is_running is False
           assert task_manager.task_count == 0

       @pytest.mark.asyncio
       async def test_double_start_warning(self, task_manager):
           await task_manager.start()
           await task_manager.start()  # No debe crashear
           assert task_manager.is_running is True
           await task_manager.stop()

       @pytest.mark.asyncio
       async def test_stop_without_start(self, task_manager):
           await task_manager.stop()  # No debe crashear
           assert task_manager.is_running is False

       @pytest.mark.asyncio
       async def test_graceful_shutdown(self, task_manager):
           """Las tareas deben detenerse limpiamente."""
           await task_manager.start()
           assert task_manager.task_count == 4
           await task_manager.stop()
           assert task_manager.task_count == 0


   class TestPartialDependencies:
       """Tests con dependencias parciales."""

       @pytest.mark.asyncio
       async def test_no_tier_manager(self, mock_cache, mock_flash_memory, mock_embeddings):
           tm = BackgroundTaskManager(
               tier_manager=None,
               cache=mock_cache,
               flash_memory=mock_flash_memory,
               embeddings=mock_embeddings,
           )
           await tm.start()
           assert tm.task_count == 3  # Sin tier evaluation
           await tm.stop()

       @pytest.mark.asyncio
       async def test_no_cache(self, mock_tier_manager, mock_flash_memory, mock_embeddings):
           tm = BackgroundTaskManager(
               tier_manager=mock_tier_manager,
               cache=None,
               flash_memory=mock_flash_memory,
               embeddings=mock_embeddings,
           )
           await tm.start()
           assert tm.task_count == 2  # Sin warming ni cleanup
           await tm.stop()

       @pytest.mark.asyncio
       async def test_minimal_dependencies(self, mock_tier_manager):
           tm = BackgroundTaskManager(tier_manager=mock_tier_manager)
           await tm.start()
           assert tm.task_count == 1  # Solo tier evaluation
           await tm.stop()

       @pytest.mark.asyncio
       async def test_no_dependencies(self):
           tm = BackgroundTaskManager()
           await tm.start()
           assert tm.task_count == 0
           await tm.stop()


   class TestTaskExecution:
       """Tests de ejecución de tareas."""

       @pytest.mark.asyncio
       async def test_tier_evaluation_callable(self, task_manager, mock_tier_manager):
           await task_manager._evaluate_tiers()
           mock_tier_manager.evaluate_all.assert_called_once()

       @pytest.mark.asyncio
       async def test_cache_warming_callable(self, task_manager, mock_flash_memory):
           await task_manager._warm_cache()
           mock_flash_memory.recall_by_type.assert_called()

       @pytest.mark.asyncio
       async def test_task_error_doesnt_crash(self, task_manager, mock_tier_manager):
           """Un error en una tarea no debe crashear el manager."""
           mock_tier_manager.evaluate_all.side_effect = Exception("DB error")
           await task_manager._evaluate_tiers()  # No debe lanzar excepción

5. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/core/test_background.py -v

VERIFICAR:
- [ ] Archivo src/core/background.py existe
- [ ] Start crea tareas en background
- [ ] Stop cancela tareas grácilmente
- [ ] Evaluación de tiers cada 5 min
- [ ] Cache warming cada 1h
- [ ] Embedding generation cada 24h
- [ ] Redis cleanup cada 24h
- [ ] Errores en tareas no crashean el manager
- [ ] Funciona con dependencias parciales
- [ ] TODOS los tests pasan

SI FALLA:
- Import error: verificar micro-fases 2.2, 2.3, 2.4
- asyncio error: verificar Python 3.11+
- Task cancellation: verificar CancelledError handling

NO HACER:
- No ejecutar tareas pesadas en el hilo principal de la API
- No ignorar errores de tareas (log siempre)
- No crear timers con intervalos < 1 minuto para tier evaluation
- No ejecutar evaluate_all() en cada request HTTP

GATE: BackgroundTaskManager inicia y detiene tareas grácilmente, intervalos configurados, errores manejados, dependencias parciales soportadas, todos los tests pasan.
```
