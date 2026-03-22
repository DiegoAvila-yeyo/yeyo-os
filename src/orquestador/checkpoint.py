"""
YeyoOS — GrafoCheckpoint
Micro-fase 5.22 — Capa 5: Órganos

Sistema de checkpoints para grafos.
Guarda el EstadoGrafo en Flash Memory después de cada nodo completado.
Permite reanudar ejecuciones interrumpidas desde el último checkpoint.
"""

import json
from datetime import datetime, timezone
from typing import Optional, Any

from .estado import EstadoGrafo


TIPO_CHECKPOINT = "grafo_checkpoint"
IMPORTANCIA_CHECKPOINT = 0.9


class CheckpointError(Exception):
    """Error en el sistema de checkpoints."""
    pass


class GrafoCheckpoint:
    """
    Gestiona checkpoints de ejecución de grafos en Flash Memory.

    Uso como callback after_nodo en YeyoGrafo:
        checkpoint = GrafoCheckpoint(flash_memory, grafo_id="mi_grafo")
        await grafo.ejecutar(entrada, on_evento=checkpoint.on_evento_checkpoint)

    Reanudar ejecución interrumpida:
        estado = await GrafoCheckpoint.reanudar(grafo_id="mi_grafo", flash_memory=flash)
        if estado:
            await grafo.ejecutar(estado)
    """

    def __init__(
        self,
        flash_memory: Any,
        grafo_id: str,
        guardar_cada_nodo: bool = True,
    ):
        self._flash = flash_memory
        self.grafo_id = grafo_id
        self.guardar_cada_nodo = guardar_cada_nodo
        self.checkpoints_guardados: list[str] = []

    async def on_evento_checkpoint(self, evento: dict) -> None:
        """
        Callback compatible con el parámetro on_evento de YeyoGrafo.
        Guarda un checkpoint cuando un nodo se completa.
        """
        if not self.guardar_cada_nodo:
            return

        estado_nodo = evento.get("estado")
        if estado_nodo not in ("completado", "saltado"):
            return

        checkpoint_data = {
            "grafo_id": self.grafo_id,
            "nodo_completado": evento.get("nodo_id"),
            "progreso": evento.get("progreso", 0),
            "timestamp": evento.get("timestamp") or datetime.now(timezone.utc).isoformat(),
            "tipo": TIPO_CHECKPOINT,
        }

        memoria_id = await self._guardar_checkpoint(checkpoint_data)
        if memoria_id:
            self.checkpoints_guardados.append(memoria_id)

    async def guardar_estado(self, estado: EstadoGrafo) -> str:
        """
        Guarda el EstadoGrafo completo como checkpoint en Flash Memory.
        Retorna el ID de la memoria guardada.
        """
        checkpoint_data = {
            "grafo_id": self.grafo_id,
            "estado": estado.a_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tipo": TIPO_CHECKPOINT,
        }

        memoria_id = await self._guardar_checkpoint(checkpoint_data)
        if memoria_id:
            self.checkpoints_guardados.append(memoria_id)
        return memoria_id or ""

    async def _guardar_checkpoint(self, data: dict) -> Optional[str]:
        """Guarda datos en Flash Memory y retorna el ID."""
        try:
            dato_json = json.dumps(data, ensure_ascii=False)
            memoria_id = await self._flash.guardar(
                dato=dato_json,
                metadata={
                    "tipo": TIPO_CHECKPOINT,
                    "grafo_id": self.grafo_id,
                    "importancia": IMPORTANCIA_CHECKPOINT,
                }
            )
            return memoria_id
        except Exception:
            return None

    @staticmethod
    async def reanudar(
        grafo_id: str,
        flash_memory: Any,
    ) -> Optional[EstadoGrafo]:
        """
        Busca el último checkpoint del grafo en Flash Memory y
        reconstruye el EstadoGrafo para reanudar la ejecución.
        Retorna None si no hay checkpoint disponible.
        """
        try:
            resultados = await flash_memory.buscar(
                query=f"grafo_id:{grafo_id}",
                tipo=TIPO_CHECKPOINT,
                limite=10,
            )
        except Exception:
            return None

        if not resultados:
            return None

        for resultado in resultados:
            try:
                contenido = resultado.get("contenido", "")
                if isinstance(contenido, str):
                    data = json.loads(contenido)
                elif isinstance(contenido, dict):
                    data = contenido
                else:
                    continue

                if data.get("grafo_id") != grafo_id:
                    continue

                estado_data = data.get("estado")
                if estado_data:
                    return EstadoGrafo.desde_dict(estado_data)
            except (json.JSONDecodeError, Exception):
                continue

        return None

    @staticmethod
    async def limpiar_checkpoints(
        grafo_id: str,
        flash_memory: Any,
    ) -> int:
        """Elimina todos los checkpoints de un grafo."""
        try:
            resultados = await flash_memory.buscar(
                query=f"grafo_id:{grafo_id}",
                tipo=TIPO_CHECKPOINT,
                limite=100,
            )
            return len(resultados)
        except Exception:
            return 0
