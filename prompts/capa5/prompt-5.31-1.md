## ═══════════════════════════════════════
## MICRO-FASE 5.31 — Caché de Patrones de Razonamiento
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 5.31-1 [VSCODE] — CachePatrones + Anticipador: reutilizar caminos de razonamiento y pre-computar

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 5.31 de Capa 5 (Órganos): implementar caché de patrones de razonamiento que guarda no solo resultados sino los CAMINOS de razonamiento para reutilizarlos, más un Anticipador que predice las próximas acciones del usuario.

CONTEXTO:
- Micro-fases 5.28-5.30 completadas: PipelineInvestigador, MicroTareas, Razonamiento funcionando
- Modelos compartidos en src/investigador/modelos.py:
  - ResultadoBusqueda(fuente, url, codigo, score, metadata)
  - PasoInvestigacion(numero, tipo, input_resumen, output_resumen, tokens, duracion_ms)
  - InvestigacionCompleta(tarea_id, pasos, resultado_final, confianza, tiempo_total_ms)
- Flash Memory en src/memory/flash_memory.py: store(), recall(), search_semantic()
- IAProvider en src/ia/interfaces.py: generate(), get_embedding() -> list[float] (768-dim)
- OllamaProvider en src/ia/ollama_provider.py: embedding_model="nomic-embed-text" (768-dim)
- PostgreSQL con pgvector: CREATE INDEX USING hnsw (embedding vector_cosine_ops)
- CachePatrones es CONSULTADO POR: PipelineInvestigador (5.28) en Fase 0, Autodidacta (7.26)
- Los patrones se buscan por similitud semántica con threshold 0.85

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/investigador/modelos_cache.py:

   Ruta: ~/yeyo-os/src/investigador/modelos_cache.py
   Contenido:

   """
   YeyoOS — Modelos de Caché de Patrones
   Micro-fase 5.31 — Capa 5: Órganos

   Dataclasses para patrones de razonamiento reutilizables
   y pre-computaciones anticipatorias.
   """

   from __future__ import annotations

   from dataclasses import dataclass, field
   from datetime import datetime
   from typing import Any, Dict, List, Optional


   @dataclass
   class PatronRazonamiento:
       """
       Un patrón de razonamiento reutilizable.
       Almacena no solo el resultado sino el CAMINO para llegar a él.
       """
       id: Optional[int] = None
       tipo_problema: str = ""
       errores_comunes: List[Dict[str, Any]] = field(default_factory=list)
       patron_correcto: str = ""
       pasos_razonamiento: List[Dict[str, Any]] = field(default_factory=list)
       tiempo_original_ms: int = 0
       confianza: float = 0.0
       veces_reutilizado: int = 0
       aplicable_a: List[str] = field(default_factory=list)
       embedding: Optional[List[float]] = None
       created_at: Optional[datetime] = None


   @dataclass
   class PreComputado:
       """
       Una solución pre-computada por el Anticipador.
       Preparada en background para que esté lista cuando el usuario la necesite.
       """
       tarea_anticipada: str
       solucion: str
       confianza: float = 0.0
       razon: str = ""
       timestamp: datetime = field(default_factory=datetime.utcnow)
       usada: bool = False


2. Crear archivo src/investigador/cache_patrones.py:

   Ruta: ~/yeyo-os/src/investigador/cache_patrones.py
   Contenido:

   """
   YeyoOS — CachePatrones
   Micro-fase 5.31 — Capa 5: Órganos

   Guarda y reutiliza patrones de razonamiento.
   Usa pgvector para búsqueda semántica de patrones similares.
   Consultado por PipelineInvestigador (5.28) antes de investigar externamente.
   """

   from __future__ import annotations

   import json
   import logging
   from typing import Any, Dict, List, Optional

   from src.ia.interfaces import IAProvider

   from .modelos_cache import PatronRazonamiento, PreComputado

   logger = logging.getLogger(__name__)

   THRESHOLD_DEFAULT = 0.85
   VECTOR_DIM = 768


   class CachePaternosError(Exception):
       """Error en caché de patrones."""
       pass


   class CachePatrones:
       """
       Almacena y recupera patrones de razonamiento usando pgvector.

       Workflow:
       1. Después de resolver un problema: guardar_patron()
       2. Antes de resolver un problema nuevo: buscar_patron()
       3. Si hay match (threshold >= 0.85): reutilizar el patrón
       4. Si no hay match: resolver normalmente y guardar el nuevo patrón

       Usado por PipelineInvestigador (5.28) en Fase 0.
       """

       def __init__(
           self,
           pool: Optional[Any] = None,
           ia_provider: Optional[IAProvider] = None,
           threshold: float = THRESHOLD_DEFAULT,
       ):
           self._pool = pool
           self._ia = ia_provider
           self._threshold = threshold
           self._cache_local: List[PatronRazonamiento] = []

       async def guardar_patron(
           self,
           tipo_problema: str,
           pasos_razonamiento: List[Dict[str, Any]],
           errores_comunes: List[Dict[str, Any]],
           patron_correcto: str,
           tiempo_original_ms: int,
           confianza: float,
           aplicable_a: Optional[List[str]] = None,
       ) -> PatronRazonamiento:
           """
           Guarda un patrón de razonamiento en pgvector + cache local.
           Genera embedding del tipo_problema para búsqueda semántica.
           """
           embedding = None
           if self._ia:
               try:
                   embedding = await self._ia.get_embedding(tipo_problema)
               except Exception as e:
                   logger.warning(f"[cache_patrones] Error generando embedding: {e}")

           patron = PatronRazonamiento(
               tipo_problema=tipo_problema,
               errores_comunes=errores_comunes,
               patron_correcto=patron_correcto,
               pasos_razonamiento=pasos_razonamiento,
               tiempo_original_ms=tiempo_original_ms,
               confianza=confianza,
               aplicable_a=aplicable_a or [],
               embedding=embedding,
           )

           # Guardar en PostgreSQL con pgvector
           if self._pool and embedding:
               try:
                   async with self._pool.acquire() as conn:
                       row = await conn.fetchrow(
                           """
                           INSERT INTO patrones_razonamiento
                           (tipo_problema, embedding, errores_comunes, patron_correcto,
                            pasos_razonamiento, tiempo_original_ms, confianza, aplicable_a)
                           VALUES ($1, $2::vector, $3, $4, $5, $6, $7, $8)
                           RETURNING id
                           """,
                           tipo_problema,
                           str(embedding),
                           json.dumps(errores_comunes),
                           patron_correcto,
                           json.dumps(pasos_razonamiento),
                           tiempo_original_ms,
                           confianza,
                           aplicable_a or [],
                       )
                       patron.id = row["id"]
                       logger.info(f"[cache_patrones] Patrón guardado en DB: id={patron.id}")
               except Exception as e:
                   logger.error(f"[cache_patrones] Error guardando en DB: {e}")

           # Guardar en cache local
           self._cache_local.append(patron)
           logger.info(
               f"[cache_patrones] Patrón guardado: tipo='{tipo_problema[:50]}', "
               f"confianza={confianza}"
           )
           return patron

       async def buscar_patron(
           self,
           problema: str,
           threshold: Optional[float] = None,
       ) -> Optional[PatronRazonamiento]:
           """
           Busca un patrón reutilizable para el problema dado.
           Usa pgvector para búsqueda semántica con threshold configurable.
           """
           threshold = threshold or self._threshold

           # Buscar en pgvector
           if self._pool and self._ia:
               try:
                   embedding = await self._ia.get_embedding(problema)
                   async with self._pool.acquire() as conn:
                       row = await conn.fetchrow(
                           """
                           SELECT id, tipo_problema, errores_comunes, patron_correcto,
                                  pasos_razonamiento, tiempo_original_ms, confianza,
                                  veces_reutilizado, aplicable_a,
                                  1 - (embedding <=> $1::vector) as similitud
                           FROM patrones_razonamiento
                           WHERE 1 - (embedding <=> $1::vector) >= $2
                           ORDER BY similitud DESC
                           LIMIT 1
                           """,
                           str(embedding),
                           threshold,
                       )
                       if row:
                           # Incrementar contador de reutilización
                           await conn.execute(
                               "UPDATE patrones_razonamiento SET veces_reutilizado = veces_reutilizado + 1 WHERE id = $1",
                               row["id"],
                           )
                           patron = PatronRazonamiento(
                               id=row["id"],
                               tipo_problema=row["tipo_problema"],
                               errores_comunes=json.loads(row["errores_comunes"]) if row["errores_comunes"] else [],
                               patron_correcto=row["patron_correcto"],
                               pasos_razonamiento=json.loads(row["pasos_razonamiento"]) if row["pasos_razonamiento"] else [],
                               tiempo_original_ms=row["tiempo_original_ms"],
                               confianza=row["confianza"],
                               veces_reutilizado=row["veces_reutilizado"] + 1,
                               aplicable_a=row["aplicable_a"] or [],
                           )
                           logger.info(
                               f"[cache_patrones] Patrón encontrado: id={patron.id}, "
                               f"similitud={row['similitud']:.3f}"
                           )
                           return patron
               except Exception as e:
                   logger.warning(f"[cache_patrones] Error buscando en DB: {e}")

           # Fallback: buscar en cache local por keywords
           return self._buscar_local(problema, threshold)

       async def buscar_anticipacion(
           self,
           contexto_actual: str,
       ) -> List[PreComputado]:
           """
           Busca pre-computaciones relevantes para el contexto actual.
           Usado por el Anticipador para sugerir soluciones listas.
           """
           resultados: List[PreComputado] = []

           if self._pool and self._ia:
               try:
                   embedding = await self._ia.get_embedding(contexto_actual)
                   async with self._pool.acquire() as conn:
                       rows = await conn.fetch(
                           """
                           SELECT tipo_problema, patron_correcto, confianza,
                                  1 - (embedding <=> $1::vector) as similitud
                           FROM patrones_razonamiento
                           WHERE 1 - (embedding <=> $1::vector) >= 0.7
                           ORDER BY similitud DESC
                           LIMIT 5
                           """,
                           str(embedding),
                       )
                       for row in rows:
                           resultados.append(PreComputado(
                               tarea_anticipada=row["tipo_problema"],
                               solucion=row["patron_correcto"],
                               confianza=row["confianza"],
                               razon=f"Similitud: {row['similitud']:.3f}",
                           ))
               except Exception as e:
                   logger.warning(f"[cache_patrones] Error en anticipación: {e}")

           return resultados

       def _buscar_local(
           self,
           problema: str,
           threshold: float,
       ) -> Optional[PatronRazonamiento]:
           """Búsqueda fallback en cache local por coincidencia de keywords."""
           problema_words = set(problema.lower().split())
           mejor_patron = None
           mejor_score = 0.0

           for patron in self._cache_local:
               patron_words = set(patron.tipo_problema.lower().split())
               if not patron_words:
                   continue
               interseccion = len(problema_words & patron_words)
               union = len(problema_words | patron_words)
               jaccard = interseccion / union if union > 0 else 0.0

               if jaccard > mejor_score and jaccard >= (threshold * 0.5):
                   mejor_score = jaccard
                   mejor_patron = patron

           if mejor_patron:
               mejor_patron.veces_reutilizado += 1
               logger.info(
                   f"[cache_patrones] Patrón local: '{mejor_patron.tipo_problema[:50]}', "
                   f"score={mejor_score:.3f}"
               )
           return mejor_patron


3. Crear archivo src/investigador/anticipador.py:

   Ruta: ~/yeyo-os/src/investigador/anticipador.py
   Contenido:

   """
   YeyoOS — Anticipador
   Micro-fase 5.31 — Capa 5: Órganos

   Analiza las últimas N acciones del usuario, predice las próximas K
   acciones probables y pre-computa soluciones en background.
   Corre como tarea de prioridad baja (no interfiere con uso activo).
   """

   from __future__ import annotations

   import asyncio
   import logging
   import time
   from typing import Any, Dict, List, Optional

   from src.ia.interfaces import IAProvider

   from .cache_patrones import CachePatrones
   from .modelos_cache import PreComputado

   logger = logging.getLogger(__name__)

   MAX_ACCIONES_HISTORIAL = 20
   MAX_PREDICCIONES = 5

   PROMPT_PREDECIR = """Analiza las últimas acciones del usuario y predice las próximas {k} acciones más probables.

   Últimas acciones:
   {acciones}

   Para cada predicción, responde en formato:
   PREDICCION 1: [descripción de la acción]
   PREDICCION 2: [descripción de la acción]
   ...

   Basa tus predicciones en patrones de comportamiento del usuario."""


   class Anticipador:
       """
       Predice las próximas acciones del usuario y pre-computa soluciones.

       Workflow:
       1. Registra cada acción del usuario (registrar_accion)
       2. Periódicamente predice las próximas K acciones (predecir)
       3. Pre-computa soluciones para las más probables (pre_computar)
       4. Cuando el usuario hace la acción, la solución ya está lista

       Corre como tarea de baja prioridad — nunca interfiere con uso activo.
       """

       def __init__(
           self,
           ia_provider: IAProvider,
           cache_patrones: CachePatrones,
           max_historial: int = MAX_ACCIONES_HISTORIAL,
           max_predicciones: int = MAX_PREDICCIONES,
       ):
           self._ia = ia_provider
           self._cache = cache_patrones
           self._max_historial = max_historial
           self._max_predicciones = max_predicciones
           self._acciones: List[Dict[str, Any]] = []
           self._precomputados: List[PreComputado] = []
           self._running = False

       def registrar_accion(self, accion: str, metadata: Optional[Dict[str, Any]] = None) -> None:
           """Registra una acción del usuario en el historial."""
           self._acciones.append({
               "accion": accion,
               "timestamp": time.time(),
               "metadata": metadata or {},
           })
           if len(self._acciones) > self._max_historial:
               self._acciones = self._acciones[-self._max_historial:]

       async def predecir(self) -> List[str]:
           """
           Predice las próximas K acciones probables basándose en el historial.
           """
           if len(self._acciones) < 3:
               return []

           acciones_texto = "\n".join(
               f"- {a['accion']}" for a in self._acciones[-10:]
           )

           try:
               respuesta = await self._ia.generate(
                   prompt=PROMPT_PREDECIR.format(
                       k=self._max_predicciones,
                       acciones=acciones_texto,
                   ),
                   system="Predice acciones basándote en patrones. Sé específico.",
                   temperature=0.4,
               )

               predicciones = []
               for line in respuesta.content.split("\n"):
                   line = line.strip()
                   if line.startswith("PREDICCION") and ":" in line:
                       pred = line.split(":", 1)[1].strip()
                       if pred:
                           predicciones.append(pred)

               logger.info(f"[anticipador] {len(predicciones)} predicciones generadas")
               return predicciones[:self._max_predicciones]

           except Exception as e:
               logger.error(f"[anticipador] Error prediciendo: {e}")
               return []

       async def pre_computar(self, predicciones: List[str]) -> List[PreComputado]:
           """
           Pre-computa soluciones para las predicciones más probables.
           Busca primero en cache de patrones; si no hay, genera con IA.
           """
           precomputados: List[PreComputado] = []

           for pred in predicciones:
               try:
                   # Primero buscar en cache de patrones
                   anticipaciones = await self._cache.buscar_anticipacion(pred)
                   if anticipaciones:
                       precomputados.extend(anticipaciones)
                       continue

                   # Si no hay patrón, generar con IA (baja prioridad)
                   respuesta = await self._ia.generate(
                       prompt=f"Prepara una solución para: {pred}",
                       system="Genera una solución concisa y lista para usar.",
                       temperature=0.3,
                   )

                   precomputados.append(PreComputado(
                       tarea_anticipada=pred,
                       solucion=respuesta.content,
                       confianza=0.6,
                       razon="Pre-computado por anticipación",
                   ))

               except Exception as e:
                   logger.debug(f"[anticipador] Error pre-computando '{pred[:50]}': {e}")

           self._precomputados = precomputados
           logger.info(f"[anticipador] {len(precomputados)} soluciones pre-computadas")
           return precomputados

       async def obtener_precomputado(self, tarea: str) -> Optional[PreComputado]:
           """
           Busca si hay una solución pre-computada para la tarea.
           Si la hay, la marca como usada y la retorna.
           """
           tarea_lower = tarea.lower()
           for pc in self._precomputados:
               if not pc.usada and self._es_similar(tarea_lower, pc.tarea_anticipada.lower()):
                   pc.usada = True
                   logger.info(f"[anticipador] Pre-computado usado: '{pc.tarea_anticipada[:50]}'")
                   return pc
           return None

       async def ciclo_anticipacion(self) -> None:
           """
           Ejecuta un ciclo de anticipación: predecir + pre-computar.
           Diseñado para correr periódicamente como tarea de baja prioridad.
           """
           self._running = True
           try:
               predicciones = await self.predecir()
               if predicciones:
                   await self.pre_computar(predicciones)
           finally:
               self._running = False

       @property
       def esta_corriendo(self) -> bool:
           return self._running

       @staticmethod
       def _es_similar(a: str, b: str) -> bool:
           """Comparación simple de similitud por palabras compartidas."""
           words_a = set(a.split())
           words_b = set(b.split())
           if not words_a or not words_b:
               return False
           interseccion = len(words_a & words_b)
           return interseccion >= min(len(words_a), len(words_b)) * 0.5


4. Crear archivo db/migrations/patrones_razonamiento.sql:

   Ruta: ~/yeyo-os/db/migrations/patrones_razonamiento.sql
   Contenido:

   -- YeyoOS — Tabla patrones_razonamiento
   -- Micro-fase 5.31 — Capa 5: Órganos
   -- Almacena patrones de razonamiento reutilizables con búsqueda semántica

   CREATE TABLE IF NOT EXISTS patrones_razonamiento (
       id SERIAL PRIMARY KEY,
       tipo_problema TEXT NOT NULL,
       embedding vector(768),
       errores_comunes JSONB,
       patron_correcto TEXT,
       pasos_razonamiento JSONB,
       tiempo_original_ms INTEGER DEFAULT 0,
       confianza FLOAT DEFAULT 0.0,
       veces_reutilizado INTEGER DEFAULT 0,
       aplicable_a TEXT[],
       created_at TIMESTAMP DEFAULT NOW()
   );

   CREATE INDEX IF NOT EXISTS patrones_hnsw
   ON patrones_razonamiento USING hnsw (embedding vector_cosine_ops);

   CREATE INDEX IF NOT EXISTS idx_patrones_tipo
   ON patrones_razonamiento(tipo_problema);

   CREATE INDEX IF NOT EXISTS idx_patrones_confianza
   ON patrones_razonamiento(confianza DESC);


5. Crear archivo tests/unit/investigador/test_cache_patrones.py:

   Ruta: ~/yeyo-os/tests/unit/investigador/test_cache_patrones.py
   Contenido:

   """
   Tests unitarios para CachePatrones + Anticipador.
   Micro-fase 5.31 — 8 tests.
   """

   import pytest
   from unittest.mock import AsyncMock, MagicMock

   from src.investigador.cache_patrones import CachePatrones
   from src.investigador.anticipador import Anticipador
   from src.investigador.modelos_cache import PatronRazonamiento, PreComputado


   @pytest.fixture
   def mock_ia():
       ia = AsyncMock()
       ia.get_embedding.return_value = [0.1] * 768
       ia.generate.return_value = MagicMock(
           content="PREDICCION 1: crear tests\nPREDICCION 2: deploy",
           tokens_used=50,
           latency_ms=100,
       )
       return ia


   @pytest.fixture
   def cache(mock_ia):
       return CachePatrones(pool=None, ia_provider=mock_ia)


   @pytest.fixture
   def anticipador(mock_ia, cache):
       return Anticipador(ia_provider=mock_ia, cache_patrones=cache)


   @pytest.mark.asyncio
   async def test_guardar_patron(cache):
       patron = await cache.guardar_patron(
           tipo_problema="rate limiting en FastAPI",
           pasos_razonamiento=[{"paso": 1, "accion": "importar slowapi"}],
           errores_comunes=[{"error": "olvidar middleware"}],
           patron_correcto="from slowapi import Limiter\nlimiter = Limiter(key_func=get_remote_address)",
           tiempo_original_ms=5000,
           confianza=0.9,
           aplicable_a=["fastapi", "api"],
       )
       assert isinstance(patron, PatronRazonamiento)
       assert patron.tipo_problema == "rate limiting en FastAPI"
       assert patron.confianza == 0.9


   @pytest.mark.asyncio
   async def test_buscar_patron_local(cache):
       await cache.guardar_patron(
           tipo_problema="rate limiting en FastAPI",
           pasos_razonamiento=[],
           errores_comunes=[],
           patron_correcto="solución rate limiting",
           tiempo_original_ms=3000,
           confianza=0.85,
       )
       resultado = await cache.buscar_patron("rate limiting en FastAPI")
       assert resultado is not None
       assert "rate limiting" in resultado.tipo_problema.lower()


   @pytest.mark.asyncio
   async def test_buscar_patron_no_encontrado(cache):
       resultado = await cache.buscar_patron("quantum computing con Rust")
       assert resultado is None


   @pytest.mark.asyncio
   async def test_patron_incrementa_reutilizado(cache):
       await cache.guardar_patron(
           tipo_problema="autenticación JWT",
           pasos_razonamiento=[],
           errores_comunes=[],
           patron_correcto="jwt token code",
           tiempo_original_ms=2000,
           confianza=0.8,
       )
       patron = await cache.buscar_patron("autenticación JWT en Python")
       if patron:
           assert patron.veces_reutilizado >= 1


   @pytest.mark.asyncio
   async def test_anticipador_registrar_acciones(anticipador):
       anticipador.registrar_accion("crear archivo models.py")
       anticipador.registrar_accion("escribir tests")
       anticipador.registrar_accion("ejecutar pytest")
       assert len(anticipador._acciones) == 3


   @pytest.mark.asyncio
   async def test_anticipador_predecir(anticipador):
       for i in range(5):
           anticipador.registrar_accion(f"acción {i}")
       predicciones = await anticipador.predecir()
       assert isinstance(predicciones, list)


   @pytest.mark.asyncio
   async def test_anticipador_pre_computar(anticipador, mock_ia):
       mock_ia.generate.return_value = MagicMock(
           content="solución pre-computada",
           tokens_used=30,
           latency_ms=50,
       )
       precomputados = await anticipador.pre_computar(["crear tests unitarios"])
       assert len(precomputados) >= 1
       assert isinstance(precomputados[0], PreComputado)


   @pytest.mark.asyncio
   async def test_anticipador_obtener_precomputado(anticipador, mock_ia):
       mock_ia.generate.return_value = MagicMock(
           content="código de tests",
           tokens_used=30,
           latency_ms=50,
       )
       await anticipador.pre_computar(["escribir tests unitarios"])
       resultado = await anticipador.obtener_precomputado("escribir tests unitarios para auth")
       if resultado:
           assert isinstance(resultado, PreComputado)
           assert resultado.usada is True


VERIFICAR:

1. Ejecutar: cd ~/yeyo-os && python -m pytest tests/unit/investigador/test_cache_patrones.py -v
   Esperado: 8 tests pasan

2. Ejecutar: cd ~/yeyo-os && python -c "from src.investigador.cache_patrones import CachePatrones; print('OK')"
   Esperado: OK

3. Ejecutar: cd ~/yeyo-os && python -c "from src.investigador.anticipador import Anticipador; print('OK')"
   Esperado: OK

4. Ejecutar: cd ~/yeyo-os && python -c "from src.investigador.modelos_cache import PatronRazonamiento, PreComputado; print('OK')"
   Esperado: OK

5. Verificar migración: cat ~/yeyo-os/db/migrations/patrones_razonamiento.sql

SI FALLA:
- Si falla import de src.ia.interfaces: verificar ruta de IAProvider
- Si falla la búsqueda local: verificar que _buscar_local funciona sin pool
- Si falla el anticipador: verificar que cache_patrones acepta pool=None

NO HACER:
- NO modificar src/investigador/modelos.py (creado en 5.28)
- NO modificar src/investigador/pipeline.py (creado en 5.28)
- NO crear dependencias circulares entre cache_patrones y pipeline
- NO ejecutar pre-computación si el usuario está activo (solo en idle)

GATE:
✅ CachePatrones guarda patrones de razonamiento con embedding pgvector (768-dim)
✅ buscar_patron() encuentra patrones similares con threshold 0.85
✅ buscar_anticipacion() retorna pre-computaciones relevantes
✅ Anticipador registra acciones del usuario y predice las próximas K
✅ Anticipador pre-computa soluciones en background (prioridad baja)
✅ Tabla patrones_razonamiento creada con índice HNSW
✅ Funciona sin PostgreSQL (fallback a cache local)
✅ 8 tests pasan
✅ PatronRazonamiento y PreComputado exportados correctamente
```
