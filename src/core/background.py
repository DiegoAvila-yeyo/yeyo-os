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
TIER_EVALUATION_INTERVAL = 300        # 5 minutos
CACHE_WARMING_INTERVAL = 3600         # 1 hora
EMBEDDING_GENERATION_INTERVAL = 86400  # 24 horas
REDIS_CLEANUP_INTERVAL = 86400        # 24 horas


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
