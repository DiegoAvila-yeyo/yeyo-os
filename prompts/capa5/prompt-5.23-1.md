## ═══════════════════════════════════════
## MICRO-FASE 5.23 — Cache de Resultados de Nodos
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 5.23-1 [VSCODE] — NodoCache: evitar re-ejecución con cache en Flash Memory

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 5.23 de Capa 5 (Órganos): crear NodoCache que evita re-ejecutar nodos cuando ya existe un resultado reciente con el mismo input en Flash Memory.

CONTEXTO:
- Micro-fase 5.22 completada: GrafoCheckpoint funcionando con tests
- NodoCache envuelve a cualquier Nodo existente (wrapper/decorator pattern)
- Antes de ejecutar: genera un hash del estado.entrada y busca en Flash Memory
- Si hay resultado < 24h con el mismo hash: usa el resultado cacheado, marca nodo como "saltado"
- Si no hay caché: ejecuta el nodo normalmente y guarda resultado en Flash Memory
- Los resultados cacheados se guardan con tipo="resultado_nodo"
- El evento emitido cuando hay cache hit tiene estado="saltado"
- Hash de input: hashlib.sha256(json.dumps(entrada, sort_keys=True).encode()).hexdigest()[:16]

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/orquestador/cache.py:

   Ruta: ~/yeyo-os/src/orquestador/cache.py
   Contenido:

   """
   YeyoOS — NodoCache
   Micro-fase 5.23 — Capa 5: Órganos

   Wrapper que añade cache a cualquier Nodo.
   Antes de ejecutar, busca en Flash Memory si ya existe un resultado reciente.
   Cache hit → usa resultado guardado (nodo "saltado")
   Cache miss → ejecuta normalmente y guarda resultado
   """

   import hashlib
   import json
   from datetime import datetime, timezone, timedelta
   from typing import Optional, Any

   from .estado import EstadoGrafo
   from .nodo import Nodo, NodoError


   TIPO_CACHE = "resultado_nodo"
   TTL_CACHE_HORAS = 24


   class CacheError(Exception):
       """Error en el sistema de cache."""
       pass


   class NodoCache(Nodo):
       """
       Wrapper que añade cache a cualquier Nodo del catálogo.

       Uso:
           nodo_original = catalogo.obtener("nodo_chat")
           nodo_con_cache = NodoCache(
               nodo=nodo_original,
               flash_memory=flash,
               ttl_horas=24,
           )

       Si hay cache hit, el estado tiene contexto["cache_hit"] = True
       Si hay cache miss, el nodo se ejecuta y el resultado se guarda.
       """

       def __init__(
           self,
           nodo: Nodo,
           flash_memory: Any,
           ttl_horas: float = TTL_CACHE_HORAS,
           campos_entrada: Optional[list[str]] = None,
       ):
           """
           Args:
               nodo: el nodo original a envolver con cache
               flash_memory: instancia de FlashMemory
               ttl_horas: tiempo de vida del cache en horas (default: 24h)
               campos_entrada: lista de campos de estado.entrada para el hash
                               (None = usar estado.entrada completo)
           """
           super().__init__(
               id=nodo.id,
               timeout=nodo.timeout,
               max_intentos=nodo.max_intentos,
           )
           self._nodo_original = nodo
           self._flash = flash_memory
           self.ttl_horas = ttl_horas
           self.campos_entrada = campos_entrada

           # Métricas de cache
           self.cache_hits = 0
           self.cache_misses = 0

       async def ejecutar(self, estado: EstadoGrafo) -> EstadoGrafo:
           """
           Ejecuta el nodo con cache:
           1. Genera hash del input
           2. Busca en Flash Memory
           3. Cache hit → retorna resultado cacheado, marca como saltado
           4. Cache miss → ejecuta nodo y guarda resultado
           """
           hash_entrada = self._hash_entrada(estado.entrada)

           # Buscar en cache
           resultado_cacheado = await self._buscar_cache(hash_entrada)

           if resultado_cacheado is not None:
               self.cache_hits += 1
               return self._aplicar_cache(estado, resultado_cacheado, hash_entrada)

           # Cache miss: ejecutar nodo original
           self.cache_misses += 1
           estado = await self._nodo_original.ejecutar(estado)

           # Guardar resultado en cache
           await self._guardar_cache(hash_entrada, estado)

           estado.contexto["cache_hit"] = False
           estado.contexto["cache_hash"] = hash_entrada
           return estado

       def _hash_entrada(self, entrada: dict) -> str:
           """Genera hash SHA256 del estado.entrada para identificar el cache."""
           if self.campos_entrada:
               entrada_filtrada = {k: entrada.get(k) for k in self.campos_entrada if k in entrada}
           else:
               entrada_filtrada = entrada

           try:
               entrada_json = json.dumps(entrada_filtrada, sort_keys=True, ensure_ascii=False)
           except (TypeError, ValueError):
               # Si el input no es serializable, no cachear
               entrada_json = str(entrada_filtrada)

           return hashlib.sha256(entrada_json.encode()).hexdigest()[:16]

       async def _buscar_cache(self, hash_entrada: str) -> Optional[dict]:
           """Busca resultado cacheado en Flash Memory. Retorna None si no existe o expiró."""
           try:
               resultados = await self._flash.buscar(
                   query=f"nodo_id:{self.id} hash:{hash_entrada}",
                   tipo=TIPO_CACHE,
                   limite=5,
               )
           except Exception:
               return None

           if not resultados:
               return None

           ahora = datetime.now(timezone.utc)
           ttl = timedelta(hours=self.ttl_horas)

           for resultado in resultados:
               try:
                   contenido = resultado.get("contenido", "")
                   if isinstance(contenido, str):
                       data = json.loads(contenido)
                   elif isinstance(contenido, dict):
                       data = contenido
                   else:
                       continue

                   if data.get("nodo_id") != self.id:
                       continue
                   if data.get("hash_entrada") != hash_entrada:
                       continue

                   # Verificar TTL
                   guardado_en = data.get("guardado_en")
                   if guardado_en:
                       t_guardado = datetime.fromisoformat(guardado_en)
                       if ahora - t_guardado > ttl:
                           continue  # Expirado

                   return data.get("salida")
               except (json.JSONDecodeError, ValueError, Exception):
                   continue

           return None

       async def _guardar_cache(self, hash_entrada: str, estado: EstadoGrafo) -> None:
           """Guarda el resultado del nodo en Flash Memory."""
           cache_data = {
               "nodo_id": self.id,
               "hash_entrada": hash_entrada,
               "salida": estado.salida,
               "guardado_en": datetime.now(timezone.utc).isoformat(),
               "tipo": TIPO_CACHE,
           }

           try:
               await self._flash.guardar(
                   dato=json.dumps(cache_data, ensure_ascii=False),
                   metadata={
                       "tipo": TIPO_CACHE,
                       "nodo_id": self.id,
                       "hash": hash_entrada,
                   }
               )
           except Exception:
               pass  # Fallos de cache no interrumpen la ejecución

       def _aplicar_cache(
           self,
           estado: EstadoGrafo,
           salida_cacheada: dict,
           hash_entrada: str
       ) -> EstadoGrafo:
           """Aplica el resultado cacheado al estado."""
           estado.salida.update(salida_cacheada)
           estado.contexto["cache_hit"] = True
           estado.contexto["cache_hash"] = hash_entrada
           estado.contexto["cache_nodo_id"] = self.id
           return estado

       @property
       def tasa_hit(self) -> float:
           """Retorna la tasa de cache hit (0.0-1.0)."""
           total = self.cache_hits + self.cache_misses
           return self.cache_hits / total if total > 0 else 0.0

2. Actualizar src/orquestador/__init__.py:

   Ruta: ~/yeyo-os/src/orquestador/__init__.py
   Contenido:
   """
   YeyoOS — YeyoOrquestador
   Motor de orquestación nativo de YeyoOS.
   Micro-fases 4.14-4.23 + 5.22-5.25 — Capas 4-5
   """
   from .estado import EstadoGrafo, EstadoGrafoError
   from .nodo import Nodo, NodoFuncion, NodoInline, NodoError, NodoTimeoutError, nodo
   from .edge import Edge, EdgeDirecto, EdgeCondicional, EdgeError, FIN_GRAFO, edge
   from .grafo import YeyoGrafo, ResultadoGrafo, GrafoError, GrafoTimeoutError
   from .paralelo import NodoParalelo
   from .orquestador import YeyoOrquestador, RespuestaOrquestador, OrquestadorError
   from .catalogo import CatalogoNodos, CatalogoError
   from .eventos import GraphEventEmitter, crear_evento_grafo
   from .checkpoint import GrafoCheckpoint, CheckpointError
   from .cache import NodoCache, CacheError

3. Crear archivo tests/unit/orquestador/test_cache.py:

   Ruta: ~/yeyo-os/tests/unit/orquestador/test_cache.py
   Contenido:

   """Tests para NodoCache — Micro-fase 5.23"""

   import json
   import pytest
   from datetime import datetime, timezone, timedelta
   from unittest.mock import AsyncMock, MagicMock
   from src.orquestador.estado import EstadoGrafo
   from src.orquestador.nodo import nodo, NodoInline
   from src.orquestador.cache import NodoCache, TIPO_CACHE


   # ─── Nodo de prueba ────────────────────────────────────────────────────────

   contador_ejecuciones = {"n": 0}


   @nodo(id="nodo_costoso")
   async def nodo_costoso(estado: EstadoGrafo) -> EstadoGrafo:
       contador_ejecuciones["n"] += 1
       estado.salida["resultado_costoso"] = f"resultado_{contador_ejecuciones['n']}"
       return estado


   def reset_contador():
       contador_ejecuciones["n"] = 0


   # ─── Mock de FlashMemory ───────────────────────────────────────────────────

   def mock_flash_memory_vacio():
       """Flash Memory sin resultados cacheados."""
       m = AsyncMock()
       m.guardar = AsyncMock(return_value="mem-cache-001")
       m.buscar = AsyncMock(return_value=[])
       return m


   def mock_flash_memory_con_cache(salida_cacheada: dict, hash_entrada: str, nodo_id: str):
       """Flash Memory con un resultado cacheado válido."""
       m = AsyncMock()
       cache_data = {
           "nodo_id": nodo_id,
           "hash_entrada": hash_entrada,
           "salida": salida_cacheada,
           "guardado_en": datetime.now(timezone.utc).isoformat(),
           "tipo": TIPO_CACHE,
       }
       m.guardar = AsyncMock(return_value="mem-cache-001")
       m.buscar = AsyncMock(return_value=[{
           "id": "mem-cache-001",
           "contenido": json.dumps(cache_data),
           "score": 0.99
       }])
       return m


   def mock_flash_memory_con_cache_expirado(salida_cacheada: dict, hash_entrada: str, nodo_id: str):
       """Flash Memory con un resultado cacheado EXPIRADO (más de 24h)."""
       m = AsyncMock()
       tiempo_expirado = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
       cache_data = {
           "nodo_id": nodo_id,
           "hash_entrada": hash_entrada,
           "salida": salida_cacheada,
           "guardado_en": tiempo_expirado,
           "tipo": TIPO_CACHE,
       }
       m.guardar = AsyncMock(return_value="mem-cache-001")
       m.buscar = AsyncMock(return_value=[{
           "id": "mem-cache-001",
           "contenido": json.dumps(cache_data),
           "score": 0.99
       }])
       return m


   class TestNodoCacheHash:

       def test_mismo_input_mismo_hash(self):
           flash = mock_flash_memory_vacio()
           nc = NodoCache(nodo_costoso, flash)
           entrada = {"texto": "hola", "usuario": "u1"}
           h1 = nc._hash_entrada(entrada)
           h2 = nc._hash_entrada(entrada)
           assert h1 == h2

       def test_diferente_input_diferente_hash(self):
           flash = mock_flash_memory_vacio()
           nc = NodoCache(nodo_costoso, flash)
           h1 = nc._hash_entrada({"texto": "hola"})
           h2 = nc._hash_entrada({"texto": "adios"})
           assert h1 != h2

       def test_orden_no_importa_mismo_hash(self):
           flash = mock_flash_memory_vacio()
           nc = NodoCache(nodo_costoso, flash)
           h1 = nc._hash_entrada({"b": 2, "a": 1})
           h2 = nc._hash_entrada({"a": 1, "b": 2})
           assert h1 == h2

       def test_hash_tiene_16_caracteres(self):
           flash = mock_flash_memory_vacio()
           nc = NodoCache(nodo_costoso, flash)
           h = nc._hash_entrada({"x": "y"})
           assert len(h) == 16

       def test_campos_entrada_filtra_campos(self):
           flash = mock_flash_memory_vacio()
           nc = NodoCache(nodo_costoso, flash, campos_entrada=["texto"])
           h1 = nc._hash_entrada({"texto": "hola", "timestamp": "2025-01-01"})
           h2 = nc._hash_entrada({"texto": "hola", "timestamp": "2025-12-31"})
           # Solo considera "texto", el timestamp no afecta el hash
           assert h1 == h2


   class TestNodoCacheMiss:

       @pytest.mark.asyncio
       async def test_cache_miss_ejecuta_nodo(self):
           reset_contador()
           flash = mock_flash_memory_vacio()
           nc = NodoCache(nodo_costoso, flash)
           estado = EstadoGrafo(entrada={"texto": "nuevo"})
           await nc.ejecutar(estado)
           assert contador_ejecuciones["n"] == 1
           assert nc.cache_misses == 1

       @pytest.mark.asyncio
       async def test_cache_miss_guarda_resultado(self):
           reset_contador()
           flash = mock_flash_memory_vacio()
           nc = NodoCache(nodo_costoso, flash)
           estado = EstadoGrafo(entrada={"texto": "guardar"})
           await nc.ejecutar(estado)
           flash.guardar.assert_called_once()

       @pytest.mark.asyncio
       async def test_cache_miss_marca_contexto(self):
           reset_contador()
           flash = mock_flash_memory_vacio()
           nc = NodoCache(nodo_costoso, flash)
           estado = EstadoGrafo(entrada={"texto": "miss"})
           resultado = await nc.ejecutar(estado)
           assert resultado.contexto.get("cache_hit") is False

       @pytest.mark.asyncio
       async def test_cache_miss_tiene_resultado_del_nodo(self):
           reset_contador()
           flash = mock_flash_memory_vacio()
           nc = NodoCache(nodo_costoso, flash)
           estado = EstadoGrafo(entrada={"texto": "ejecutar"})
           resultado = await nc.ejecutar(estado)
           assert "resultado_costoso" in resultado.salida


   class TestNodoCacheHit:

       @pytest.mark.asyncio
       async def test_cache_hit_no_ejecuta_nodo(self):
           reset_contador()
           estado = EstadoGrafo(entrada={"texto": "cacheado"})
           nc_temp = NodoCache(nodo_costoso, mock_flash_memory_vacio())
           hash_entrada = nc_temp._hash_entrada(estado.entrada)

           salida_cacheada = {"resultado_costoso": "resultado_del_cache"}
           flash = mock_flash_memory_con_cache(salida_cacheada, hash_entrada, "nodo_costoso")
           nc = NodoCache(nodo_costoso, flash)
           resultado = await nc.ejecutar(estado)

           assert contador_ejecuciones["n"] == 0  # no ejecutó
           assert nc.cache_hits == 1
           assert resultado.salida["resultado_costoso"] == "resultado_del_cache"

       @pytest.mark.asyncio
       async def test_cache_hit_marca_contexto(self):
           estado = EstadoGrafo(entrada={"texto": "hit"})
           nc_temp = NodoCache(nodo_costoso, mock_flash_memory_vacio())
           hash_entrada = nc_temp._hash_entrada(estado.entrada)

           flash = mock_flash_memory_con_cache({"r": "ok"}, hash_entrada, "nodo_costoso")
           nc = NodoCache(nodo_costoso, flash)
           resultado = await nc.ejecutar(estado)
           assert resultado.contexto.get("cache_hit") is True

       @pytest.mark.asyncio
       async def test_cache_hit_no_guarda_en_flash_memory(self):
           estado = EstadoGrafo(entrada={"texto": "hit_no_guardar"})
           nc_temp = NodoCache(nodo_costoso, mock_flash_memory_vacio())
           hash_entrada = nc_temp._hash_entrada(estado.entrada)

           flash = mock_flash_memory_con_cache({"r": "ok"}, hash_entrada, "nodo_costoso")
           nc = NodoCache(nodo_costoso, flash)
           await nc.ejecutar(estado)
           flash.guardar.assert_not_called()


   class TestNodoCacheTTL:

       @pytest.mark.asyncio
       async def test_cache_expirado_ejecuta_nodo(self):
           reset_contador()
           estado = EstadoGrafo(entrada={"texto": "expirado"})
           nc_temp = NodoCache(nodo_costoso, mock_flash_memory_vacio())
           hash_entrada = nc_temp._hash_entrada(estado.entrada)

           flash = mock_flash_memory_con_cache_expirado({"r": "viejo"}, hash_entrada, "nodo_costoso")
           nc = NodoCache(nodo_costoso, flash)
           resultado = await nc.ejecutar(estado)

           # Cache expirado → ejecuta el nodo
           assert contador_ejecuciones["n"] == 1
           assert nc.cache_misses == 1


   class TestNodoCacheMetricas:

       @pytest.mark.asyncio
       async def test_tasa_hit_correcta(self):
           nc_temp = NodoCache(nodo_costoso, mock_flash_memory_vacio())
           nc_temp.cache_hits = 3
           nc_temp.cache_misses = 1
           assert nc_temp.tasa_hit == 0.75

       def test_tasa_hit_cero_si_sin_usos(self):
           nc = NodoCache(nodo_costoso, mock_flash_memory_vacio())
           assert nc.tasa_hit == 0.0


   class TestNodoCacheRobustez:

       @pytest.mark.asyncio
       async def test_error_en_buscar_ejecuta_nodo(self):
           reset_contador()
           flash = AsyncMock()
           flash.buscar = AsyncMock(side_effect=ConnectionError("flash down"))
           flash.guardar = AsyncMock(return_value="mem-001")
           nc = NodoCache(nodo_costoso, flash)
           estado = EstadoGrafo(entrada={"texto": "error"})
           resultado = await nc.ejecutar(estado)
           # Sin cache → ejecuta el nodo normalmente
           assert contador_ejecuciones["n"] == 1

       @pytest.mark.asyncio
       async def test_error_en_guardar_no_interrumpe(self):
           reset_contador()
           flash = AsyncMock()
           flash.buscar = AsyncMock(return_value=[])
           flash.guardar = AsyncMock(side_effect=ConnectionError("flash down"))
           nc = NodoCache(nodo_costoso, flash)
           estado = EstadoGrafo(entrada={"texto": "guardar_error"})
           resultado = await nc.ejecutar(estado)
           # El resultado debe estar disponible aunque falle el cache
           assert "resultado_costoso" in resultado.salida

4. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/orquestador/test_cache.py -v

VERIFICAR:
- [ ] src/orquestador/cache.py existe con NodoCache
- [ ] Hash SHA256 del input tiene 16 caracteres y es determinístico
- [ ] Mismo input → mismo hash (sort_keys garantiza orden)
- [ ] Cache miss → ejecuta nodo y guarda en Flash Memory
- [ ] Cache hit → no ejecuta nodo, retorna resultado cacheado
- [ ] Cache hit → contexto["cache_hit"] = True, no llama a guardar()
- [ ] Cache expirado (> 24h) → ejecuta nodo normalmente
- [ ] Errores de Flash Memory no interrumpen la ejecución
- [ ] TODOS los tests pasan

SI FALLA:
- json.dumps con sort_keys: verificar que la entrada es un dict válido
- TTL calculation: usar timedelta para comparar timestamps con timezone
- Hash no determinístico: verificar que sort_keys=True está en json.dumps

NO HACER:
- No implementar caché en memoria (Redis/RAM) — solo Flash Memory
- No implementar invalidación manual del cache — solo TTL
- No crear GeneradorGrafos aún (eso es micro-fase 5.24)

GATE: Cache hit evita re-ejecución del nodo, cache miss ejecuta normalmente y guarda, cache expirado se trata como miss, errores de Flash Memory no interrumpen, todos los tests pasan.
```
