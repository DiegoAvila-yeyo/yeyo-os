"""
YeyoOS — TierManager (Gestor de Tiers de Memoria)
Micro-fase 2.4 — Capa 2: Cerebro

Gestiona la promoción y degradación automática de memorias
entre tiers HOT/WARM/COLD basándose en patrones de acceso.

REGLA: Las memorias NUNCA se borran. Solo se mueven entre tiers.
"""

import logging
from datetime import datetime, timedelta, timezone

from .models import Memory
from .flash_memory import FlashMemory
from .cache import MemoryCache

logger = logging.getLogger("yeyoos.tier_manager")

# Umbrales de promoción/degradación
HOT_PROMOTION_MIN_ACCESS = 5        # accesos mínimos para WARM→HOT
HOT_PROMOTION_WINDOW_HOURS = 24     # ventana de tiempo para contar accesos
HOT_DEMOTION_INACTIVITY_HOURS = 2   # horas sin acceso para HOT→WARM
COLD_DEMOTION_INACTIVITY_DAYS = 7   # días sin acceso para WARM→COLD


class TierManager:
    """
    Evalúa y ajusta los tiers de las memorias automáticamente.
    Reglas:
    - WARM → HOT: access_count >= 5 en últimas 24h
    - HOT → WARM: sin acceso en 2 horas
    - WARM → COLD: sin acceso en 7 días
    - COLD → WARM: cualquier acceso reciente (<1h) promueve de vuelta
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
                    logger.info(f"Tier cambió: {memory.id} {memory.tier}→{new_tier}")
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
            if memory.accessed_at:
                accessed = memory.accessed_at
                if accessed.tzinfo is None:
                    accessed = accessed.replace(tzinfo=timezone.utc)
                if now - accessed > timedelta(hours=HOT_DEMOTION_INACTIVITY_HOURS):
                    return "WARM"
            return "HOT"

        elif memory.tier == "WARM":
            # WARM → HOT: suficientes accesos recientes
            if memory.access_count >= HOT_PROMOTION_MIN_ACCESS and memory.accessed_at:
                accessed = memory.accessed_at
                if accessed.tzinfo is None:
                    accessed = accessed.replace(tzinfo=timezone.utc)
                if now - accessed < timedelta(hours=HOT_PROMOTION_WINDOW_HOURS):
                    return "HOT"

            # WARM → COLD: inactividad larga
            if memory.accessed_at:
                accessed = memory.accessed_at
                if accessed.tzinfo is None:
                    accessed = accessed.replace(tzinfo=timezone.utc)
                if now - accessed > timedelta(days=COLD_DEMOTION_INACTIVITY_DAYS):
                    return "COLD"
            return "WARM"

        elif memory.tier == "COLD":
            # COLD → WARM: acceso reciente (<1h)
            if memory.accessed_at:
                accessed = memory.accessed_at
                if accessed.tzinfo is None:
                    accessed = accessed.replace(tzinfo=timezone.utc)
                if now - accessed < timedelta(hours=1):
                    return "WARM"
            return "COLD"

        return memory.tier

    @staticmethod
    def _is_promotion(current_tier: str, new_tier: str) -> bool:
        """Determina si un cambio de tier es una promoción."""
        tier_order = {"COLD": 0, "WARM": 1, "HOT": 2}
        return tier_order.get(new_tier, 0) > tier_order.get(current_tier, 0)
