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
