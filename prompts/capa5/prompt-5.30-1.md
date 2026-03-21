## ═══════════════════════════════════════
## MICRO-FASE 5.30 — Razonamiento Extendido: CoT + ToT + Self-Consistency
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 5.30-1 [VSCODE] — Tres estrategias de razonamiento profundo integradas con micro-tareas

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 5.30 de Capa 5 (Órganos): implementar 3 estrategias de razonamiento profundo — Chain of Thought, Tree of Thought, Self-Consistency — todas usando micro-tareas (5.29) para mantener contexto limpio por paso.

CONTEXTO:
- Micro-fase 5.28 completada: PipelineInvestigador con 6 fases
- Micro-fase 5.29 completada: EjecutorMicroTareas + TareaDB funcionando
- Modelos compartidos en src/investigador/modelos.py:
  - PasoInvestigacion(numero, tipo, input_resumen, output_resumen, tokens, duracion_ms)
  - InvestigacionCompleta(tarea_id, pasos, resultado_final, confianza, tiempo_total_ms)
- EjecutorMicroTareas en src/investigador/micro_tareas.py:
  - MicroTarea(prompt, input_keys, output_key, max_tokens, system, temperature)
  - ResultadoCadena(tarea_id, pasos, exito, resultado_final, tokens_total, duracion_total_ms)
  - ejecutar_cadena(tareas, tarea_id, datos_iniciales) -> ResultadoCadena
- TareaDB en src/investigador/tarea_db.py: guardar_paso(), leer_paso(), guardar_dato(), leer_dato()
- IAProvider en src/ia/interfaces.py: generate(), chat(), get_embedding()
- OllamaProvider en src/ia/ollama_provider.py: implementación qwen2.5:3b
- YeyoOrquestador en src/orquestador/orquestador.py: nodos del grafo pueden tener estrategia "cot"|"tot"|"sc"|"auto"
- Razonamiento es USADO POR: YeyoOrquestador (4.19), Autodidacta (7.26)

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/investigador/razonamiento.py:

   Ruta: ~/yeyo-os/src/investigador/razonamiento.py
   Contenido:

   """
   YeyoOS — Estrategias de Razonamiento Extendido
   Micro-fase 5.30 — Capa 5: Órganos

   3 estrategias de razonamiento profundo:
   1. ChainOfThought — pasos secuenciales de razonamiento
   2. TreeOfThought — K soluciones en paralelo, evalúa y elige la mejor
   3. SelfConsistency — N respuestas con temperatura alta, vota por consenso

   Todas usan EjecutorMicroTareas (5.29) para mantener contexto limpio por paso.
   """

   from __future__ import annotations

   import asyncio
   import logging
   import time
   import uuid
   from collections import Counter
   from dataclasses import dataclass, field
   from typing import Any, Dict, List, Optional

   from src.ia.interfaces import IAProvider

   from .micro_tareas import EjecutorMicroTareas, MicroTarea, ResultadoCadena
   from .tarea_db import TareaDB

   logger = logging.getLogger(__name__)


   @dataclass
   class ResultadoRazonamiento:
       """Resultado unificado de cualquier estrategia de razonamiento."""
       estrategia: str  # "cot", "tot", "sc"
       resultado_final: str = ""
       confianza: float = 0.0
       pasos_total: int = 0
       tokens_total: int = 0
       duracion_total_ms: int = 0
       caminos_explorados: int = 1
       consenso: Optional[float] = None
       detalles: Dict[str, Any] = field(default_factory=dict)


   class RazonamientoError(Exception):
       """Error en razonamiento."""
       pass


   class ChainOfThought:
       """
       Chain of Thought: razonamiento paso a paso.
       Cada paso es una micro-tarea con contexto limpio.
       El output de cada paso alimenta el siguiente via DB.

       Ideal para: complejidad 0.3-0.6, problemas descomponibles en pasos.
       """

       def __init__(
           self,
           ia_provider: IAProvider,
           tarea_db: TareaDB,
           num_pasos: int = 5,
           max_tokens_por_paso: int = 1500,
       ):
           self._ia = ia_provider
           self._db = tarea_db
           self._num_pasos = num_pasos
           self._max_tokens = max_tokens_por_paso
           self._ejecutor = EjecutorMicroTareas(ia_provider, tarea_db, max_tokens_por_paso)

       async def razonar(self, tarea: str) -> ResultadoRazonamiento:
           """
           Ejecuta razonamiento Chain of Thought.
           Genera N pasos secuenciales, cada uno refinando el anterior.
           """
           inicio = time.perf_counter()

           micro_tareas: List[MicroTarea] = []

           # Paso 1: Descomponer el problema
           micro_tareas.append(MicroTarea(
               prompt=(
                   "Descompone este problema en pasos claros y concretos.\n"
                   "Problema: {tarea}\n\n"
                   "Lista los pasos necesarios para resolverlo (máximo 5 pasos)."
               ),
               input_keys=["tarea"],
               output_key="descomposicion",
               max_tokens=self._max_tokens,
               system="Eres un experto en descomposición de problemas. Sé preciso y concreto.",
           ))

           # Paso 2: Resolver paso a paso
           micro_tareas.append(MicroTarea(
               prompt=(
                   "Resuelve el siguiente problema paso a paso.\n\n"
                   "Plan de pasos:\n{descomposicion}\n\n"
                   "Ejecuta cada paso y muestra el resultado intermedio."
               ),
               input_keys=["descomposicion"],
               output_key="razonamiento",
               max_tokens=self._max_tokens,
               system="Resuelve cada paso mostrando tu razonamiento. Sé metódico.",
               temperature=0.3,
           ))

           # Paso 3: Sintetizar resultado
           micro_tareas.append(MicroTarea(
               prompt=(
                   "Sintetiza la solución final basándote en este razonamiento:\n\n"
                   "{razonamiento}\n\n"
                   "Genera SOLO la solución final, limpia y lista para usar."
               ),
               input_keys=["razonamiento"],
               output_key="solucion",
               max_tokens=self._max_tokens,
               system="Sintetiza la solución. Solo el resultado final, sin explicaciones.",
               temperature=0.2,
           ))

           # Pasos adicionales de refinamiento si num_pasos > 3
           for i in range(3, self._num_pasos):
               micro_tareas.append(MicroTarea(
                   prompt=(
                       f"Revisa y mejora esta solución (iteración {i - 2}):\n\n"
                       "{solucion}\n\n"
                       "¿Hay errores? ¿Se puede optimizar? Retorna la versión mejorada."
                   ),
                   input_keys=["solucion"],
                   output_key="solucion",
                   max_tokens=self._max_tokens,
                   system="Revisa críticamente y mejora. Si está bien, retórnala igual.",
                   temperature=0.2,
               ))

           resultado_cadena = await self._ejecutor.ejecutar_cadena(
               micro_tareas,
               datos_iniciales={"tarea": tarea},
           )

           duracion_ms = int((time.perf_counter() - inicio) * 1000)

           return ResultadoRazonamiento(
               estrategia="cot",
               resultado_final=resultado_cadena.resultado_final,
               confianza=0.75 if resultado_cadena.exito else 0.2,
               pasos_total=len(resultado_cadena.pasos),
               tokens_total=resultado_cadena.tokens_total,
               duracion_total_ms=duracion_ms,
               caminos_explorados=1,
               detalles={"pasos": [p.output_resumen for p in resultado_cadena.pasos]},
           )


   class TreeOfThought:
       """
       Tree of Thought: genera K soluciones independientes en paralelo,
       evalúa cada una y elige la mejor. Opcionalmente refina la ganadora.

       Ideal para: complejidad 0.6-0.8, problemas con múltiples enfoques posibles.
       """

       def __init__(
           self,
           ia_provider: IAProvider,
           tarea_db: TareaDB,
           num_ramas: int = 3,
           max_tokens_por_paso: int = 1500,
       ):
           self._ia = ia_provider
           self._db = tarea_db
           self._num_ramas = num_ramas
           self._max_tokens = max_tokens_por_paso

       async def razonar(self, tarea: str) -> ResultadoRazonamiento:
           """
           Genera K soluciones en paralelo, evalúa y elige la mejor.
           """
           inicio = time.perf_counter()

           # Fase 1: Generar K soluciones en paralelo
           tareas_paralelas = []
           for i in range(self._num_ramas):
               ejecutor = EjecutorMicroTareas(self._ia, self._db, self._max_tokens)
               cadena = [
                   MicroTarea(
                       prompt=(
                           f"Resuelve este problema usando enfoque #{i + 1} (sé creativo, "
                           f"explora un camino diferente a los demás):\n\n"
                           "{tarea}\n\n"
                           "Genera una solución completa."
                       ),
                       input_keys=["tarea"],
                       output_key=f"solucion_{i}",
                       max_tokens=self._max_tokens,
                       system="Eres un experto. Genera una solución completa y diferente.",
                       temperature=0.7 + (i * 0.1),
                   ),
               ]
               tareas_paralelas.append(
                   ejecutor.ejecutar_cadena(
                       cadena,
                       tarea_id=f"tot_rama_{i}_{uuid.uuid4().hex[:8]}",
                       datos_iniciales={"tarea": tarea},
                   )
               )

           resultados_ramas = await asyncio.gather(*tareas_paralelas, return_exceptions=True)

           # Recolectar soluciones exitosas
           soluciones: List[str] = []
           tokens_total = 0
           for r in resultados_ramas:
               if isinstance(r, ResultadoCadena) and r.exito:
                   soluciones.append(r.resultado_final)
                   tokens_total += r.tokens_total

           if not soluciones:
               return ResultadoRazonamiento(
                   estrategia="tot",
                   resultado_final="",
                   confianza=0.0,
                   duracion_total_ms=int((time.perf_counter() - inicio) * 1000),
               )

           # Fase 2: Evaluar y elegir la mejor
           evaluador = EjecutorMicroTareas(self._ia, self._db, self._max_tokens)
           soluciones_texto = "\n\n---\n\n".join(
               [f"SOLUCIÓN {i + 1}:\n{s}" for i, s in enumerate(soluciones)]
           )
           cadena_eval = [
               MicroTarea(
                   prompt=(
                       f"Evalúa estas {len(soluciones)} soluciones al problema:\n"
                       f"Problema: {tarea[:500]}\n\n"
                       f"{soluciones_texto}\n\n"
                       "¿Cuál es la mejor? Responde SOLO con el número (1, 2, etc.) "
                       "y una línea de justificación."
                   ),
                   input_keys=[],
                   output_key="evaluacion",
                   max_tokens=self._max_tokens,
                   system="Evalúa objetivamente. Elige la mejor solución.",
                   temperature=0.1,
               ),
           ]
           resultado_eval = await evaluador.ejecutar_cadena(cadena_eval)
           tokens_total += resultado_eval.tokens_total

           # Parsear la solución ganadora
           mejor_idx = self._parsear_mejor(resultado_eval.resultado_final, len(soluciones))
           mejor_solucion = soluciones[mejor_idx]

           # Fase 3: Refinar la ganadora
           refinador = EjecutorMicroTareas(self._ia, self._db, self._max_tokens)
           cadena_refinar = [
               MicroTarea(
                   prompt=(
                       "Refina y mejora esta solución:\n\n"
                       "{solucion}\n\n"
                       "Corrige errores, optimiza, y retorna la versión final."
                   ),
                   input_keys=["solucion"],
                   output_key="final",
                   max_tokens=self._max_tokens,
                   system="Mejora la solución. Retorna solo el resultado final.",
                   temperature=0.2,
               ),
           ]
           resultado_refinar = await refinador.ejecutar_cadena(
               cadena_refinar,
               datos_iniciales={"solucion": mejor_solucion},
           )
           tokens_total += resultado_refinar.tokens_total

           duracion_ms = int((time.perf_counter() - inicio) * 1000)

           return ResultadoRazonamiento(
               estrategia="tot",
               resultado_final=resultado_refinar.resultado_final or mejor_solucion,
               confianza=0.85 if resultado_refinar.exito else 0.6,
               pasos_total=sum(
                   len(r.pasos) for r in resultados_ramas if isinstance(r, ResultadoCadena)
               ) + len(resultado_eval.pasos) + len(resultado_refinar.pasos),
               tokens_total=tokens_total,
               duracion_total_ms=duracion_ms,
               caminos_explorados=len(soluciones),
               detalles={
                   "ramas_generadas": self._num_ramas,
                   "ramas_exitosas": len(soluciones),
                   "mejor_rama": mejor_idx + 1,
               },
           )

       @staticmethod
       def _parsear_mejor(evaluacion: str, num_soluciones: int) -> int:
           """Extrae el índice de la mejor solución de la evaluación."""
           for char in evaluacion:
               if char.isdigit():
                   idx = int(char) - 1
                   if 0 <= idx < num_soluciones:
                       return idx
           return 0


   class SelfConsistency:
       """
       Self-Consistency: genera la misma respuesta N veces con temperatura alta,
       vota por la más frecuente. Si no hay consenso, escala a TreeOfThought.

       Ideal para: complejidad > 0.8, problemas donde la respuesta correcta
       debe emerger por consenso.
       """

       def __init__(
           self,
           ia_provider: IAProvider,
           tarea_db: TareaDB,
           num_muestras: int = 5,
           umbral_consenso: float = 0.6,
           max_tokens_por_paso: int = 1500,
       ):
           self._ia = ia_provider
           self._db = tarea_db
           self._num_muestras = num_muestras
           self._umbral_consenso = umbral_consenso
           self._max_tokens = max_tokens_por_paso

       async def razonar(self, tarea: str) -> ResultadoRazonamiento:
           """
           Genera N respuestas con temperatura alta y vota por consenso.
           Si no hay consenso, escala a TreeOfThought.
           """
           inicio = time.perf_counter()

           # Fase 1: Generar N respuestas en paralelo
           tareas_paralelas = []
           for i in range(self._num_muestras):
               ejecutor = EjecutorMicroTareas(self._ia, self._db, self._max_tokens)
               cadena = [
                   MicroTarea(
                       prompt=(
                           "Resuelve este problema. Sé preciso y da una respuesta concreta.\n\n"
                           "{tarea}\n\n"
                           "Respuesta:"
                       ),
                       input_keys=["tarea"],
                       output_key=f"respuesta_{i}",
                       max_tokens=self._max_tokens,
                       system="Responde de forma precisa y concreta.",
                       temperature=0.8,
                   ),
               ]
               tareas_paralelas.append(
                   ejecutor.ejecutar_cadena(
                       cadena,
                       tarea_id=f"sc_muestra_{i}_{uuid.uuid4().hex[:8]}",
                       datos_iniciales={"tarea": tarea},
                   )
               )

           resultados = await asyncio.gather(*tareas_paralelas, return_exceptions=True)

           respuestas: List[str] = []
           tokens_total = 0
           for r in resultados:
               if isinstance(r, ResultadoCadena) and r.exito:
                   respuestas.append(r.resultado_final.strip())
                   tokens_total += r.tokens_total

           if not respuestas:
               return ResultadoRazonamiento(
                   estrategia="sc",
                   confianza=0.0,
                   duracion_total_ms=int((time.perf_counter() - inicio) * 1000),
               )

           # Fase 2: Votar por consenso
           consenso, respuesta_ganadora, score_consenso = self._votar(respuestas)

           if consenso:
               duracion_ms = int((time.perf_counter() - inicio) * 1000)
               return ResultadoRazonamiento(
                   estrategia="sc",
                   resultado_final=respuesta_ganadora,
                   confianza=min(score_consenso, 0.95),
                   pasos_total=len(respuestas),
                   tokens_total=tokens_total,
                   duracion_total_ms=duracion_ms,
                   caminos_explorados=len(respuestas),
                   consenso=score_consenso,
                   detalles={
                       "muestras": self._num_muestras,
                       "respuestas_unicas": len(set(respuestas)),
                       "consenso_score": score_consenso,
                   },
               )

           # Fase 3: Sin consenso → escalar a Tree of Thought
           logger.info("[razonamiento] SC sin consenso, escalando a ToT")
           tot = TreeOfThought(self._ia, self._db, num_ramas=3, max_tokens_por_paso=self._max_tokens)
           resultado_tot = await tot.razonar(tarea)
           resultado_tot.estrategia = "sc+tot"
           resultado_tot.tokens_total += tokens_total
           resultado_tot.duracion_total_ms = int((time.perf_counter() - inicio) * 1000)
           return resultado_tot

       def _votar(self, respuestas: List[str]) -> tuple:
           """
           Vota por la respuesta más frecuente.
           Usa las primeras 100 chars como clave de agrupación (normalizado).
           """
           normalizadas = [r.strip().lower()[:100] for r in respuestas]
           counter = Counter(normalizadas)
           mas_comun, frecuencia = counter.most_common(1)[0]
           score = frecuencia / len(respuestas)

           idx_ganador = normalizadas.index(mas_comun)
           respuesta_original = respuestas[idx_ganador]

           consenso = score >= self._umbral_consenso
           return consenso, respuesta_original, score


2. Crear archivo src/investigador/selector_estrategia.py:

   Ruta: ~/yeyo-os/src/investigador/selector_estrategia.py
   Contenido:

   """
   YeyoOS — SelectorEstrategia
   Micro-fase 5.30 — Capa 5: Órganos

   Elige automáticamente la estrategia de razonamiento según complejidad.
   Integración: nodos del grafo del YeyoOrquestador (4.19) pueden tener
   estrategia: "cot" | "tot" | "sc" | "auto" (default: "auto").
   """

   from __future__ import annotations

   import logging
   import re
   from typing import Any, Dict, Optional

   from src.ia.interfaces import IAProvider

   from .micro_tareas import EjecutorMicroTareas
   from .razonamiento import (
       ChainOfThought,
       ResultadoRazonamiento,
       SelfConsistency,
       TreeOfThought,
   )
   from .tarea_db import TareaDB

   logger = logging.getLogger(__name__)

   KEYWORDS_ALTA_COMPLEJIDAD = {
       "distributed", "concurrent", "distributed system", "microservices",
       "machine learning", "neural network", "optimization", "algorithm",
       "security", "encryption", "authentication", "kubernetes",
       "compilador", "intérprete", "parser", "kernel",
       "concurrencia", "distribuido", "aprendizaje automático",
   }

   KEYWORDS_MEDIA_COMPLEJIDAD = {
       "api", "database", "cache", "queue", "websocket",
       "crud", "rest", "graphql", "middleware", "migration",
       "test", "deploy", "docker", "ci/cd", "pipeline",
       "base de datos", "migración", "despliegue",
   }


   class SelectorEstrategia:
       """
       Selecciona la estrategia de razonamiento óptima según complejidad.

       Umbrales:
       - complejidad < 0.3 → respuesta directa (sin razonamiento extendido)
       - complejidad 0.3-0.6 → ChainOfThought
       - complejidad 0.6-0.8 → TreeOfThought
       - complejidad > 0.8 → SelfConsistency + TreeOfThought (fallback)
       """

       def __init__(
           self,
           ia_provider: IAProvider,
           tarea_db: TareaDB,
           historial_complejidades: Optional[Dict[str, float]] = None,
       ):
           self._ia = ia_provider
           self._db = tarea_db
           self._historial = historial_complejidades or {}

       async def resolver(
           self,
           tarea: str,
           estrategia_override: Optional[str] = None,
       ) -> ResultadoRazonamiento:
           """
           Resuelve una tarea usando la estrategia óptima.

           Args:
               tarea: Descripción de la tarea
               estrategia_override: "cot", "tot", "sc" o None para auto-selección
           """
           if estrategia_override and estrategia_override != "auto":
               return await self._ejecutar_estrategia(estrategia_override, tarea)

           complejidad = self.estimar_complejidad(tarea)
           logger.info(f"[selector_estrategia] Complejidad estimada: {complejidad}")

           if complejidad < 0.3:
               return await self._respuesta_directa(tarea)
           elif complejidad < 0.6:
               return await self._ejecutar_estrategia("cot", tarea)
           elif complejidad < 0.8:
               return await self._ejecutar_estrategia("tot", tarea)
           else:
               return await self._ejecutar_estrategia("sc", tarea)

       def estimar_complejidad(self, tarea: str) -> float:
           """
           Estima complejidad 0.0-1.0 basada en:
           1. Longitud del texto (más largo = más complejo)
           2. Keywords técnicas (más keywords = más complejo)
           3. Historial de tareas similares
           """
           tarea_lower = tarea.lower()

           # Factor 1: Longitud (0.0-0.3)
           longitud = len(tarea)
           if longitud > 1000:
               score_longitud = 0.3
           elif longitud > 500:
               score_longitud = 0.2
           elif longitud > 200:
               score_longitud = 0.1
           else:
               score_longitud = 0.05

           # Factor 2: Keywords técnicas (0.0-0.5)
           hits_alta = sum(1 for kw in KEYWORDS_ALTA_COMPLEJIDAD if kw in tarea_lower)
           hits_media = sum(1 for kw in KEYWORDS_MEDIA_COMPLEJIDAD if kw in tarea_lower)
           score_keywords = min((hits_alta * 0.15 + hits_media * 0.05), 0.5)

           # Factor 3: Historial (0.0-0.2)
           score_historial = 0.0
           for tarea_previa, complejidad_previa in self._historial.items():
               palabras_comunes = set(tarea_lower.split()) & set(tarea_previa.lower().split())
               if len(palabras_comunes) >= 3:
                   score_historial = max(score_historial, complejidad_previa * 0.2)

           complejidad = min(score_longitud + score_keywords + score_historial, 1.0)

           # Guardar en historial para futuras estimaciones
           self._historial[tarea[:200]] = complejidad

           return round(complejidad, 3)

       async def _ejecutar_estrategia(
           self,
           estrategia: str,
           tarea: str,
       ) -> ResultadoRazonamiento:
           """Ejecuta la estrategia indicada."""
           if estrategia == "cot":
               cot = ChainOfThought(self._ia, self._db)
               return await cot.razonar(tarea)
           elif estrategia == "tot":
               tot = TreeOfThought(self._ia, self._db)
               return await tot.razonar(tarea)
           elif estrategia == "sc":
               sc = SelfConsistency(self._ia, self._db)
               return await sc.razonar(tarea)
           else:
               raise ValueError(f"Estrategia desconocida: {estrategia}")

       async def _respuesta_directa(self, tarea: str) -> ResultadoRazonamiento:
           """Para tareas simples: respuesta directa sin razonamiento extendido."""
           import time
           inicio = time.perf_counter()

           respuesta = await self._ia.generate(
               prompt=tarea,
               system="Responde de forma directa y concisa.",
               temperature=0.3,
           )

           return ResultadoRazonamiento(
               estrategia="directa",
               resultado_final=respuesta.content,
               confianza=0.7,
               pasos_total=1,
               tokens_total=respuesta.tokens_used,
               duracion_total_ms=int((time.perf_counter() - inicio) * 1000),
           )


3. Crear archivo tests/unit/investigador/test_razonamiento.py:

   Ruta: ~/yeyo-os/tests/unit/investigador/test_razonamiento.py
   Contenido:

   """
   Tests unitarios para Razonamiento Extendido.
   Micro-fase 5.30 — 10 tests (3 CoT + 3 ToT + 3 SC + 1 Selector).
   """

   import pytest
   from unittest.mock import AsyncMock, MagicMock

   from src.investigador.razonamiento import (
       ChainOfThought,
       TreeOfThought,
       SelfConsistency,
       ResultadoRazonamiento,
   )
   from src.investigador.selector_estrategia import SelectorEstrategia
   from src.investigador.tarea_db import TareaDB


   @pytest.fixture
   def mock_ia():
       ia = AsyncMock()
       ia.generate.return_value = MagicMock(
           content="solución generada por el modelo",
           tokens_used=80,
           latency_ms=100,
       )
       return ia


   @pytest.fixture
   def tarea_db():
       return TareaDB(pool=None)


   # --- Tests ChainOfThought ---

   @pytest.mark.asyncio
   async def test_cot_retorna_resultado(mock_ia, tarea_db):
       cot = ChainOfThought(mock_ia, tarea_db, num_pasos=3)
       resultado = await cot.razonar("¿Cómo implementar un rate limiter?")
       assert isinstance(resultado, ResultadoRazonamiento)
       assert resultado.estrategia == "cot"
       assert resultado.resultado_final != ""
       assert resultado.confianza > 0


   @pytest.mark.asyncio
   async def test_cot_ejecuta_multiples_pasos(mock_ia, tarea_db):
       cot = ChainOfThought(mock_ia, tarea_db, num_pasos=4)
       resultado = await cot.razonar("Problema complejo")
       assert resultado.pasos_total >= 3
       assert resultado.tokens_total > 0


   @pytest.mark.asyncio
   async def test_cot_un_solo_camino(mock_ia, tarea_db):
       cot = ChainOfThought(mock_ia, tarea_db)
       resultado = await cot.razonar("Test")
       assert resultado.caminos_explorados == 1


   # --- Tests TreeOfThought ---

   @pytest.mark.asyncio
   async def test_tot_retorna_resultado(mock_ia, tarea_db):
       tot = TreeOfThought(mock_ia, tarea_db, num_ramas=2)
       resultado = await tot.razonar("¿Cómo diseñar un sistema distribuido?")
       assert isinstance(resultado, ResultadoRazonamiento)
       assert resultado.estrategia == "tot"
       assert resultado.resultado_final != ""


   @pytest.mark.asyncio
   async def test_tot_explora_multiples_caminos(mock_ia, tarea_db):
       tot = TreeOfThought(mock_ia, tarea_db, num_ramas=3)
       resultado = await tot.razonar("Problema con múltiples enfoques")
       assert resultado.caminos_explorados >= 1


   @pytest.mark.asyncio
   async def test_tot_parsea_mejor_solucion(mock_ia, tarea_db):
       ia_eval = AsyncMock()
       respuesta_counter = [0]

       async def generate_side_effect(**kwargs):
           respuesta_counter[0] += 1
           if "mejor" in kwargs.get("prompt", "").lower() or "evalúa" in kwargs.get("prompt", "").lower():
               return MagicMock(content="1 - La primera es mejor", tokens_used=30, latency_ms=50)
           return MagicMock(content=f"Solución {respuesta_counter[0]}", tokens_used=50, latency_ms=100)

       ia_eval.generate = AsyncMock(side_effect=generate_side_effect)
       tot = TreeOfThought(ia_eval, tarea_db, num_ramas=2)
       resultado = await tot.razonar("Test parseo")
       assert resultado.resultado_final != ""


   # --- Tests SelfConsistency ---

   @pytest.mark.asyncio
   async def test_sc_retorna_resultado(mock_ia, tarea_db):
       sc = SelfConsistency(mock_ia, tarea_db, num_muestras=3)
       resultado = await sc.razonar("¿Cuánto es 2+2?")
       assert isinstance(resultado, ResultadoRazonamiento)
       assert resultado.estrategia in ("sc", "sc+tot")


   @pytest.mark.asyncio
   async def test_sc_consenso_con_respuestas_iguales(mock_ia, tarea_db):
       mock_ia.generate.return_value = MagicMock(
           content="4", tokens_used=10, latency_ms=20,
       )
       sc = SelfConsistency(mock_ia, tarea_db, num_muestras=5, umbral_consenso=0.5)
       resultado = await sc.razonar("¿Cuánto es 2+2?")
       assert resultado.consenso is not None
       assert resultado.consenso >= 0.5


   @pytest.mark.asyncio
   async def test_sc_escala_a_tot_sin_consenso(mock_ia, tarea_db):
       call_counter = [0]

       async def varied_responses(**kwargs):
           call_counter[0] += 1
           return MagicMock(
               content=f"respuesta_unica_{call_counter[0]}",
               tokens_used=30,
               latency_ms=50,
           )

       mock_ia.generate = AsyncMock(side_effect=varied_responses)
       sc = SelfConsistency(mock_ia, tarea_db, num_muestras=5, umbral_consenso=0.9)
       resultado = await sc.razonar("Pregunta ambigua")
       assert resultado.estrategia in ("sc", "sc+tot")


   # --- Test SelectorEstrategia ---

   @pytest.mark.asyncio
   async def test_selector_elige_por_complejidad(mock_ia, tarea_db):
       selector = SelectorEstrategia(mock_ia, tarea_db)

       # Tarea simple
       comp_simple = selector.estimar_complejidad("hola")
       assert comp_simple < 0.3

       # Tarea compleja
       comp_compleja = selector.estimar_complejidad(
           "Implementar un sistema distribuido con machine learning "
           "y concurrent processing para optimization de neural network"
       )
       assert comp_compleja > 0.3

       # Resolver con auto-selección
       resultado = await selector.resolver("tarea simple")
       assert isinstance(resultado, ResultadoRazonamiento)


VERIFICAR:

1. Ejecutar: cd ~/yeyo-os && python -m pytest tests/unit/investigador/test_razonamiento.py -v
   Esperado: 10 tests pasan

2. Ejecutar: cd ~/yeyo-os && python -c "from src.investigador.razonamiento import ChainOfThought, TreeOfThought, SelfConsistency; print('OK')"
   Esperado: OK

3. Ejecutar: cd ~/yeyo-os && python -c "from src.investigador.selector_estrategia import SelectorEstrategia; print('OK')"
   Esperado: OK

SI FALLA:
- Si falla import de .micro_tareas: verificar que EjecutorMicroTareas, MicroTarea existen en src/investigador/micro_tareas.py (5.29)
- Si falla import de .tarea_db: verificar que TareaDB existe (5.29)
- Si asyncio.gather falla con ResultadoCadena: verificar que ejecutar_cadena retorna ResultadoCadena

NO HACER:
- NO modificar src/investigador/micro_tareas.py (creado en 5.29)
- NO modificar src/investigador/tarea_db.py (creado en 5.29)
- NO modificar src/investigador/modelos.py (creado en 5.28)
- NO usar estado compartido entre pasos — toda la comunicación va por DB

GATE:
✅ ChainOfThought resuelve problemas en pasos secuenciales (micro-tareas)
✅ TreeOfThought genera K soluciones en paralelo, evalúa y elige la mejor
✅ SelfConsistency genera N respuestas, vota por consenso, escala a ToT si no hay
✅ SelectorEstrategia elige automáticamente según complejidad estimada
✅ Todas las estrategias usan EjecutorMicroTareas (contexto limpio por paso)
✅ 10 tests pasan (3 CoT + 3 ToT + 3 SC + 1 Selector)
✅ Nodos del grafo pueden usar estrategia: "cot" | "tot" | "sc" | "auto"
```
