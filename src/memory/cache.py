"""
YeyoOS — MemoryCache (Capa Redis para HOT tier)
Micro-fase 2.2 — Capa 2: Cerebro

Caché de memorias HOT en Redis para acceso ultra-rápido (<1ms).
Si Redis no está disponible, el sistema degrada grácilmente a PostgreSQL.
"""

import json
import logging
from typing import Optional

import redis.asyncio as redis

from .models import Memory

logger = logging.getLogger("yeyoos.cache")

MEMORY_KEY_PREFIX = "yeyoos:memory:"
HOT_SET_KEY = "yeyoos:hot_memories"
DEFAULT_TTL = 3600  # 1 hora en segundos


class MemoryCache:
    """
    Caché Redis para memorias del tier HOT.
    Proporciona acceso <1ms a memorias frecuentemente accedidas.
    """

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis: Optional[redis.Redis] = None

    async def connect(self):
        """Establece conexión con Redis."""
        self.redis = redis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        logger.info("MemoryCache conectado a Redis")

    async def disconnect(self):
        """Cierra conexión con Redis."""
        if self.redis:
            await self.redis.aclose()
            logger.info("MemoryCache desconectado de Redis")

    async def get(self, memory_id: str) -> Optional[Memory]:
        """
        Obtiene una memoria del caché.
        Retorna None si no está en caché (cache miss).
        """
        if not self.redis:
            return None
        try:
            key = f"{MEMORY_KEY_PREFIX}{memory_id}"
            data = await self.redis.get(key)
            if data is None:
                logger.debug(f"Cache MISS: {memory_id}")
                return None
            logger.debug(f"Cache HIT: {memory_id}")
            return Memory(**json.loads(data))
        except Exception as e:
            logger.warning(f"Error leyendo caché: {e}")
            return None

    async def set(self, memory: Memory, ttl: int = DEFAULT_TTL):
        """
        Almacena una memoria en caché con TTL.
        Solo memorias HOT deben estar en caché.
        TTL default: 1 hora (3600 segundos).
        """
        if not self.redis:
            return
        try:
            key = f"{MEMORY_KEY_PREFIX}{memory.id}"
            data = memory.model_dump_json()
            await self.redis.set(key, data, ex=ttl)
            await self.redis.sadd(HOT_SET_KEY, memory.id)
            logger.debug(f"Cache SET: {memory.id} TTL={ttl}s")
        except Exception as e:
            logger.warning(f"Error escribiendo caché: {e}")

    async def invalidate(self, memory_id: str):
        """
        Invalida (elimina) una memoria del caché.
        Esto NO borra la memoria de PostgreSQL — solo del caché Redis.
        """
        if not self.redis:
            return
        try:
            key = f"{MEMORY_KEY_PREFIX}{memory_id}"
            await self.redis.delete(key)
            await self.redis.srem(HOT_SET_KEY, memory_id)
            logger.debug(f"Cache INVALIDATE: {memory_id}")
        except Exception as e:
            logger.warning(f"Error invalidando caché: {e}")

    async def get_hot_memories(self, limit: int = 20) -> list[str]:
        """
        Retorna los IDs de memorias HOT en caché.
        Para obtener las memorias completas, usar get() con cada ID.
        """
        if not self.redis:
            return []
        try:
            members = await self.redis.smembers(HOT_SET_KEY)
            return list(members)[:limit]
        except Exception as e:
            logger.warning(f"Error obteniendo memorias HOT: {e}")
            return []

    async def get_multiple(self, memory_ids: list[str]) -> list[Memory]:
        """
        Obtiene múltiples memorias del caché en una sola operación.
        Retorna solo las que están en caché (ignora misses).
        """
        if not self.redis or not memory_ids:
            return []
        try:
            keys = [f"{MEMORY_KEY_PREFIX}{mid}" for mid in memory_ids]
            pipeline = self.redis.pipeline()
            for key in keys:
                pipeline.get(key)
            results = await pipeline.execute()

            memories = []
            for data in results:
                if data is not None:
                    memories.append(Memory(**json.loads(data)))
            return memories
        except Exception as e:
            logger.warning(f"Error en get_multiple: {e}")
            return []

    async def warm_cache(self, memories: list[Memory]):
        """
        Pre-carga memorias HOT en caché.
        Usado por background tasks para mantener el caché caliente.
        """
        for memory in memories:
            if memory.tier == "HOT":
                await self.set(memory)
        logger.info(f"Cache warming: {len(memories)} memorias evaluadas")

    async def clear_all(self):
        """
        Limpia todo el caché de memorias.
        SOLO usar en mantenimiento. Esto NO borra memorias de PG.
        """
        if not self.redis:
            return
        try:
            hot_ids = await self.redis.smembers(HOT_SET_KEY)
            pipeline = self.redis.pipeline()
            for mid in hot_ids:
                pipeline.delete(f"{MEMORY_KEY_PREFIX}{mid}")
            pipeline.delete(HOT_SET_KEY)
            await pipeline.execute()
            logger.info("Cache limpiado completamente")
        except Exception as e:
            logger.warning(f"Error limpiando caché: {e}")

    async def get_stats(self) -> dict:
        """Estadísticas del caché."""
        if not self.redis:
            return {"connected": False}
        try:
            hot_count = await self.redis.scard(HOT_SET_KEY)
            info = await self.redis.info("memory")
            return {
                "connected": True,
                "hot_memories_count": hot_count,
                "used_memory_human": info.get("used_memory_human", "unknown"),
            }
        except Exception:
            return {"connected": False}

    async def health_check(self) -> bool:
        """Verifica que Redis está disponible."""
        if not self.redis:
            return False
        try:
            return await self.redis.ping()
        except Exception:
            return False
