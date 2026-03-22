"""
YeyoOS — TareaDB
Micro-fase 5.29 — Capa 5: Órganos

CRUD contra tabla investigacion_pasos + almacenamiento key-value
para datos intermedios de micro-tareas.
Es el "pegamento" entre pasos: cada paso lee y escribe aquí.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from .modelos import PasoInvestigacion

logger = logging.getLogger(__name__)


class TareaDBError(Exception):
    """Error en TareaDB."""
    pass


class TareaDB:
    """
    Almacena y recupera datos intermedios de micro-tareas.

    Usa dos mecanismos:
    1. Tabla investigacion_pasos (PostgreSQL) para tracking de pasos
    2. Dict en memoria como store key-value para datos entre pasos
       (en producción se puede reemplazar por Redis o tabla auxiliar)

    El store key-value usa el patrón: tarea_id:key -> value
    """

    def __init__(self, pool: Optional[Any] = None):
        """
        Args:
            pool: asyncpg connection pool (opcional — si None, solo usa store en memoria)
        """
        self._pool = pool
        self._store: Dict[str, str] = {}

    async def guardar_paso(
        self,
        tarea_id: str,
        paso: int,
        tipo: str,
        input_resumen: str,
        output_resumen: str,
        tokens: int = 0,
        duracion: int = 0,
        confianza: float = 0.0,
    ) -> None:
        """Guarda un paso en la tabla investigacion_pasos."""
        if self._pool:
            try:
                async with self._pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO investigacion_pasos
                        (tarea_id, paso_numero, tipo, input_resumen, output_resumen,
                         tokens_usados, duracion_ms, confianza)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        """,
                        tarea_id, paso, tipo, input_resumen, output_resumen,
                        tokens, duracion, confianza,
                    )
            except Exception as e:
                logger.error(f"[tarea_db] Error guardando paso: {e}")
        else:
            logger.debug(f"[tarea_db] Pool no disponible, paso {paso} solo en memoria")

    async def leer_paso(self, tarea_id: str, paso_numero: int) -> Optional[PasoInvestigacion]:
        """Lee un paso específico de la tabla investigacion_pasos."""
        if self._pool:
            try:
                async with self._pool.acquire() as conn:
                    row = await conn.fetchrow(
                        """
                        SELECT paso_numero, tipo, input_resumen, output_resumen,
                               tokens_usados, duracion_ms, confianza
                        FROM investigacion_pasos
                        WHERE tarea_id = $1 AND paso_numero = $2
                        """,
                        tarea_id, paso_numero,
                    )
                    if row:
                        return PasoInvestigacion(
                            numero=row["paso_numero"],
                            tipo=row["tipo"],
                            input_resumen=row["input_resumen"] or "",
                            output_resumen=row["output_resumen"] or "",
                            tokens=row["tokens_usados"] or 0,
                            duracion_ms=row["duracion_ms"] or 0,
                            confianza=row["confianza"] or 0.0,
                        )
            except Exception as e:
                logger.error(f"[tarea_db] Error leyendo paso: {e}")
        return None

    async def leer_resumen(self, tarea_id: str) -> str:
        """
        Genera un resumen comprimido de todos los pasos de una tarea.
        Útil para inyectar contexto mínimo en pasos posteriores.
        """
        if self._pool:
            try:
                async with self._pool.acquire() as conn:
                    rows = await conn.fetch(
                        """
                        SELECT paso_numero, tipo, output_resumen
                        FROM investigacion_pasos
                        WHERE tarea_id = $1
                        ORDER BY paso_numero
                        """,
                        tarea_id,
                    )
                    if rows:
                        partes = []
                        for row in rows:
                            partes.append(
                                f"Paso {row['paso_numero']} ({row['tipo']}): "
                                f"{(row['output_resumen'] or '')[:100]}"
                            )
                        return "\n".join(partes)
            except Exception as e:
                logger.error(f"[tarea_db] Error leyendo resumen: {e}")

        store_keys = [k for k in self._store if k.startswith(f"{tarea_id}:")]
        if store_keys:
            partes = [f"{k.split(':', 1)[1]}: {self._store[k][:100]}" for k in sorted(store_keys)]
            return "\n".join(partes)
        return ""

    async def leer_resultado_final(self, tarea_id: str) -> str:
        """Lee el resultado del último paso de una tarea."""
        if self._pool:
            try:
                async with self._pool.acquire() as conn:
                    row = await conn.fetchrow(
                        """
                        SELECT output_resumen
                        FROM investigacion_pasos
                        WHERE tarea_id = $1
                        ORDER BY paso_numero DESC
                        LIMIT 1
                        """,
                        tarea_id,
                    )
                    if row:
                        return row["output_resumen"] or ""
            except Exception as e:
                logger.error(f"[tarea_db] Error leyendo resultado final: {e}")

        store_keys = sorted(
            [k for k in self._store if k.startswith(f"{tarea_id}:")],
            reverse=True,
        )
        if store_keys:
            return self._store[store_keys[0]]
        return ""

    async def guardar_dato(self, tarea_id: str, key: str, value: str) -> None:
        """Guarda un dato key-value para una tarea (pegamento entre micro-tareas)."""
        store_key = f"{tarea_id}:{key}"
        self._store[store_key] = value
        logger.debug(f"[tarea_db] Guardado {store_key} ({len(value)} chars)")

    async def leer_dato(self, tarea_id: str, key: str) -> Optional[str]:
        """Lee un dato key-value de una tarea."""
        store_key = f"{tarea_id}:{key}"
        valor = self._store.get(store_key)
        if valor is not None:
            logger.debug(f"[tarea_db] Leído {store_key} ({len(valor)} chars)")
        return valor

    async def listar_datos(self, tarea_id: str) -> Dict[str, str]:
        """Lista todos los datos key-value de una tarea."""
        prefix = f"{tarea_id}:"
        return {
            k[len(prefix):]: v
            for k, v in self._store.items()
            if k.startswith(prefix)
        }

    async def limpiar_tarea(self, tarea_id: str) -> None:
        """Limpia todos los datos en memoria de una tarea."""
        keys_to_remove = [k for k in self._store if k.startswith(f"{tarea_id}:")]
        for k in keys_to_remove:
            del self._store[k]
        logger.debug(f"[tarea_db] Limpiados {len(keys_to_remove)} datos de {tarea_id}")
