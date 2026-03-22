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
