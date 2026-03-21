## ═══════════════════════════════════════
## MICRO-FASE 2.2 — Redis Cache Layer
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 2.2-1 [VSCODE] — Implementar capa de caché Redis para HOT tier

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 2.2 de Capa 2 (Cerebro): implementar la capa de caché Redis para memorias del tier HOT.

CONTEXTO:
- Capa 0 completada: Redis 7 corriendo en localhost:6379
- Capa 1 completada: Interfaces definidas
- Micro-fase 2.0 completada: Schema Flash Memory en PostgreSQL
- Micro-fase 2.1 completada: FlashMemory CRUD con asyncpg
- Tiers de memoria: HOT (Redis, <1ms) / WARM (PG activo, <10ms) / COLD (PG archivo, <50ms)
- Las memorias HOT viven en Redis con TTL de 1 hora
- Si Redis cae, el sistema sigue funcionando con PG (degradación grácil)
- Hardware: GTX 1060 3GB VRAM, 16GB RAM, WSL2 Ubuntu

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Instalar dependencia si no existe:
   cd ~/yeyo-os
   source .venv/bin/activate
   pip install redis

2. Crear archivo src/memory/cache.py:

   Ruta: ~/yeyo-os/src/memory/cache.py
   Contenido:

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

   # Prefijo para keys de memoria en Redis
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
               await self.redis.close()
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
               # Agregar al set de memorias HOT
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

3. Actualizar src/memory/__init__.py:

   Ruta: ~/yeyo-os/src/memory/__init__.py
   Contenido:

   from .flash_memory import FlashMemory
   from .models import Memory
   from .cache import MemoryCache

4. Crear tests:

   Ruta: ~/yeyo-os/tests/unit/memory/test_memory_cache.py
   Contenido:

   """
   Tests para MemoryCache — Micro-fase 2.2
   Tests unitarios con fakeredis y tests de integración con Redis real.
   """

   import pytest
   import json
   from unittest.mock import AsyncMock, patch, MagicMock
   from src.memory.cache import MemoryCache, MEMORY_KEY_PREFIX, HOT_SET_KEY, DEFAULT_TTL
   from src.memory.models import Memory


   class TestMemoryCacheUnit:
       """Tests unitarios sin Redis real."""

       def test_default_redis_url(self):
           cache = MemoryCache()
           assert cache.redis_url == "redis://localhost:6379"

       def test_custom_redis_url(self):
           cache = MemoryCache(redis_url="redis://custom:6380")
           assert cache.redis_url == "redis://custom:6380"

       def test_default_ttl_is_one_hour(self):
           assert DEFAULT_TTL == 3600

       def test_key_prefix(self):
           assert MEMORY_KEY_PREFIX == "yeyoos:memory:"

       @pytest.mark.asyncio
       async def test_get_returns_none_without_connection(self):
           cache = MemoryCache()
           result = await cache.get("some-id")
           assert result is None

       @pytest.mark.asyncio
       async def test_get_hot_memories_returns_empty_without_connection(self):
           cache = MemoryCache()
           result = await cache.get_hot_memories()
           assert result == []

       @pytest.mark.asyncio
       async def test_health_check_false_without_connection(self):
           cache = MemoryCache()
           result = await cache.health_check()
           assert result is False


   @pytest.mark.integration
   class TestMemoryCacheIntegration:
       """Tests de integración con Redis real."""

       @pytest.fixture
       async def cache(self):
           c = MemoryCache(redis_url="redis://localhost:6379")
           await c.connect()
           yield c
           await c.clear_all()
           await c.disconnect()

       @pytest.mark.asyncio
       async def test_health_check_true(self, cache):
           assert await cache.health_check() is True

       @pytest.mark.asyncio
       async def test_set_and_get_memory(self, cache):
           mem = Memory(
               id="test-cache-001",
               content="Memoria en caché",
               type="fact",
               tier="HOT",
               checksum="a" * 64,
           )
           await cache.set(mem)
           found = await cache.get("test-cache-001")
           assert found is not None
           assert found.content == "Memoria en caché"
           assert found.tier == "HOT"

       @pytest.mark.asyncio
       async def test_get_cache_miss(self, cache):
           result = await cache.get("nonexistent-id")
           assert result is None

       @pytest.mark.asyncio
       async def test_invalidate_removes_from_cache(self, cache):
           mem = Memory(
               id="test-cache-002",
               content="To be invalidated",
               type="fact",
               tier="HOT",
               checksum="b" * 64,
           )
           await cache.set(mem)
           assert await cache.get("test-cache-002") is not None
           await cache.invalidate("test-cache-002")
           assert await cache.get("test-cache-002") is None

       @pytest.mark.asyncio
       async def test_get_hot_memories_returns_ids(self, cache):
           mem = Memory(
               id="test-cache-003",
               content="HOT memory",
               type="preference",
               tier="HOT",
               checksum="c" * 64,
           )
           await cache.set(mem)
           hot_ids = await cache.get_hot_memories()
           assert "test-cache-003" in hot_ids

       @pytest.mark.asyncio
       async def test_get_multiple(self, cache):
           for i in range(3):
               mem = Memory(
                   id=f"test-multi-{i}",
                   content=f"Multi test {i}",
                   type="fact",
                   tier="HOT",
                   checksum=f"{i}" * 64,
               )
               await cache.set(mem)
           results = await cache.get_multiple(
               ["test-multi-0", "test-multi-1", "test-multi-2"]
           )
           assert len(results) == 3

       @pytest.mark.asyncio
       async def test_warm_cache_only_hot(self, cache):
           hot_mem = Memory(
               id="test-warm-hot",
               content="HOT",
               type="fact",
               tier="HOT",
               checksum="d" * 64,
           )
           warm_mem = Memory(
               id="test-warm-warm",
               content="WARM",
               type="fact",
               tier="WARM",
               checksum="e" * 64,
           )
           await cache.warm_cache([hot_mem, warm_mem])
           assert await cache.get("test-warm-hot") is not None
           assert await cache.get("test-warm-warm") is None

       @pytest.mark.asyncio
       async def test_get_stats(self, cache):
           stats = await cache.get_stats()
           assert stats["connected"] is True
           assert "hot_memories_count" in stats

       @pytest.mark.asyncio
       async def test_clear_all(self, cache):
           mem = Memory(
               id="test-clear",
               content="Clear test",
               type="fact",
               tier="HOT",
               checksum="f" * 64,
           )
           await cache.set(mem)
           await cache.clear_all()
           assert await cache.get("test-clear") is None

5. Ejecutar tests unitarios:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/memory/test_memory_cache.py -v -k "Unit"

6. Ejecutar tests de integración (requiere Redis corriendo):
   python -m pytest tests/unit/memory/test_memory_cache.py -v -k "Integration" -m integration

VERIFICAR:
- [ ] Archivo src/memory/cache.py existe
- [ ] MemoryCache se conecta a Redis
- [ ] Cache HIT retorna memoria en <1ms
- [ ] Cache MISS retorna None (no error)
- [ ] TTL de 1 hora funciona
- [ ] Invalidación elimina del caché (NO de PostgreSQL)
- [ ] get_hot_memories retorna IDs correctos
- [ ] warm_cache solo cachea memorias HOT
- [ ] Degradación grácil: sin Redis, retorna None/empty/False
- [ ] TODOS los tests pasan

SI FALLA:
- redis no instalado: `pip install redis`
- Redis no corriendo: `sudo systemctl start redis` o `redis-server`
- Conexión rechazada: verificar que Redis está en localhost:6379
- Import error: verificar src/memory/__init__.py

NO HACER:
- No usar Redis como almacenamiento primario (PG es el primario)
- No borrar memorias de PostgreSQL desde el caché
- No implementar lógica de tiers automática (eso es micro-fase 2.4)
- No cachear memorias WARM o COLD

GATE: MemoryCache funcional, cache hit/miss funcionan, TTL configurado, degradación grácil sin Redis, warm_cache solo cachea HOT, todos los tests pasan.
```
