"""
YeyoOS — EstadoGrafo
Micro-fase 4.14 — Capa 4: Sistema Nervioso

Objeto central que fluye entre todos los nodos del YeyoOrquestador.
Serializable a JSON para checkpoints en Flash Memory.
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional
from copy import deepcopy


class EstadoGrafoError(Exception):
    """Error en la gestión de EstadoGrafo."""
    pass


@dataclass
class EstadoGrafo:
    """
    Objeto que fluye entre todos los nodos del YeyoOrquestador.

    - entrada: Input original (inmutable conceptualmente)
    - salida: Output acumulado por los nodos
    - contexto: Datos compartidos entre nodos (metadatos, scores, etc.)
    - nodo_actual: ID del nodo que se está ejecutando ahora mismo
    - historial: Lista ordenada de IDs de nodos ejecutados exitosamente
    - intentos: Conteo de intentos por nodo {nodo_id: n}
    - inicio: Timestamp de inicio de la ejecución del grafo
    - errores: Lista de errores con contexto {nodo_id, mensaje, timestamp}
    - memoria_ids: IDs de memorias creadas en Flash Memory durante la ejecución
    """

    entrada: dict
    salida: dict = field(default_factory=dict)
    contexto: dict = field(default_factory=dict)
    nodo_actual: str = ""
    historial: list = field(default_factory=list)
    intentos: dict = field(default_factory=dict)
    inicio: Optional[datetime] = field(default=None)
    errores: list = field(default_factory=list)
    memoria_ids: list = field(default_factory=list)

    def __post_init__(self):
        if self.inicio is None:
            self.inicio = datetime.now(timezone.utc)
        if not isinstance(self.entrada, dict):
            raise EstadoGrafoError("'entrada' debe ser un diccionario")

    def registrar_nodo_completado(self, nodo_id: str) -> None:
        """Registra un nodo como completado en el historial."""
        if not nodo_id:
            raise EstadoGrafoError("nodo_id no puede estar vacío")
        self.historial.append(nodo_id)

    def marcar_nodo_actual(self, nodo_id: str) -> None:
        """Marca el nodo que se está ejecutando actualmente."""
        self.nodo_actual = nodo_id

    def nodo_fue_ejecutado(self, nodo_id: str) -> bool:
        """Retorna True si el nodo ya fue ejecutado exitosamente."""
        return nodo_id in self.historial

    def incrementar_intento(self, nodo_id: str) -> int:
        """Incrementa el contador de intentos para un nodo. Retorna el nuevo conteo."""
        self.intentos[nodo_id] = self.intentos.get(nodo_id, 0) + 1
        return self.intentos[nodo_id]

    def obtener_intentos(self, nodo_id: str) -> int:
        """Retorna el número de intentos para un nodo (0 si nunca intentado)."""
        return self.intentos.get(nodo_id, 0)

    def registrar_error(self, nodo_id: str, mensaje: str, detalle: Any = None) -> None:
        """Registra un error ocurrido en un nodo."""
        self.errores.append({
            "nodo_id": nodo_id,
            "mensaje": str(mensaje),
            "detalle": str(detalle) if detalle is not None else None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def tiene_errores(self) -> bool:
        """Retorna True si hay algún error registrado."""
        return len(self.errores) > 0

    def ultimo_error(self) -> Optional[dict]:
        """Retorna el último error registrado, o None si no hay errores."""
        return self.errores[-1] if self.errores else None

    def registrar_memoria(self, memoria_id: str) -> None:
        """Registra el ID de una memoria creada en Flash Memory."""
        if memoria_id not in self.memoria_ids:
            self.memoria_ids.append(memoria_id)

    def a_dict(self) -> dict:
        """Serializa el estado a un diccionario JSON-compatible."""
        data = asdict(self)
        if self.inicio is not None:
            data["inicio"] = self.inicio.isoformat()
        return data

    def a_json(self) -> str:
        """Serializa el estado a JSON string."""
        return json.dumps(self.a_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def desde_dict(cls, data: dict) -> "EstadoGrafo":
        """Reconstruye un EstadoGrafo desde un diccionario (checkpoint)."""
        data = dict(data)
        inicio_raw = data.pop("inicio", None)
        estado = cls(**data)
        if inicio_raw:
            if isinstance(inicio_raw, str):
                estado.inicio = datetime.fromisoformat(inicio_raw)
            elif isinstance(inicio_raw, datetime):
                estado.inicio = inicio_raw
        return estado

    @classmethod
    def desde_json(cls, json_str: str) -> "EstadoGrafo":
        """Reconstruye un EstadoGrafo desde un JSON string (checkpoint)."""
        data = json.loads(json_str)
        if not isinstance(data, dict):
            raise EstadoGrafoError("El JSON debe representar un diccionario")
        return cls.desde_dict(data)

    def clonar(self) -> "EstadoGrafo":
        """Retorna una copia profunda del estado."""
        return self.desde_dict(self.a_dict())

    def duracion_segundos(self) -> float:
        """Retorna la duración en segundos desde el inicio."""
        if self.inicio is None:
            return 0.0
        ahora = datetime.now(timezone.utc)
        delta = ahora - self.inicio
        return delta.total_seconds()

    def __repr__(self) -> str:
        return (
            f"EstadoGrafo(nodo_actual={self.nodo_actual!r}, "
            f"historial={self.historial}, "
            f"errores={len(self.errores)})"
        )
