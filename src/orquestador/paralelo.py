"""
YeyoOS — NodoParalelo
Micro-fase 4.18 — Capa 4: Sistema Nervioso

Ejecuta múltiples nodos en paralelo con asyncio.gather.
El tiempo total = tiempo del nodo más lento (no la suma).
"""

import asyncio
from typing import Callable, List, Optional

from .estado import EstadoGrafo
from .nodo import Nodo, NodoError


class NodoParalelo(Nodo):
    """
    Nodo que ejecuta múltiples nodos en paralelo con asyncio.gather.

    Cada nodo recibe una copia del EstadoGrafo (son independientes).
    Al finalizar, la función combinar fusiona todos los resultados.

    Modos de error:
    - fail_fast (default): si cualquier nodo falla, NodoParalelo falla
    - continue_on_error: continúa aunque algún nodo falle, registra errores en contexto
    """

    def __init__(
        self,
        id: str,
        nodos: List[Nodo],
        combinar: Optional[Callable[[List[EstadoGrafo]], dict]] = None,
        timeout: float = 120.0,
        max_intentos: int = 1,
        modo_error: str = "fail_fast",
    ):
        super().__init__(id=id, timeout=timeout, max_intentos=max_intentos)
        if not nodos:
            raise ValueError(f"NodoParalelo '{id}' debe tener al menos un nodo")
        if modo_error not in ("fail_fast", "continue_on_error"):
            raise ValueError(
                f"modo_error debe ser 'fail_fast' o 'continue_on_error', "
                f"recibido: '{modo_error}'"
            )
        self._nodos_paralelos = nodos
        self._combinar = combinar
        self.modo_error = modo_error

    async def ejecutar(self, estado: EstadoGrafo) -> EstadoGrafo:
        """
        Ejecuta todos los nodos en paralelo.
        Cada nodo recibe una copia del estado de entrada.
        """
        # Crear copias del estado para cada nodo
        estados_entrada = [estado.clonar() for _ in self._nodos_paralelos]

        if self.modo_error == "fail_fast":
            return await self._ejecutar_fail_fast(estado, estados_entrada)
        else:
            return await self._ejecutar_continue_on_error(estado, estados_entrada)

    async def _ejecutar_fail_fast(
        self,
        estado_original: EstadoGrafo,
        estados_entrada: List[EstadoGrafo]
    ) -> EstadoGrafo:
        """
        Ejecuta en paralelo. Si cualquier nodo falla, lanza NodoError inmediatamente.
        asyncio.gather propagará la primera excepción.
        """
        tareas = [
            nodo.ejecutar_con_timeout(estado_entrada)
            for nodo, estado_entrada in zip(self._nodos_paralelos, estados_entrada)
        ]

        try:
            resultados = await asyncio.gather(*tareas)
        except (NodoError, Exception) as e:
            raise NodoError(
                self.id,
                f"NodoParalelo falló en modo fail_fast: {e}",
                causa=e if isinstance(e, Exception) else None
            )

        return self._combinar_resultados(estado_original, list(resultados))

    async def _ejecutar_continue_on_error(
        self,
        estado_original: EstadoGrafo,
        estados_entrada: List[EstadoGrafo]
    ) -> EstadoGrafo:
        """
        Ejecuta en paralelo. Si algún nodo falla, continúa con los demás.
        Los fallos se registran en estado.contexto["errores_paralelo"].
        """
        tareas = [
            nodo.ejecutar_con_timeout(estado_entrada)
            for nodo, estado_entrada in zip(self._nodos_paralelos, estados_entrada)
        ]

        # gather con return_exceptions=True para no propagar excepciones
        resultados_raw = await asyncio.gather(*tareas, return_exceptions=True)

        resultados_ok: List[EstadoGrafo] = []
        errores_paralelo = []

        for nodo_inst, resultado in zip(self._nodos_paralelos, resultados_raw):
            if isinstance(resultado, Exception):
                errores_paralelo.append({
                    "nodo_id": nodo_inst.id,
                    "error": str(resultado),
                })
                estado_original.registrar_error(
                    f"{self.id}.{nodo_inst.id}",
                    f"Error en paralelo: {resultado}"
                )
            else:
                resultados_ok.append(resultado)

        if errores_paralelo:
            estado_original.contexto["errores_paralelo"] = errores_paralelo

        if not resultados_ok:
            raise NodoError(
                self.id,
                f"Todos los nodos paralelos fallaron ({len(errores_paralelo)} errores)"
            )

        return self._combinar_resultados(estado_original, resultados_ok)

    def _combinar_resultados(
        self,
        estado_original: EstadoGrafo,
        resultados: List[EstadoGrafo]
    ) -> EstadoGrafo:
        """Llama a la función combinar y fusiona el resultado en el estado original."""
        if self._combinar is not None:
            datos_combinados = self._combinar(resultados)
            if isinstance(datos_combinados, dict):
                estado_original.salida.update(datos_combinados)
        return estado_original
