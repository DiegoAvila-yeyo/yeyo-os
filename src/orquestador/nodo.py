"""
YeyoOS — Nodo Base y formas de definición
Micro-fase 4.15 — Capa 4: Sistema Nervioso

Tres formas de definir nodos en el YeyoOrquestador:
1. Decorador @nodo(id, timeout, max_intentos)
2. Herencia de clase Nodo (NodoClase)
3. Instancia inline Nodo(id, fn=lambda)
"""

import asyncio
import functools
from abc import ABC, abstractmethod
from typing import Callable, Optional, Awaitable, Union

from .estado import EstadoGrafo, EstadoGrafoError


FnNodo = Callable[[EstadoGrafo], Awaitable[EstadoGrafo]]


class NodoError(Exception):
    """Error durante la ejecución de un nodo."""
    def __init__(self, nodo_id: str, mensaje: str, causa: Optional[Exception] = None):
        super().__init__(f"[{nodo_id}] {mensaje}")
        self.nodo_id = nodo_id
        self.mensaje = mensaje
        self.causa = causa


class NodoTimeoutError(NodoError):
    """El nodo excedió su tiempo máximo de ejecución."""
    pass


class Nodo(ABC):
    """Clase base abstracta para nodos del YeyoOrquestador."""

    id: str = ""
    timeout: float = 30.0
    max_intentos: int = 1

    def __init__(
        self,
        id: Optional[str] = None,
        timeout: Optional[float] = None,
        max_intentos: Optional[int] = None,
        fn: Optional[FnNodo] = None,
    ):
        if id is not None:
            self.id = id
        if timeout is not None:
            self.timeout = timeout
        if max_intentos is not None:
            self.max_intentos = max_intentos
        if fn is not None:
            self._fn_override = fn
        else:
            self._fn_override = None

        if not self.id:
            raise ValueError("Nodo debe tener un 'id' no vacío")
        if self.timeout <= 0:
            raise ValueError(f"timeout debe ser positivo, recibido: {self.timeout}")
        if self.max_intentos < 1:
            raise ValueError(f"max_intentos debe ser >= 1, recibido: {self.max_intentos}")

    async def ejecutar(self, estado: EstadoGrafo) -> EstadoGrafo:
        """Ejecuta la lógica del nodo."""
        if self._fn_override is not None:
            return await self._llamar_fn(self._fn_override, estado)
        raise NotImplementedError(
            f"Nodo '{self.id}' debe sobreescribir ejecutar() o pasar fn= en el constructor"
        )

    async def _llamar_fn(self, fn: FnNodo, estado: EstadoGrafo) -> EstadoGrafo:
        """Llama la función, soportando tanto async como sync (lambda)."""
        resultado = fn(estado)
        if asyncio.iscoroutine(resultado):
            return await resultado
        return resultado

    async def ejecutar_con_timeout(self, estado: EstadoGrafo) -> EstadoGrafo:
        """Ejecuta el nodo respetando el timeout configurado."""
        try:
            return await asyncio.wait_for(
                self.ejecutar(estado),
                timeout=self.timeout
            )
        except asyncio.TimeoutError:
            raise NodoTimeoutError(
                self.id,
                f"Timeout de {self.timeout}s excedido"
            )

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"id={self.id!r}, "
            f"timeout={self.timeout}s, "
            f"max_intentos={self.max_intentos})"
        )


class NodoFuncion(Nodo):
    """Nodo creado a partir de una función async (forma 1: decorador @nodo)."""

    def __init__(
        self,
        id: str,
        fn: FnNodo,
        timeout: float = 30.0,
        max_intentos: int = 1,
        nombre_display: Optional[str] = None,
    ):
        super().__init__(id=id, timeout=timeout, max_intentos=max_intentos)
        self._fn = fn
        self.nombre_display = nombre_display or id

    async def ejecutar(self, estado: EstadoGrafo) -> EstadoGrafo:
        return await self._llamar_fn(self._fn, estado)


class NodoInline(Nodo):
    """Nodo creado inline con una función lambda (forma 3: inline)."""

    def __init__(
        self,
        id: str,
        fn: Union[FnNodo, Callable[[EstadoGrafo], EstadoGrafo]],
        timeout: float = 30.0,
        max_intentos: int = 1,
    ):
        super().__init__(id=id, timeout=timeout, max_intentos=max_intentos, fn=fn)


def nodo(
    id: str,
    timeout: float = 30.0,
    max_intentos: int = 1,
) -> Callable[[FnNodo], NodoFuncion]:
    """Decorador para crear NodoFuncion desde una función async."""
    if not id:
        raise ValueError("El decorador @nodo requiere un id no vacío")

    def decorator(fn: FnNodo) -> NodoFuncion:
        nodo_func = NodoFuncion(
            id=id,
            fn=fn,
            timeout=timeout,
            max_intentos=max_intentos,
            nombre_display=fn.__name__,
        )
        functools.update_wrapper(nodo_func, fn)
        return nodo_func

    return decorator
