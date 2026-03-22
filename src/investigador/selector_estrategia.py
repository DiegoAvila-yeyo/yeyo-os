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
