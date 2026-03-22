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
