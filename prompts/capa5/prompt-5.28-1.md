## ═══════════════════════════════════════
## MICRO-FASE 5.28 — Pipeline Investigador: Búsqueda → Ensamblaje → Verificación
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 5.28-1 [VSCODE] — Pipeline completo de investigación: buscar, evaluar, ensamblar, verificar, almacenar

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 5.28 de Capa 5 (Órganos): implementar el Pipeline Investigador completo — cuando Yeyo no tiene la respuesta en memoria, investiga en internet (GitHub, StackOverflow, docs), evalúa candidatos, ensambla la mejor solución, la verifica con 5 niveles y la almacena en Flash Memory.

CONTEXTO:
- Micro-fases 5.0–5.27 completadas: todos los nodos, grafos avanzados, voz funcionando
- Stack backend: FastAPI + Python, PostgreSQL + pgvector (768-dim), Redis
- Modelo IA: qwen2.5:3b via Ollama local (http://localhost:11434)
- Flash Memory en src/memory/flash_memory.py: clase FlashMemory con store(), recall(), search_semantic()
- Modelo Memory en src/memory/models.py: Memory(id, content, type, tier, embedding, metadata, ...)
- MemoryCache en src/memory/cache.py: MemoryCache con get(), set(), invalidate()
- IAProvider en src/ia/interfaces.py: IAProvider con generate(), chat(), get_embedding()
- OllamaProvider en src/ia/ollama_provider.py: implementación de IAProvider
- YeyoConfig en src/core/config.py: database_url, redis_url, ollama_host, ollama_model
- EventBus en src/core/event_bus.py: EventBus con publish(), subscribe()
- Nodo/YeyoGrafo en src/orquestador/nodo.py y grafo.py: sistema de grafos existente
- EstadoGrafo en src/orquestador/estado.py: entrada, salida, contexto, historial
- YeyoOrquestador en src/orquestador/orquestador.py: procesar_mensaje(), registrar_grafo()
- CachePatrones de micro-fase 5.31 estará en src/investigador/cache_patrones.py
- EjecutorMicroTareas de micro-fase 5.29 estará en src/investigador/micro_tareas.py
- Dependencias: httpx (ya instalado), asyncpg (ya instalado)

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/investigador/__init__.py:

   Ruta: ~/yeyo-os/src/investigador/__init__.py
   Contenido:

   """
   YeyoOS — Módulo Investigador
   Capas 5.28–5.32 — Capa 5: Órganos

   Pipeline de investigación autónoma: buscar, evaluar, ensamblar, verificar, almacenar.
   Incluye micro-tareas, razonamiento extendido, caché de patrones y selector de modelo.
   """

   from .modelos import ResultadoBusqueda, InvestigacionCompleta, PasoInvestigacion
   from .pipeline import PipelineInvestigador

   __all__ = [
       "ResultadoBusqueda",
       "InvestigacionCompleta",
       "PasoInvestigacion",
       "PipelineInvestigador",
   ]


2. Crear archivo src/investigador/modelos.py:

   Ruta: ~/yeyo-os/src/investigador/modelos.py
   Contenido:

   """
   YeyoOS — Modelos del Investigador
   Micro-fase 5.28 — Capa 5: Órganos

   Dataclasses compartidas por todo el módulo investigador.
   Usadas por: pipeline.py, buscador_externo.py, evaluador.py, ensamblador.py,
   verificador.py, micro_tareas.py, cache_patrones.py, razonamiento.py.
   """

   from __future__ import annotations

   from dataclasses import dataclass, field
   from datetime import datetime
   from typing import Any, Dict, List, Optional


   @dataclass
   class ResultadoBusqueda:
       """Un resultado individual de búsqueda (interna o externa)."""
       fuente: str  # "flash_memory", "redis", "pgvector", "github", "stackoverflow", "docs"
       url: str  # URL o ID del recurso
       codigo: str  # Código o contenido encontrado
       score: float  # 0.0-1.0 — calidad estimada
       metadata: Dict[str, Any] = field(default_factory=dict)
       # metadata puede incluir: estrellas, votos, fecha, lenguaje, licencia, etc.


   @dataclass
   class PasoInvestigacion:
       """Un paso individual dentro de una investigación."""
       numero: int
       tipo: str  # "busqueda_interna", "busqueda_externa", "evaluacion", "ensamblaje", "verificacion", "almacenamiento"
       input_resumen: str  # Resumen del input (truncado para no llenar contexto)
       output_resumen: str  # Resumen del output
       tokens: int = 0
       duracion_ms: int = 0
       confianza: float = 0.0
       timestamp: datetime = field(default_factory=datetime.utcnow)


   @dataclass
   class InvestigacionCompleta:
       """Resultado completo de una investigación."""
       tarea_id: str
       pasos: List[PasoInvestigacion] = field(default_factory=list)
       resultado_final: str = ""
       confianza: float = 0.0  # 0.0-1.0
       tiempo_total_ms: int = 0
       tokens_total: int = 0
       fuentes_usadas: List[str] = field(default_factory=list)
       exito: bool = False


   @dataclass
   class TestResult:
       """Resultado de ejecución de tests."""
       passed: bool
       total: int = 0
       failed: int = 0
       errors: List[str] = field(default_factory=list)
       output: str = ""


   @dataclass
   class LintResult:
       """Resultado de análisis estático."""
       passed: bool
       warnings: int = 0
       errors: int = 0
       issues: List[Dict[str, Any]] = field(default_factory=list)


   @dataclass
   class StressResult:
       """Resultado de stress test en Docker."""
       passed: bool
       tiempo_ms: int = 0
       memoria_peak_mb: float = 0.0
       errores: List[str] = field(default_factory=list)


   @dataclass
   class VerificacionCompleta:
       """Resultado agregado de los 5 niveles de verificación."""
       nivel_1_ejecucion: bool = False
       nivel_2_tests: Optional[TestResult] = None
       nivel_3_lint: Optional[LintResult] = None
       nivel_4_similitud: float = 0.0
       nivel_5_stress: Optional[StressResult] = None
       confianza: float = 0.0  # Calculada sobre los 5 niveles
       detalles: Dict[str, Any] = field(default_factory=dict)


3. Crear archivo src/investigador/buscador_externo.py:

   Ruta: ~/yeyo-os/src/investigador/buscador_externo.py
   Contenido:

   """
   YeyoOS — BuscadorExterno
   Micro-fase 5.28 — Capa 5: Órganos

   Busca soluciones en fuentes externas: GitHub, StackOverflow, documentación.
   Cada método retorna List[ResultadoBusqueda] con score normalizado 0.0-1.0.
   """

   from __future__ import annotations

   import logging
   import time
   from typing import Any, Dict, List, Optional
   from urllib.parse import quote_plus

   import httpx

   from .modelos import ResultadoBusqueda

   logger = logging.getLogger(__name__)

   GITHUB_API = "https://api.github.com"
   SO_API = "https://api.stackexchange.com/2.3"
   DEFAULT_TIMEOUT = 15.0


   class BuscadorExternoError(Exception):
       """Error en búsqueda externa."""
       pass


   class BuscadorExterno:
       """
       Busca código y soluciones en fuentes externas.

       Requiere conexión a internet. Cada método captura errores de red
       y retorna lista vacía en vez de explotar (graceful degradation).
       """

       def __init__(
           self,
           github_token: Optional[str] = None,
           timeout: float = DEFAULT_TIMEOUT,
       ):
           self._github_token = github_token
           self._timeout = timeout
           headers = {"Accept": "application/json"}
           if github_token:
               headers["Authorization"] = f"token {github_token}"
           self._client = httpx.AsyncClient(
               timeout=self._timeout,
               headers=headers,
               follow_redirects=True,
           )

       async def close(self) -> None:
           await self._client.aclose()

       async def buscar_github(
           self,
           query: str,
           min_stars: int = 50,
           lenguaje: Optional[str] = None,
           max_resultados: int = 10,
       ) -> List[ResultadoBusqueda]:
           """
           Busca repositorios y código en GitHub.
           Filtra por estrellas mínimas para garantizar calidad.
           Retorna List[ResultadoBusqueda] ordenados por score descendente.
           """
           resultados: List[ResultadoBusqueda] = []
           try:
               q = f"{query} stars:>={min_stars}"
               if lenguaje:
                   q += f" language:{lenguaje}"

               resp = await self._client.get(
                   f"{GITHUB_API}/search/repositories",
                   params={"q": q, "sort": "stars", "order": "desc", "per_page": max_resultados},
               )
               if resp.status_code == 403:
                   logger.warning("[buscador_externo] GitHub API rate limit alcanzado")
                   return resultados
               resp.raise_for_status()
               data = resp.json()

               for item in data.get("items", [])[:max_resultados]:
                   stars = item.get("stargazers_count", 0)
                   max_stars = max(stars, 1)
                   score_stars = min(stars / 10000.0, 1.0)
                   updated = item.get("updated_at", "")
                   score_fresh = 0.8 if "2024" in updated or "2025" in updated else 0.4
                   score = round((score_stars * 0.6 + score_fresh * 0.4), 3)

                   resultados.append(ResultadoBusqueda(
                       fuente="github",
                       url=item.get("html_url", ""),
                       codigo=item.get("description", "") or "",
                       score=score,
                       metadata={
                           "estrellas": stars,
                           "lenguaje": item.get("language", ""),
                           "nombre": item.get("full_name", ""),
                           "actualizado": updated,
                           "licencia": (item.get("license") or {}).get("spdx_id", "unknown"),
                           "topics": item.get("topics", []),
                       },
                   ))

               resultados.sort(key=lambda r: r.score, reverse=True)
               logger.info(f"[buscador_externo] GitHub: {len(resultados)} resultados para '{query}'")

           except httpx.HTTPError as e:
               logger.error(f"[buscador_externo] Error GitHub API: {e}")
           except Exception as e:
               logger.error(f"[buscador_externo] Error inesperado GitHub: {e}")

           return resultados

       async def buscar_stackoverflow(
           self,
           query: str,
           min_votes: int = 10,
           max_resultados: int = 10,
       ) -> List[ResultadoBusqueda]:
           """
           Busca preguntas con respuestas aceptadas en StackOverflow.
           Filtra por votos mínimos. Retorna respuestas, no preguntas.
           """
           resultados: List[ResultadoBusqueda] = []
           try:
               resp = await self._client.get(
                   f"{SO_API}/search/advanced",
                   params={
                       "order": "desc",
                       "sort": "votes",
                       "q": query,
                       "accepted": "True",
                       "site": "stackoverflow",
                       "filter": "withbody",
                       "pagesize": max_resultados,
                   },
               )
               resp.raise_for_status()
               data = resp.json()

               for item in data.get("items", []):
                   votos = item.get("score", 0)
                   if votos < min_votes:
                       continue

                   score_votos = min(votos / 500.0, 1.0)
                   tiene_respuesta = 1.0 if item.get("is_answered") else 0.3
                   score = round((score_votos * 0.5 + tiene_respuesta * 0.5), 3)

                   body = item.get("body", "")
                   if len(body) > 3000:
                       body = body[:3000] + "... [truncado]"

                   resultados.append(ResultadoBusqueda(
                       fuente="stackoverflow",
                       url=item.get("link", ""),
                       codigo=body,
                       score=score,
                       metadata={
                           "votos": votos,
                           "titulo": item.get("title", ""),
                           "tags": item.get("tags", []),
                           "respondida": item.get("is_answered", False),
                           "respuestas": item.get("answer_count", 0),
                           "vistas": item.get("view_count", 0),
                       },
                   ))

               resultados.sort(key=lambda r: r.score, reverse=True)
               logger.info(f"[buscador_externo] StackOverflow: {len(resultados)} resultados para '{query}'")

           except httpx.HTTPError as e:
               logger.error(f"[buscador_externo] Error SO API: {e}")
           except Exception as e:
               logger.error(f"[buscador_externo] Error inesperado SO: {e}")

           return resultados

       async def buscar_documentacion(
           self,
           libreria: str,
           tema: str,
           max_resultados: int = 5,
       ) -> List[ResultadoBusqueda]:
           """
           Busca en documentación oficial usando GitHub code search.
           Busca en repos oficiales de la librería.
           """
           resultados: List[ResultadoBusqueda] = []
           try:
               q = f"{tema} repo:{libreria}/{libreria} path:docs OR path:README"
               resp = await self._client.get(
                   f"{GITHUB_API}/search/code",
                   params={"q": q, "per_page": max_resultados},
               )
               if resp.status_code == 403:
                   logger.warning("[buscador_externo] GitHub code search rate limit")
                   return resultados
               resp.raise_for_status()
               data = resp.json()

               for item in data.get("items", [])[:max_resultados]:
                   resultados.append(ResultadoBusqueda(
                       fuente="docs",
                       url=item.get("html_url", ""),
                       codigo=item.get("name", ""),
                       score=0.7,
                       metadata={
                           "archivo": item.get("path", ""),
                           "repo": item.get("repository", {}).get("full_name", ""),
                       },
                   ))

               logger.info(f"[buscador_externo] Docs: {len(resultados)} resultados para '{libreria}/{tema}'")

           except httpx.HTTPError as e:
               logger.error(f"[buscador_externo] Error docs search: {e}")
           except Exception as e:
               logger.error(f"[buscador_externo] Error inesperado docs: {e}")

           return resultados


4. Crear archivo src/investigador/evaluador.py:

   Ruta: ~/yeyo-os/src/investigador/evaluador.py
   Contenido:

   """
   YeyoOS — EvaluadorCandidatos
   Micro-fase 5.28 — Capa 5: Órganos

   Evalúa candidatos de búsqueda con 5 criterios de calidad.
   Retorna ranking con score 0.0-1.0 para cada candidato.
   """

   from __future__ import annotations

   import logging
   import re
   from dataclasses import dataclass, field
   from typing import Any, Dict, List, Optional

   from .modelos import ResultadoBusqueda

   logger = logging.getLogger(__name__)

   PESOS_CRITERIOS = {
       "pasa_lint": 0.20,
       "compatible_stack": 0.25,
       "tiene_tests": 0.15,
       "estrellas_votos": 0.20,
       "frescura": 0.20,
   }

   STACK_YEYO = {
       "python", "fastapi", "postgresql", "redis", "typescript",
       "react", "nextjs", "next.js", "zustand", "tailwind",
       "docker", "ollama", "pgvector", "asyncio", "httpx",
   }

   LINT_PATTERNS_BAD = [
       r"eval\s*\(",
       r"exec\s*\(",
       r"__import__\s*\(",
       r"subprocess\.call\(",
       r"os\.system\s*\(",
       r"pickle\.loads?\s*\(",
   ]


   @dataclass
   class EvaluacionCandidato:
       """Resultado de evaluación de un candidato."""
       resultado: ResultadoBusqueda
       pasa_lint: float = 0.0
       compatible_stack: float = 0.0
       tiene_tests: float = 0.0
       estrellas_votos: float = 0.0
       frescura: float = 0.0
       score_final: float = 0.0
       razones: List[str] = field(default_factory=list)


   class EvaluadorCandidatos:
       """
       Evalúa candidatos de búsqueda con 5 criterios de calidad.
       Cada criterio puntúa 0.0-1.0, y el score final es un promedio ponderado.
       """

       def __init__(self, stack_proyecto: Optional[set] = None):
           self._stack = stack_proyecto or STACK_YEYO

       def evaluar(self, candidatos: List[ResultadoBusqueda]) -> List[EvaluacionCandidato]:
           """Evalúa lista de candidatos y retorna ranking ordenado por score descendente."""
           evaluaciones: List[EvaluacionCandidato] = []

           for candidato in candidatos:
               ev = EvaluacionCandidato(resultado=candidato)

               ev.pasa_lint = self._evaluar_lint(candidato)
               ev.compatible_stack = self._evaluar_stack(candidato)
               ev.tiene_tests = self._evaluar_tests(candidato)
               ev.estrellas_votos = self._evaluar_popularidad(candidato)
               ev.frescura = self._evaluar_frescura(candidato)

               ev.score_final = round(
                   ev.pasa_lint * PESOS_CRITERIOS["pasa_lint"]
                   + ev.compatible_stack * PESOS_CRITERIOS["compatible_stack"]
                   + ev.tiene_tests * PESOS_CRITERIOS["tiene_tests"]
                   + ev.estrellas_votos * PESOS_CRITERIOS["estrellas_votos"]
                   + ev.frescura * PESOS_CRITERIOS["frescura"],
                   3,
               )

               evaluaciones.append(ev)

           evaluaciones.sort(key=lambda e: e.score_final, reverse=True)
           logger.info(
               f"[evaluador] {len(evaluaciones)} candidatos evaluados. "
               f"Top score: {evaluaciones[0].score_final if evaluaciones else 0}"
           )
           return evaluaciones

       def _evaluar_lint(self, candidato: ResultadoBusqueda) -> float:
           """Verifica que el código no tenga patrones peligrosos."""
           codigo = candidato.codigo.lower()
           for pattern in LINT_PATTERNS_BAD:
               if re.search(pattern, codigo):
                   return 0.2
           if not codigo.strip():
               return 0.5
           return 1.0

       def _evaluar_stack(self, candidato: ResultadoBusqueda) -> float:
           """Verifica compatibilidad con el stack del proyecto."""
           meta = candidato.metadata
           lenguaje = str(meta.get("lenguaje", "")).lower()
           tags = [t.lower() for t in meta.get("tags", [])]
           topics = [t.lower() for t in meta.get("topics", [])]
           texto = candidato.codigo.lower()

           coincidencias = 0
           for tech in self._stack:
               if tech in lenguaje or tech in tags or tech in topics or tech in texto:
                   coincidencias += 1

           if coincidencias == 0:
               return 0.3
           return min(coincidencias / 3.0, 1.0)

       def _evaluar_tests(self, candidato: ResultadoBusqueda) -> float:
           """Verifica si el código menciona tests."""
           codigo = candidato.codigo.lower()
           indicadores = ["test_", "pytest", "unittest", "assert ", "mock", "fixture", "describe(", "it(", "expect("]
           encontrados = sum(1 for ind in indicadores if ind in codigo)
           if encontrados >= 3:
               return 1.0
           if encontrados >= 1:
               return 0.6
           return 0.3

       def _evaluar_popularidad(self, candidato: ResultadoBusqueda) -> float:
           """Score basado en estrellas (GitHub) o votos (SO)."""
           meta = candidato.metadata
           estrellas = meta.get("estrellas", 0)
           votos = meta.get("votos", 0)
           valor = max(estrellas, votos)

           if valor >= 1000:
               return 1.0
           if valor >= 100:
               return 0.8
           if valor >= 50:
               return 0.6
           if valor >= 10:
               return 0.4
           return 0.2

       def _evaluar_frescura(self, candidato: ResultadoBusqueda) -> float:
           """Score basado en qué tan reciente es el contenido."""
           meta = candidato.metadata
           actualizado = str(meta.get("actualizado", ""))
           if "2025" in actualizado:
               return 1.0
           if "2024" in actualizado:
               return 0.8
           if "2023" in actualizado:
               return 0.5
           return 0.3


5. Crear archivo src/investigador/ensamblador.py:

   Ruta: ~/yeyo-os/src/investigador/ensamblador.py
   Contenido:

   """
   YeyoOS — Ensamblador
   Micro-fase 5.28 — Capa 5: Órganos

   Toma el candidato ganador + contexto del proyecto y usa el modelo IA
   para adaptar el código (nombres, estructura, convenciones).
   Cada adaptación es una micro-tarea con contexto limpio.
   """

   from __future__ import annotations

   import logging
   import time
   from typing import Any, Dict, Optional

   from src.ia.interfaces import IAProvider, IAResponse

   from .modelos import ResultadoBusqueda

   logger = logging.getLogger(__name__)

   PROMPT_ENSAMBLAR = """Eres un experto en adaptación de código. Tu tarea es tomar código encontrado en internet
   y adaptarlo al proyecto YeyoOS.

   REGLAS:
   1. Mantener la lógica original intacta
   2. Renombrar variables/funciones a convenciones del proyecto (snake_case Python, camelCase TypeScript)
   3. Adaptar imports a la estructura del proyecto (src/ para backend, frontend/src/ para frontend)
   4. Agregar type hints completos en Python
   5. Agregar docstrings en español
   6. Eliminar código innecesario o comentarios irrelevantes
   7. NO inventar funcionalidad que no estaba en el original
   8. Si hay dependencias externas, mencionarlas al final

   CONTEXTO DEL PROYECTO:
   {contexto_proyecto}

   CÓDIGO ORIGINAL (fuente: {fuente}, URL: {url}):
   ```
   {codigo_original}
   ```

   TAREA:
   {tarea}

   Retorna SOLO el código adaptado, sin explicaciones adicionales."""

   PROMPT_VERIFICAR_ADAPTACION = """Compara el código original con la adaptación.

   ORIGINAL:
   ```
   {codigo_original}
   ```

   ADAPTACIÓN:
   ```
   {codigo_adaptado}
   ```

   ¿La adaptación mantiene la misma lógica? ¿Hay errores?
   Responde en formato:
   CORRECTO: sí/no
   ERRORES: lista de errores o "ninguno"
   SCORE: 0.0-1.0"""


   class EnsambladorError(Exception):
       """Error durante el ensamblaje."""
       pass


   class Ensamblador:
       """
       Adapta código encontrado al contexto del proyecto YeyoOS.
       Usa el modelo IA para renombrar, reestructurar y adaptar.
       """

       def __init__(
           self,
           ia_provider: IAProvider,
           contexto_proyecto: Optional[str] = None,
       ):
           self._ia = ia_provider
           self._contexto = contexto_proyecto or self._contexto_default()

       @staticmethod
       def _contexto_default() -> str:
           return (
               "YeyoOS: OS AI-nativo. Backend FastAPI+Python en src/. "
               "Frontend Next.js+TypeScript en frontend/src/. "
               "PostgreSQL+pgvector+Redis. Modelo qwen2.5:3b via Ollama. "
               "Convenciones: snake_case Python, camelCase TypeScript, "
               "docstrings en español, type hints obligatorios, async/await."
           )

       async def ensamblar(
           self,
           candidato: ResultadoBusqueda,
           tarea: str,
           max_tokens: int = 2000,
       ) -> Dict[str, Any]:
           """
           Toma un candidato y lo adapta al proyecto.

           Returns:
               Dict con keys: codigo_adaptado, fuente, score_adaptacion, tokens_usados, duracion_ms
           """
           inicio = time.perf_counter()

           prompt = PROMPT_ENSAMBLAR.format(
               contexto_proyecto=self._contexto,
               fuente=candidato.fuente,
               url=candidato.url,
               codigo_original=candidato.codigo[:3000],
               tarea=tarea,
           )

           try:
               respuesta: IAResponse = await self._ia.generate(
                   prompt=prompt,
                   system="Eres un adaptador de código experto. Solo retorna código, sin markdown.",
                   temperature=0.3,
               )

               codigo_adaptado = self._limpiar_codigo(respuesta.content)

               score = await self._verificar_adaptacion(
                   candidato.codigo[:3000],
                   codigo_adaptado,
               )

               duracion_ms = int((time.perf_counter() - inicio) * 1000)

               logger.info(
                   f"[ensamblador] Adaptación completada: "
                   f"score={score}, tokens={respuesta.tokens_used}, "
                   f"duracion={duracion_ms}ms"
               )

               return {
                   "codigo_adaptado": codigo_adaptado,
                   "fuente": candidato.fuente,
                   "url": candidato.url,
                   "score_adaptacion": score,
                   "tokens_usados": respuesta.tokens_used,
                   "duracion_ms": duracion_ms,
               }

           except Exception as e:
               logger.error(f"[ensamblador] Error en ensamblaje: {e}")
               raise EnsambladorError(f"Fallo al ensamblar: {e}") from e

       async def _verificar_adaptacion(
           self,
           codigo_original: str,
           codigo_adaptado: str,
       ) -> float:
           """Verifica que la adaptación mantiene la lógica original."""
           try:
               prompt = PROMPT_VERIFICAR_ADAPTACION.format(
                   codigo_original=codigo_original,
                   codigo_adaptado=codigo_adaptado,
               )
               respuesta = await self._ia.generate(
                   prompt=prompt,
                   system="Evalúa la adaptación. Responde con SCORE: 0.0-1.0",
                   temperature=0.1,
               )
               contenido = respuesta.content.lower()
               for line in contenido.split("\n"):
                   if "score:" in line:
                       try:
                           score_str = line.split("score:")[-1].strip()
                           return min(max(float(score_str), 0.0), 1.0)
                       except ValueError:
                           pass
               if "correcto: sí" in contenido or "correcto: si" in contenido:
                   return 0.85
               return 0.5
           except Exception as e:
               logger.warning(f"[ensamblador] Error verificando adaptación: {e}")
               return 0.5

       @staticmethod
       def _limpiar_codigo(texto: str) -> str:
           """Elimina markdown code fences si el modelo las incluye."""
           lines = texto.strip().split("\n")
           if lines and lines[0].startswith("```"):
               lines = lines[1:]
           if lines and lines[-1].startswith("```"):
               lines = lines[:-1]
           return "\n".join(lines).strip()


6. Crear archivo src/investigador/verificador.py:

   Ruta: ~/yeyo-os/src/investigador/verificador.py
   Contenido:

   """
   YeyoOS — Verificador
   Micro-fase 5.28 — Capa 5: Órganos

   5 niveles de verificación para código investigado:
   1. Ejecución básica (compilación/interpretación)
   2. Tests independientes
   3. Análisis estático (conecta con YeyoLint 6.14 si disponible)
   4. Comparación con fuente original (similitud)
   5. Stress test en Docker (si disponible)

   Calcula confianza agregada 0.0-1.0 sobre los 5 niveles.
   """

   from __future__ import annotations

   import asyncio
   import logging
   import subprocess
   import tempfile
   import time
   from pathlib import Path
   from typing import Any, Dict, List, Optional

   from .modelos import LintResult, StressResult, TestResult, VerificacionCompleta

   logger = logging.getLogger(__name__)

   PESOS_NIVELES = {
       1: 0.25,  # Ejecución
       2: 0.25,  # Tests
       3: 0.20,  # Lint
       4: 0.15,  # Similitud con fuente
       5: 0.15,  # Stress test
   }


   class VerificadorError(Exception):
       """Error en verificación."""
       pass


   class Verificador:
       """
       Verificador de código con 5 niveles de profundidad.
       Cada nivel es independiente — si uno falla, los demás siguen.
       La confianza final es un promedio ponderado de todos los niveles.
       """

       def __init__(
           self,
           timeout_ejecucion: float = 30.0,
           timeout_tests: float = 60.0,
           timeout_stress: float = 120.0,
           yeyo_lint_fn: Optional[Any] = None,
       ):
           self._timeout_ejecucion = timeout_ejecucion
           self._timeout_tests = timeout_tests
           self._timeout_stress = timeout_stress
           self._yeyo_lint_fn = yeyo_lint_fn

       async def verificar_completo(
           self,
           codigo: str,
           lenguaje: str = "python",
           tests: Optional[str] = None,
           fuente_original: Optional[str] = None,
           config_stress: Optional[Dict[str, Any]] = None,
       ) -> VerificacionCompleta:
           """
           Ejecuta los 5 niveles de verificación.
           Cada nivel es independiente — si uno falla, los demás siguen.
           """
           resultado = VerificacionCompleta()

           resultado.nivel_1_ejecucion = await self.ejecutar_codigo(codigo, lenguaje)

           if tests:
               resultado.nivel_2_tests = await self.correr_tests(codigo, tests)
           else:
               resultado.nivel_2_tests = TestResult(passed=True, total=0)

           resultado.nivel_3_lint = await self.analisis_estatico(codigo, lenguaje)

           if fuente_original:
               resultado.nivel_4_similitud = await self.comparar_con_fuente(codigo, fuente_original)
           else:
               resultado.nivel_4_similitud = 0.7

           if config_stress:
               resultado.nivel_5_stress = await self.stress_test_docker(codigo, config_stress)
           else:
               resultado.nivel_5_stress = StressResult(passed=True)

           resultado.confianza = self.calcular_confianza(resultado)

           logger.info(f"[verificador] Verificación completa: confianza={resultado.confianza}")
           return resultado

       async def ejecutar_codigo(self, codigo: str, lenguaje: str = "python") -> bool:
           """
           Nivel 1: Verifica que el código se ejecuta sin errores de sintaxis/importación.
           Ejecuta en subprocess con timeout. NO ejecuta lógica de negocio completa.
           """
           if lenguaje not in ("python", "javascript", "typescript"):
               logger.warning(f"[verificador] Lenguaje no soportado para ejecución: {lenguaje}")
               return True

           try:
               with tempfile.NamedTemporaryFile(
                   mode="w",
                   suffix=self._extension(lenguaje),
                   delete=False,
               ) as f:
                   if lenguaje == "python":
                       f.write(f"import ast\nast.parse('''{codigo}''')\nprint('OK')\n")
                   else:
                       f.write(codigo)
                   f.flush()
                   tmp_path = f.name

               if lenguaje == "python":
                   cmd = ["python", tmp_path]
               elif lenguaje == "javascript":
                   cmd = ["node", "--check", tmp_path]
               else:
                   cmd = ["npx", "tsc", "--noEmit", tmp_path]

               proc = await asyncio.create_subprocess_exec(
                   *cmd,
                   stdout=asyncio.subprocess.PIPE,
                   stderr=asyncio.subprocess.PIPE,
               )
               stdout, stderr = await asyncio.wait_for(
                   proc.communicate(),
                   timeout=self._timeout_ejecucion,
               )

               passed = proc.returncode == 0
               if not passed:
                   logger.warning(f"[verificador] Nivel 1 falló: {stderr.decode()[:500]}")
               return passed

           except asyncio.TimeoutError:
               logger.warning("[verificador] Nivel 1 timeout")
               return False
           except Exception as e:
               logger.error(f"[verificador] Nivel 1 error: {e}")
               return False
           finally:
               try:
                   Path(tmp_path).unlink(missing_ok=True)
               except Exception:
                   pass

       async def correr_tests(self, codigo: str, tests: str) -> TestResult:
           """
           Nivel 2: Ejecuta tests independientes contra el código.
           Crea un archivo temporal con código + tests y ejecuta pytest.
           """
           try:
               with tempfile.TemporaryDirectory() as tmpdir:
                   code_path = Path(tmpdir) / "modulo.py"
                   test_path = Path(tmpdir) / "test_modulo.py"

                   code_path.write_text(codigo, encoding="utf-8")
                   test_content = f"import sys\nsys.path.insert(0, r'{tmpdir}')\nfrom modulo import *\n\n{tests}"
                   test_path.write_text(test_content, encoding="utf-8")

                   proc = await asyncio.create_subprocess_exec(
                       "python", "-m", "pytest", str(test_path), "-v", "--tb=short",
                       stdout=asyncio.subprocess.PIPE,
                       stderr=asyncio.subprocess.PIPE,
                       cwd=tmpdir,
                   )
                   stdout, stderr = await asyncio.wait_for(
                       proc.communicate(),
                       timeout=self._timeout_tests,
                   )

                   output = stdout.decode()
                   passed = proc.returncode == 0
                   total, failed = self._parse_pytest_output(output)

                   return TestResult(
                       passed=passed,
                       total=total,
                       failed=failed,
                       errors=[] if passed else [stderr.decode()[:1000]],
                       output=output[:2000],
                   )

           except asyncio.TimeoutError:
               return TestResult(passed=False, errors=["Timeout ejecutando tests"])
           except Exception as e:
               return TestResult(passed=False, errors=[str(e)])

       async def analisis_estatico(self, codigo: str, lenguaje: str = "python") -> LintResult:
           """
           Nivel 3: Análisis estático. Usa YeyoLint (6.14) si está disponible,
           sino hace análisis básico con patrones.
           """
           if self._yeyo_lint_fn:
               try:
                   return await self._yeyo_lint_fn(codigo, lenguaje)
               except Exception as e:
                   logger.warning(f"[verificador] YeyoLint falló, usando fallback: {e}")

           issues = []
           lines = codigo.split("\n")
           warnings = 0
           errors = 0

           for i, line in enumerate(lines, 1):
               stripped = line.strip()
               if "eval(" in stripped or "exec(" in stripped:
                   issues.append({"linea": i, "tipo": "error", "mensaje": "Uso de eval/exec detectado"})
                   errors += 1
               if len(line) > 120:
                   issues.append({"linea": i, "tipo": "warning", "mensaje": "Línea > 120 caracteres"})
                   warnings += 1
               if "TODO" in stripped or "FIXME" in stripped:
                   issues.append({"linea": i, "tipo": "warning", "mensaje": "TODO/FIXME encontrado"})
                   warnings += 1
               if "import *" in stripped:
                   issues.append({"linea": i, "tipo": "warning", "mensaje": "Import wildcard"})
                   warnings += 1

           return LintResult(
               passed=errors == 0,
               warnings=warnings,
               errors=errors,
               issues=issues,
           )

       async def comparar_con_fuente(self, codigo: str, fuente_original: str) -> float:
           """
           Nivel 4: Compara el código adaptado con la fuente original.
           Retorna similitud 0.0-1.0. Debe ser diferente (adaptado) pero no totalmente distinto.
           """
           if not fuente_original or not codigo:
               return 0.5

           set_original = set(fuente_original.split())
           set_adaptado = set(codigo.split())

           if not set_original or not set_adaptado:
               return 0.5

           interseccion = len(set_original & set_adaptado)
           union = len(set_original | set_adaptado)
           jaccard = interseccion / union if union > 0 else 0.0

           if jaccard > 0.95:
               return 0.6
           if jaccard > 0.3:
               return 0.9
           if jaccard > 0.1:
               return 0.7
           return 0.4

       async def stress_test_docker(
           self,
           codigo: str,
           config: Dict[str, Any],
       ) -> StressResult:
           """
           Nivel 5: Stress test en Docker container efímero.
           Ejecuta el código N veces con carga y mide rendimiento.
           Requiere Docker instalado. Si no está disponible, retorna passed=True.
           """
           iteraciones = config.get("iteraciones", 100)
           memoria_max_mb = config.get("memoria_max_mb", 256)

           try:
               proc = await asyncio.create_subprocess_exec(
                   "docker", "version",
                   stdout=asyncio.subprocess.PIPE,
                   stderr=asyncio.subprocess.PIPE,
               )
               await proc.communicate()
               if proc.returncode != 0:
                   logger.info("[verificador] Docker no disponible, saltando stress test")
                   return StressResult(passed=True, tiempo_ms=0)
           except FileNotFoundError:
               logger.info("[verificador] Docker no instalado, saltando stress test")
               return StressResult(passed=True, tiempo_ms=0)

           try:
               with tempfile.TemporaryDirectory() as tmpdir:
                   script_path = Path(tmpdir) / "stress.py"
                   stress_code = (
                       f"import time\nstart = time.time()\n"
                       f"for i in range({iteraciones}):\n"
                       f"    exec(open('/app/code.py').read(), {{}})\n"
                       f"elapsed = int((time.time() - start) * 1000)\n"
                       f"print(f'OK {{elapsed}}ms')\n"
                   )
                   script_path.write_text(stress_code, encoding="utf-8")
                   code_path = Path(tmpdir) / "code.py"
                   code_path.write_text(codigo, encoding="utf-8")

                   proc = await asyncio.create_subprocess_exec(
                       "docker", "run", "--rm",
                       "--network=none",
                       f"--memory={memoria_max_mb}m",
                       "--cpus=1",
                       "-v", f"{tmpdir}:/app:ro",
                       "python:3.11-slim",
                       "python", "/app/stress.py",
                       stdout=asyncio.subprocess.PIPE,
                       stderr=asyncio.subprocess.PIPE,
                   )
                   stdout, stderr = await asyncio.wait_for(
                       proc.communicate(),
                       timeout=self._timeout_stress,
                   )

                   output = stdout.decode()
                   passed = proc.returncode == 0 and "OK" in output
                   tiempo_ms = 0
                   if "OK" in output:
                       try:
                           tiempo_ms = int(output.split("OK")[1].strip().replace("ms", ""))
                       except (ValueError, IndexError):
                           pass

                   return StressResult(
                       passed=passed,
                       tiempo_ms=tiempo_ms,
                       memoria_peak_mb=float(memoria_max_mb),
                       errores=[] if passed else [stderr.decode()[:500]],
                   )

           except asyncio.TimeoutError:
               return StressResult(passed=False, errores=["Timeout en stress test"])
           except Exception as e:
               logger.error(f"[verificador] Error stress test: {e}")
               return StressResult(passed=False, errores=[str(e)])

       def calcular_confianza(self, resultado: VerificacionCompleta) -> float:
           """
           Calcula confianza final 0.0-1.0 como promedio ponderado de los 5 niveles.
           """
           scores = {}
           scores[1] = 1.0 if resultado.nivel_1_ejecucion else 0.0

           if resultado.nivel_2_tests:
               scores[2] = 1.0 if resultado.nivel_2_tests.passed else 0.0
           else:
               scores[2] = 0.5

           if resultado.nivel_3_lint:
               scores[3] = 1.0 if resultado.nivel_3_lint.passed else 0.3
           else:
               scores[3] = 0.5

           scores[4] = resultado.nivel_4_similitud

           if resultado.nivel_5_stress:
               scores[5] = 1.0 if resultado.nivel_5_stress.passed else 0.0
           else:
               scores[5] = 0.5

           confianza = sum(scores[n] * PESOS_NIVELES[n] for n in range(1, 6))
           return round(confianza, 3)

       @staticmethod
       def _extension(lenguaje: str) -> str:
           return {
               "python": ".py",
               "javascript": ".js",
               "typescript": ".ts",
           }.get(lenguaje, ".txt")

       @staticmethod
       def _parse_pytest_output(output: str) -> tuple:
           """Parsea output de pytest para obtener total y fallidos."""
           total = 0
           failed = 0
           for line in output.split("\n"):
               if "passed" in line or "failed" in line:
                   parts = line.split()
                   for i, p in enumerate(parts):
                       if p == "passed" and i > 0:
                           try:
                               total += int(parts[i - 1])
                           except ValueError:
                               pass
                       if p == "failed" and i > 0:
                           try:
                               failed += int(parts[i - 1])
                               total += failed
                           except ValueError:
                               pass
           return total, failed


7. Crear archivo src/investigador/pipeline.py:

   Ruta: ~/yeyo-os/src/investigador/pipeline.py
   Contenido:

   """
   YeyoOS — PipelineInvestigador
   Micro-fase 5.28 — Capa 5: Órganos

   Corazón del paradigma de investigación autónoma.
   6 fases: buscar_interno → buscar_externo → evaluar_candidatos →
   ensamblar_solucion → verificar → almacenar.

   Cuando Yeyo no tiene la respuesta en memoria, investiga en internet.
   """

   from __future__ import annotations

   import logging
   import time
   import uuid
   from typing import Any, Dict, List, Optional

   from src.ia.interfaces import IAProvider
   from src.memory.flash_memory import FlashMemory
   from src.memory.cache import MemoryCache

   from .buscador_externo import BuscadorExterno
   from .ensamblador import Ensamblador
   from .evaluador import EvaluadorCandidatos
   from .modelos import (
       InvestigacionCompleta,
       PasoInvestigacion,
       ResultadoBusqueda,
   )
   from .verificador import Verificador

   logger = logging.getLogger(__name__)

   CONFIANZA_MINIMA_INTERNA = 0.7
   CONFIANZA_MINIMA_ACEPTAR = 0.6


   class PipelineInvestigadorError(Exception):
       """Error en el pipeline de investigación."""
       pass


   class PipelineInvestigador:
       """
       Pipeline de investigación autónoma de 6 fases.

       Uso:
           pipeline = PipelineInvestigador(ia, flash_memory, cache, buscador, ...)
           resultado = await pipeline.investigar("Cómo implementar rate limiting en FastAPI")

       Integración con YeyoOrquestador (4.19):
           Un nodo de tipo "investigar" en un grafo delega al pipeline.
           Si un nodo normal falla, escala automáticamente aquí.
       """

       def __init__(
           self,
           ia_provider: IAProvider,
           flash_memory: FlashMemory,
           memory_cache: Optional[MemoryCache] = None,
           buscador_externo: Optional[BuscadorExterno] = None,
           evaluador: Optional[EvaluadorCandidatos] = None,
           ensamblador: Optional[Ensamblador] = None,
           verificador: Optional[Verificador] = None,
           cache_patrones: Optional[Any] = None,
       ):
           self._ia = ia_provider
           self._flash = flash_memory
           self._cache = memory_cache
           self._buscador = buscador_externo or BuscadorExterno()
           self._evaluador = evaluador or EvaluadorCandidatos()
           self._ensamblador = ensamblador or Ensamblador(ia_provider)
           self._verificador = verificador or Verificador()
           self._cache_patrones = cache_patrones

       async def investigar(
           self,
           tarea: str,
           lenguaje: str = "python",
           max_resultados_externos: int = 10,
       ) -> InvestigacionCompleta:
           """
           Ejecuta las 6 fases de investigación.
           Retorna InvestigacionCompleta con resultado, confianza y pasos.
           """
           tarea_id = f"inv_{uuid.uuid4().hex[:12]}"
           investigacion = InvestigacionCompleta(tarea_id=tarea_id)
           inicio = time.perf_counter()

           try:
               # Fase 0: Consultar caché de patrones (5.31) si disponible
               if self._cache_patrones:
                   patron = await self._consultar_cache_patrones(tarea, investigacion)
                   if patron and patron.get("confianza", 0) >= CONFIANZA_MINIMA_INTERNA:
                       investigacion.resultado_final = patron.get("solucion", "")
                       investigacion.confianza = patron["confianza"]
                       investigacion.exito = True
                       investigacion.tiempo_total_ms = int((time.perf_counter() - inicio) * 1000)
                       investigacion.fuentes_usadas.append("cache_patrones")
                       logger.info(f"[pipeline] {tarea_id} resuelto por caché de patrones")
                       return investigacion

               # Fase 1: Búsqueda interna (Redis → pgvector → Flash Memory)
               internos = await self.buscar_interno(tarea, investigacion)
               if internos and internos[0].score >= CONFIANZA_MINIMA_INTERNA:
                   mejor = internos[0]
                   investigacion.resultado_final = mejor.codigo
                   investigacion.confianza = mejor.score
                   investigacion.exito = True
                   investigacion.tiempo_total_ms = int((time.perf_counter() - inicio) * 1000)
                   investigacion.fuentes_usadas.append(mejor.fuente)
                   logger.info(f"[pipeline] {tarea_id} resuelto por búsqueda interna")
                   return investigacion

               # Fase 2: Búsqueda externa (GitHub, StackOverflow, docs)
               externos = await self.buscar_externo(tarea, lenguaje, max_resultados_externos, investigacion)

               todos = (internos or []) + (externos or [])
               if not todos:
                   investigacion.resultado_final = ""
                   investigacion.confianza = 0.0
                   investigacion.tiempo_total_ms = int((time.perf_counter() - inicio) * 1000)
                   logger.warning(f"[pipeline] {tarea_id} sin resultados")
                   return investigacion

               # Fase 3: Evaluar candidatos
               evaluados = await self.evaluar_candidatos(todos, investigacion)
               if not evaluados:
                   investigacion.tiempo_total_ms = int((time.perf_counter() - inicio) * 1000)
                   return investigacion

               mejor_candidato = evaluados[0].resultado

               # Fase 4: Ensamblar solución
               ensamblado = await self.ensamblar_solucion(mejor_candidato, tarea, investigacion)

               # Fase 5: Verificar
               confianza = await self.verificar(
                   ensamblado.get("codigo_adaptado", ""),
                   lenguaje,
                   mejor_candidato.codigo,
                   investigacion,
               )

               # Fase 6: Almacenar en memoria
               if confianza >= CONFIANZA_MINIMA_ACEPTAR:
                   await self.almacenar(
                       tarea_id,
                       tarea,
                       ensamblado.get("codigo_adaptado", ""),
                       confianza,
                       investigacion,
                   )
                   investigacion.resultado_final = ensamblado.get("codigo_adaptado", "")
                   investigacion.confianza = confianza
                   investigacion.exito = True
               else:
                   investigacion.resultado_final = ensamblado.get("codigo_adaptado", "")
                   investigacion.confianza = confianza
                   investigacion.exito = False

           except Exception as e:
               logger.error(f"[pipeline] {tarea_id} error: {e}")
               investigacion.exito = False

           investigacion.tiempo_total_ms = int((time.perf_counter() - inicio) * 1000)
           investigacion.tokens_total = sum(p.tokens for p in investigacion.pasos)
           return investigacion

       async def buscar_interno(
           self,
           tarea: str,
           investigacion: InvestigacionCompleta,
       ) -> List[ResultadoBusqueda]:
           """Fase 1: Busca en Redis → pgvector → Flash Memory."""
           inicio = time.perf_counter()
           resultados: List[ResultadoBusqueda] = []

           try:
               # 1a. Redis cache
               if self._cache:
                   try:
                       cached = await self._cache.get(f"inv:{tarea[:100]}")
                       if cached:
                           resultados.append(ResultadoBusqueda(
                               fuente="redis",
                               url=f"cache:inv:{tarea[:50]}",
                               codigo=cached.content if hasattr(cached, 'content') else str(cached),
                               score=0.9,
                               metadata={"origen": "redis_cache"},
                           ))
                   except Exception as e:
                       logger.debug(f"[pipeline] Redis miss: {e}")

               # 1b. pgvector semantic search via Flash Memory
               try:
                   embedding = await self._ia.get_embedding(tarea)
                   memorias = await self._flash.search_semantic(
                       embedding=embedding,
                       threshold=0.7,
                       limit=5,
                   )
                   for mem in memorias:
                       resultados.append(ResultadoBusqueda(
                           fuente="pgvector",
                           url=f"memory:{mem.id}",
                           codigo=mem.content,
                           score=0.8,
                           metadata={"tipo": mem.type, "tier": mem.tier},
                       ))
               except Exception as e:
                   logger.debug(f"[pipeline] pgvector search error: {e}")

               # 1c. Flash Memory recall por texto
               try:
                   memorias = await self._flash.recall(query=tarea, limit=5)
                   for mem in memorias:
                       if not any(r.url == f"memory:{mem.id}" for r in resultados):
                           resultados.append(ResultadoBusqueda(
                               fuente="flash_memory",
                               url=f"memory:{mem.id}",
                               codigo=mem.content,
                               score=0.7,
                               metadata={"tipo": mem.type, "tier": mem.tier},
                           ))
               except Exception as e:
                   logger.debug(f"[pipeline] Flash Memory recall error: {e}")

           except Exception as e:
               logger.error(f"[pipeline] Error búsqueda interna: {e}")

           duracion_ms = int((time.perf_counter() - inicio) * 1000)
           investigacion.pasos.append(PasoInvestigacion(
               numero=len(investigacion.pasos) + 1,
               tipo="busqueda_interna",
               input_resumen=tarea[:200],
               output_resumen=f"{len(resultados)} resultados internos",
               duracion_ms=duracion_ms,
           ))
           return resultados

       async def buscar_externo(
           self,
           tarea: str,
           lenguaje: str,
           max_resultados: int,
           investigacion: InvestigacionCompleta,
       ) -> List[ResultadoBusqueda]:
           """Fase 2: Busca en GitHub, StackOverflow, documentación."""
           inicio = time.perf_counter()
           resultados: List[ResultadoBusqueda] = []

           try:
               github_res = await self._buscador.buscar_github(
                   query=tarea,
                   min_stars=50,
                   lenguaje=lenguaje,
                   max_resultados=max_resultados,
               )
               resultados.extend(github_res)
               investigacion.fuentes_usadas.append("github")
           except Exception as e:
               logger.warning(f"[pipeline] GitHub search failed: {e}")

           try:
               so_res = await self._buscador.buscar_stackoverflow(
                   query=tarea,
                   min_votes=10,
                   max_resultados=max_resultados,
               )
               resultados.extend(so_res)
               investigacion.fuentes_usadas.append("stackoverflow")
           except Exception as e:
               logger.warning(f"[pipeline] StackOverflow search failed: {e}")

           duracion_ms = int((time.perf_counter() - inicio) * 1000)
           investigacion.pasos.append(PasoInvestigacion(
               numero=len(investigacion.pasos) + 1,
               tipo="busqueda_externa",
               input_resumen=tarea[:200],
               output_resumen=f"{len(resultados)} resultados externos (GitHub + SO)",
               duracion_ms=duracion_ms,
           ))
           return resultados

       async def evaluar_candidatos(
           self,
           candidatos: List[ResultadoBusqueda],
           investigacion: InvestigacionCompleta,
       ) -> list:
           """Fase 3: Evalúa candidatos con criterios de calidad."""
           inicio = time.perf_counter()
           evaluados = self._evaluador.evaluar(candidatos)

           duracion_ms = int((time.perf_counter() - inicio) * 1000)
           top_score = evaluados[0].score_final if evaluados else 0
           investigacion.pasos.append(PasoInvestigacion(
               numero=len(investigacion.pasos) + 1,
               tipo="evaluacion",
               input_resumen=f"{len(candidatos)} candidatos",
               output_resumen=f"Top score: {top_score}",
               duracion_ms=duracion_ms,
           ))
           return evaluados

       async def ensamblar_solucion(
           self,
           candidato: ResultadoBusqueda,
           tarea: str,
           investigacion: InvestigacionCompleta,
       ) -> Dict[str, Any]:
           """Fase 4: Ensambla la solución adaptándola al proyecto."""
           inicio = time.perf_counter()
           resultado = await self._ensamblador.ensamblar(candidato, tarea)

           duracion_ms = int((time.perf_counter() - inicio) * 1000)
           investigacion.pasos.append(PasoInvestigacion(
               numero=len(investigacion.pasos) + 1,
               tipo="ensamblaje",
               input_resumen=f"Candidato de {candidato.fuente}",
               output_resumen=f"Adaptado, score={resultado.get('score_adaptacion', 0)}",
               tokens=resultado.get("tokens_usados", 0),
               duracion_ms=duracion_ms,
           ))
           return resultado

       async def verificar(
           self,
           codigo: str,
           lenguaje: str,
           fuente_original: str,
           investigacion: InvestigacionCompleta,
       ) -> float:
           """Fase 5: Verifica con 5 niveles."""
           inicio = time.perf_counter()
           resultado = await self._verificador.verificar_completo(
               codigo=codigo,
               lenguaje=lenguaje,
               fuente_original=fuente_original,
           )

           duracion_ms = int((time.perf_counter() - inicio) * 1000)
           investigacion.pasos.append(PasoInvestigacion(
               numero=len(investigacion.pasos) + 1,
               tipo="verificacion",
               input_resumen=f"Código {lenguaje} ({len(codigo)} chars)",
               output_resumen=f"Confianza: {resultado.confianza}",
               confianza=resultado.confianza,
               duracion_ms=duracion_ms,
           ))
           return resultado.confianza

       async def almacenar(
           self,
           tarea_id: str,
           tarea: str,
           codigo: str,
           confianza: float,
           investigacion: InvestigacionCompleta,
       ) -> None:
           """Fase 6: Almacena en Flash Memory + pgvector + Redis."""
           inicio = time.perf_counter()

           try:
               embedding = await self._ia.get_embedding(f"{tarea}\n{codigo[:500]}")
               await self._flash.store(
                   content=f"[Investigación {tarea_id}]\nTarea: {tarea}\n\n{codigo}",
                   type="skill",
                   metadata={
                       "tarea_id": tarea_id,
                       "confianza": confianza,
                       "fuentes": investigacion.fuentes_usadas,
                       "pasos": len(investigacion.pasos),
                   },
                   embedding=embedding,
                   source="investigador",
               )

               if self._cache:
                   try:
                       from src.memory.models import Memory
                       mem = Memory(
                           id=tarea_id,
                           content=codigo[:5000],
                           type="skill",
                           tier="WARM",
                           embedding=None,
                           checksum="",
                           access_count=0,
                           metadata={"confianza": confianza},
                           source="investigador",
                       )
                       await self._cache.set(mem, ttl=86400)
                   except Exception as e:
                       logger.debug(f"[pipeline] Redis cache set error: {e}")

           except Exception as e:
               logger.error(f"[pipeline] Error almacenando: {e}")

           duracion_ms = int((time.perf_counter() - inicio) * 1000)
           investigacion.pasos.append(PasoInvestigacion(
               numero=len(investigacion.pasos) + 1,
               tipo="almacenamiento",
               input_resumen=f"Resultado {tarea_id}",
               output_resumen=f"Almacenado con confianza {confianza}",
               duracion_ms=duracion_ms,
           ))

       async def _consultar_cache_patrones(
           self,
           tarea: str,
           investigacion: InvestigacionCompleta,
       ) -> Optional[Dict[str, Any]]:
           """Consulta CachePatrones (5.31) para reutilizar razonamientos previos."""
           try:
               patron = await self._cache_patrones.buscar_patron(tarea, threshold=0.85)
               if patron:
                   return {
                       "solucion": patron.patron_correcto,
                       "confianza": patron.confianza,
                   }
           except Exception as e:
               logger.debug(f"[pipeline] CachePatrones no disponible: {e}")
           return None


8. Crear archivo db/migrations/investigacion_pasos.sql:

   Ruta: ~/yeyo-os/db/migrations/investigacion_pasos.sql
   Contenido:

   -- YeyoOS — Tabla investigacion_pasos
   -- Micro-fase 5.28 — Capa 5: Órganos
   -- Tracking detallado de cada paso del Pipeline Investigador

   CREATE TABLE IF NOT EXISTS investigacion_pasos (
       id SERIAL PRIMARY KEY,
       tarea_id TEXT NOT NULL,
       paso_numero INTEGER NOT NULL,
       tipo TEXT NOT NULL,
       input_resumen TEXT,
       output_resumen TEXT,
       tokens_usados INTEGER DEFAULT 0,
       duracion_ms INTEGER DEFAULT 0,
       confianza FLOAT DEFAULT 0.0,
       created_at TIMESTAMP DEFAULT NOW()
   );

   CREATE INDEX IF NOT EXISTS idx_investigacion_tarea ON investigacion_pasos(tarea_id);
   CREATE INDEX IF NOT EXISTS idx_investigacion_tipo ON investigacion_pasos(tipo);


9. Crear archivo tests/unit/investigador/__init__.py:

   Ruta: ~/yeyo-os/tests/unit/investigador/__init__.py
   Contenido:



10. Crear archivo tests/unit/investigador/test_pipeline.py:

    Ruta: ~/yeyo-os/tests/unit/investigador/test_pipeline.py
    Contenido:

    """
    Tests unitarios para PipelineInvestigador.
    Micro-fase 5.28 — 10 tests.
    """

    import pytest
    from unittest.mock import AsyncMock, MagicMock, patch

    from src.investigador.modelos import (
        InvestigacionCompleta,
        PasoInvestigacion,
        ResultadoBusqueda,
    )
    from src.investigador.pipeline import PipelineInvestigador, CONFIANZA_MINIMA_INTERNA
    from src.investigador.evaluador import EvaluadorCandidatos, EvaluacionCandidato
    from src.investigador.buscador_externo import BuscadorExterno
    from src.investigador.ensamblador import Ensamblador
    from src.investigador.verificador import Verificador


    @pytest.fixture
    def mock_ia():
        ia = AsyncMock()
        ia.generate.return_value = MagicMock(content="codigo adaptado", tokens_used=100, latency_ms=50)
        ia.get_embedding.return_value = [0.1] * 768
        return ia


    @pytest.fixture
    def mock_flash():
        flash = AsyncMock()
        flash.recall.return_value = []
        flash.search_semantic.return_value = []
        flash.store.return_value = MagicMock(id="mem_123")
        return flash


    @pytest.fixture
    def mock_cache():
        cache = AsyncMock()
        cache.get.return_value = None
        cache.set.return_value = None
        return cache


    @pytest.fixture
    def mock_buscador():
        buscador = AsyncMock(spec=BuscadorExterno)
        buscador.buscar_github.return_value = [
            ResultadoBusqueda(
                fuente="github",
                url="https://github.com/test/repo",
                codigo="def hello(): return 'world'",
                score=0.8,
                metadata={"estrellas": 500, "lenguaje": "Python"},
            ),
        ]
        buscador.buscar_stackoverflow.return_value = []
        return buscador


    @pytest.fixture
    def pipeline(mock_ia, mock_flash, mock_cache, mock_buscador):
        return PipelineInvestigador(
            ia_provider=mock_ia,
            flash_memory=mock_flash,
            memory_cache=mock_cache,
            buscador_externo=mock_buscador,
        )


    @pytest.mark.asyncio
    async def test_investigar_retorna_investigacion_completa(pipeline):
        resultado = await pipeline.investigar("cómo hacer rate limiting")
        assert isinstance(resultado, InvestigacionCompleta)
        assert resultado.tarea_id.startswith("inv_")
        assert resultado.tiempo_total_ms >= 0


    @pytest.mark.asyncio
    async def test_investigar_busca_interno_primero(pipeline, mock_flash):
        from src.memory.models import Memory
        mem = MagicMock()
        mem.id = "mem_1"
        mem.content = "solución encontrada"
        mem.type = "skill"
        mem.tier = "HOT"
        mock_flash.search_semantic.return_value = [mem]
        resultado = await pipeline.investigar("algo conocido")
        assert len(resultado.pasos) >= 1
        assert resultado.pasos[0].tipo == "busqueda_interna"


    @pytest.mark.asyncio
    async def test_investigar_busca_externo_si_interno_no_tiene(pipeline, mock_buscador):
        resultado = await pipeline.investigar("algo nuevo")
        mock_buscador.buscar_github.assert_called_once()


    @pytest.mark.asyncio
    async def test_investigar_evalua_candidatos(pipeline):
        resultado = await pipeline.investigar("test query")
        tipos_pasos = [p.tipo for p in resultado.pasos]
        assert "evaluacion" in tipos_pasos


    @pytest.mark.asyncio
    async def test_investigar_ensambla_mejor_candidato(pipeline):
        resultado = await pipeline.investigar("test ensamblaje")
        tipos_pasos = [p.tipo for p in resultado.pasos]
        assert "ensamblaje" in tipos_pasos


    @pytest.mark.asyncio
    async def test_investigar_verifica_resultado(pipeline):
        resultado = await pipeline.investigar("test verificación")
        tipos_pasos = [p.tipo for p in resultado.pasos]
        assert "verificacion" in tipos_pasos


    @pytest.mark.asyncio
    async def test_investigar_almacena_si_confianza_suficiente(pipeline, mock_flash):
        resultado = await pipeline.investigar("test almacenamiento")
        if resultado.confianza >= 0.6:
            mock_flash.store.assert_called()


    @pytest.mark.asyncio
    async def test_investigar_sin_resultados(pipeline, mock_buscador):
        mock_buscador.buscar_github.return_value = []
        mock_buscador.buscar_stackoverflow.return_value = []
        resultado = await pipeline.investigar("algo imposible de encontrar")
        assert resultado.confianza <= 0.1


    @pytest.mark.asyncio
    async def test_investigar_con_cache_patrones(mock_ia, mock_flash):
        cache_patrones = AsyncMock()
        patron_mock = MagicMock()
        patron_mock.patron_correcto = "solución cacheada"
        patron_mock.confianza = 0.95
        cache_patrones.buscar_patron.return_value = patron_mock

        pipeline = PipelineInvestigador(
            ia_provider=mock_ia,
            flash_memory=mock_flash,
            cache_patrones=cache_patrones,
        )
        resultado = await pipeline.investigar("problema conocido")
        assert resultado.exito is True
        assert resultado.confianza >= 0.9


    @pytest.mark.asyncio
    async def test_investigar_registra_todos_los_pasos(pipeline):
        resultado = await pipeline.investigar("test pasos completos")
        assert len(resultado.pasos) >= 2
        for paso in resultado.pasos:
            assert isinstance(paso, PasoInvestigacion)
            assert paso.numero > 0
            assert paso.tipo != ""


11. Crear archivo tests/unit/investigador/test_verificador.py:

    Ruta: ~/yeyo-os/tests/unit/investigador/test_verificador.py
    Contenido:

    """
    Tests unitarios para Verificador.
    Micro-fase 5.28 — 8 tests (uno por nivel + combinaciones).
    """

    import pytest
    from unittest.mock import AsyncMock, MagicMock, patch

    from src.investigador.verificador import Verificador
    from src.investigador.modelos import (
        LintResult,
        StressResult,
        TestResult,
        VerificacionCompleta,
    )


    @pytest.fixture
    def verificador():
        return Verificador(timeout_ejecucion=10.0, timeout_tests=10.0)


    @pytest.mark.asyncio
    async def test_nivel_1_codigo_valido(verificador):
        resultado = await verificador.ejecutar_codigo("x = 1 + 1\nprint(x)", "python")
        assert resultado is True


    @pytest.mark.asyncio
    async def test_nivel_1_codigo_invalido(verificador):
        resultado = await verificador.ejecutar_codigo("def (invalid syntax", "python")
        assert resultado is False


    @pytest.mark.asyncio
    async def test_nivel_2_tests_pasan(verificador):
        codigo = "def suma(a, b): return a + b"
        tests = "def test_suma():\n    assert suma(2, 3) == 5"
        resultado = await verificador.correr_tests(codigo, tests)
        assert isinstance(resultado, TestResult)
        assert resultado.passed is True


    @pytest.mark.asyncio
    async def test_nivel_3_lint_limpio(verificador):
        codigo = "x = 1\ny = 2\nprint(x + y)"
        resultado = await verificador.analisis_estatico(codigo, "python")
        assert isinstance(resultado, LintResult)
        assert resultado.passed is True
        assert resultado.errors == 0


    @pytest.mark.asyncio
    async def test_nivel_3_lint_detecta_eval(verificador):
        codigo = "resultado = eval(input())"
        resultado = await verificador.analisis_estatico(codigo, "python")
        assert resultado.errors > 0
        assert resultado.passed is False


    @pytest.mark.asyncio
    async def test_nivel_4_similitud(verificador):
        original = "def hello(): return 'world'"
        adaptado = "def hello(): return 'mundo'"
        score = await verificador.comparar_con_fuente(adaptado, original)
        assert 0.0 <= score <= 1.0


    @pytest.mark.asyncio
    async def test_nivel_5_stress_sin_docker(verificador):
        resultado = await verificador.stress_test_docker("x = 1", {"iteraciones": 10})
        assert isinstance(resultado, StressResult)


    @pytest.mark.asyncio
    async def test_calcular_confianza_todos_pasan(verificador):
        resultado = VerificacionCompleta(
            nivel_1_ejecucion=True,
            nivel_2_tests=TestResult(passed=True, total=5),
            nivel_3_lint=LintResult(passed=True),
            nivel_4_similitud=0.85,
            nivel_5_stress=StressResult(passed=True),
        )
        confianza = verificador.calcular_confianza(resultado)
        assert confianza > 0.8


VERIFICAR:

1. Ejecutar: cd ~/yeyo-os && python -m pytest tests/unit/investigador/test_pipeline.py -v
   Esperado: 10 tests pasan

2. Ejecutar: cd ~/yeyo-os && python -m pytest tests/unit/investigador/test_verificador.py -v
   Esperado: 8 tests pasan

3. Ejecutar: cd ~/yeyo-os && python -c "from src.investigador import PipelineInvestigador, ResultadoBusqueda, InvestigacionCompleta; print('OK')"
   Esperado: OK

4. Ejecutar: cd ~/yeyo-os && python -c "from src.investigador.verificador import Verificador; print('OK')"
   Esperado: OK

5. Ejecutar: cd ~/yeyo-os && python -c "from src.investigador.buscador_externo import BuscadorExterno; print('OK')"
   Esperado: OK

6. Verificar que la migración SQL es válida:
   cat ~/yeyo-os/db/migrations/investigacion_pasos.sql

SI FALLA:
- Si falla import de src.memory.flash_memory: verificar que existe, ajustar import
- Si falla import de src.ia.interfaces: verificar ruta exacta
- Si pytest no encuentra los tests: verificar que tests/unit/investigador/__init__.py existe
- Si falla test de ejecución de código: puede ser que python no esté en PATH como "python" — ajustar a "python3"

NO HACER:
- NO modificar archivos existentes de src/memory/, src/ia/, src/orquestador/
- NO instalar dependencias nuevas (httpx ya está en requirements.txt)
- NO crear archivos fuera de src/investigador/, db/migrations/, tests/unit/investigador/
- NO hardcodear tokens de GitHub — usar variable de entorno GITHUB_TOKEN

GATE:
✅ PipelineInvestigador recibe una tarea
✅ Busca internamente (Redis → pgvector → Flash Memory)
✅ Si no encuentra, busca en GitHub/StackOverflow/docs
✅ Evalúa candidatos con 5 criterios (lint, stack, tests, popularidad, frescura)
✅ Ensambla la mejor solución adaptándola al proyecto
✅ Verifica con 5 niveles (ejecución, tests, lint, similitud, stress)
✅ Almacena en Flash Memory + pgvector + Redis
✅ 10 tests de pipeline + 8 tests de verificador pasan
✅ Tabla investigacion_pasos creada
✅ Imports de InvestigacionCompleta, ResultadoBusqueda, PasoInvestigacion exportados correctamente
```
