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

SCORE_MINIMO_ACEPTABLE = 0.3  # Candidatos con score < esto son rechazados

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

            # Validate minimum requirement: código no vacío
            if not candidato.codigo or not candidato.codigo.strip():
                ev.score_final = 0.0
                ev.razones.append("código_vacío")
                evaluaciones.append(ev)
                continue

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

            # Ensure score is in valid range [0.0, 1.0]
            ev.score_final = max(0.0, min(1.0, ev.score_final))

            # Log reason if score very low
            if ev.score_final < SCORE_MINIMO_ACEPTABLE:
                ev.razones.append(f"score_muy_bajo_{ev.score_final}")

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
        meta = candidato.metadata or {}
        lenguaje = str(meta.get("lenguaje", "")).lower() if meta.get("lenguaje") else ""
        tags = [t.lower() for t in meta.get("tags", []) if t]
        topics = [t.lower() for t in meta.get("topics", []) if t]
        texto = candidato.codigo.lower()

        coincidencias = 0
        for tech in self._stack:
            if tech in lenguaje or tech in tags or tech in topics or tech in texto:
                coincidencias += 1

        if coincidencias == 0:
            # No stack match, but text analysis is still useful
            return 0.4
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
        meta = candidato.metadata or {}
        estrellas = meta.get("estrellas", 0)
        votos = meta.get("votos", 0)
        
        # Handle non-numeric values
        try:
            estrellas = int(estrellas) if estrellas else 0
            votos = int(votos) if votos else 0
        except (ValueError, TypeError):
            estrellas = 0
            votos = 0
        
        valor = max(estrellas, votos)

        if valor >= 1000:
            return 1.0
        if valor >= 100:
            return 0.8
        if valor >= 50:
            return 0.6
        if valor >= 10:
            return 0.4
        if valor > 0:
            return 0.2
        # No popularity data = neutral score (not penalized)
        return 0.5

    def _evaluar_frescura(self, candidato: ResultadoBusqueda) -> float:
        """Score basado en qué tan reciente es el contenido."""
        meta = candidato.metadata or {}
        actualizado = str(meta.get("actualizado", "")) if meta.get("actualizado") else ""
        
        if not actualizado:
            # No timestamp = neutral (assume recent)
            return 0.5
        
        if "2025" in actualizado:
            return 1.0
        if "2024" in actualizado:
            return 0.8
        if "2023" in actualizado:
            return 0.5
        return 0.3
