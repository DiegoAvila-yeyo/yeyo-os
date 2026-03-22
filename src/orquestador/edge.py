"""
YeyoOS — Edge y condiciones de flujo
Micro-fase 4.16 — Capa 4: Sistema Nervioso

Define cómo fluye el EstadoGrafo entre nodos:
- EdgeDirecto: siempre va al mismo nodo destino
- EdgeCondicional: una función decide el nodo destino
- @edge(desde): decorador para crear EdgeCondicional
"""

import asyncio
import functools
from abc import ABC, abstractmethod
from typing import Callable, Optional, Awaitable, Union

from .estado import EstadoGrafo


# Constante especial para indicar fin del grafo
FIN_GRAFO = "__fin__"


class EdgeError(Exception):
    """Error en la configuración o evaluación de un edge."""
    pass


# Tipo para la función de condición de un edge
FnCondicion = Union[
    Callable[[EstadoGrafo], str],
    Callable[[EstadoGrafo], Awaitable[str]]
]


class Edge(ABC):
    """
    Clase base abstracta para edges del YeyoGrafo.
    Un edge define la transición entre un nodo origen y un nodo destino.
    """

    def __init__(self, desde: str):
        if not desde:
            raise EdgeError("Edge debe tener un 'desde' no vacío")
        self.desde = desde

    @abstractmethod
    async def evaluar(self, estado: EstadoGrafo) -> str:
        """
        Evalúa el edge y retorna el ID del nodo destino.
        Retorna FIN_GRAFO si la ejecución debe terminar.
        """
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(desde={self.desde!r})"


class EdgeDirecto(Edge):
    """
    Edge que siempre va al mismo nodo destino.
    Uso: grafo.edge("nodo_a", "nodo_b")
    """

    def __init__(self, desde: str, hasta: str):
        super().__init__(desde)
        if not hasta:
            raise EdgeError("EdgeDirecto debe tener un 'hasta' no vacío")
        self.hasta = hasta

    async def evaluar(self, estado: EstadoGrafo) -> str:
        return self.hasta

    def __repr__(self) -> str:
        return f"EdgeDirecto({self.desde!r} → {self.hasta!r})"


class EdgeCondicional(Edge):
    """
    Edge cuyo destino depende de una función que evalúa el EstadoGrafo.
    La función puede ser sync o async.

    Uso:
        edge = EdgeCondicional(
            desde="evaluar",
            fn=lambda estado: "aprobado" if estado.contexto["score"] >= 0.8 else "rechazado"
        )

    O con decorador @edge:
        @edge(desde="evaluar")
        async def siguiente(estado: EstadoGrafo) -> str:
            return "aprobado" if estado.contexto["score"] >= 0.8 else "rechazado"
    """

    def __init__(self, desde: str, fn: FnCondicion, nombre: Optional[str] = None):
        super().__init__(desde)
        if fn is None:
            raise EdgeError("EdgeCondicional requiere una función de condición")
        self._fn = fn
        self.nombre = nombre or getattr(fn, "__name__", "condicional")

    async def evaluar(self, estado: EstadoGrafo) -> str:
        """Evalúa la función de condición (sync o async) y retorna el nodo destino."""
        resultado = self._fn(estado)
        if asyncio.iscoroutine(resultado):
            destino = await resultado
        else:
            destino = resultado

        if not isinstance(destino, str):
            raise EdgeError(
                f"La función del edge '{self.desde}' debe retornar un string (nodo ID), "
                f"recibido: {type(destino).__name__}"
            )
        if not destino:
            raise EdgeError(
                f"La función del edge '{self.desde}' retornó un string vacío"
            )
        return destino

    def __repr__(self) -> str:
        return f"EdgeCondicional({self.desde!r} → fn={self.nombre!r})"


def edge(desde: str) -> Callable[[FnCondicion], EdgeCondicional]:
    """
    Decorador para crear EdgeCondicional desde una función.

    Uso:
        @edge(desde="evaluar_calidad")
        async def siguiente_nodo(estado: EstadoGrafo) -> str:
            score = estado.contexto.get("score", 0)
            if score >= 0.8:
                return "upscale"
            elif score >= 0.5:
                return "refinar"
            else:
                return "generar_imagen"
    """
    if not desde:
        raise EdgeError("El decorador @edge requiere un 'desde' no vacío")

    def decorator(fn: FnCondicion) -> EdgeCondicional:
        edge_cond = EdgeCondicional(desde=desde, fn=fn, nombre=fn.__name__)
        functools.update_wrapper(edge_cond, fn)
        return edge_cond

    return decorator
