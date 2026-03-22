"""
YeyoOS — YeyoGrafo Coordinador
Micro-fase 4.17 — Capa 4: Sistema Nervioso

Orquesta la ejecución de nodos en secuencia según los edges.
API fluida con method chaining.
Soporta sub-grafos, reintentos, timeout total y callbacks de eventos.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Callable, Awaitable, Union

from .estado import EstadoGrafo, EstadoGrafoError
from .nodo import Nodo, NodoFuncion, NodoError, NodoTimeoutError
from .edge import Edge, EdgeDirecto, EdgeCondicional, EdgeError, FIN_GRAFO, FnCondicion


class GrafoError(Exception):
    """Error en la configuración o ejecución de un YeyoGrafo."""
    pass


class GrafoTimeoutError(GrafoError):
    """El grafo excedió su tiempo máximo de ejecución total."""
    pass


# Tipo para el callback de eventos de nodo
EventoNodo = dict  # {grafo_id, nodo_id, estado, progreso, mensaje, timestamp}
CallbackEvento = Callable[[EventoNodo], Awaitable[None]]


@dataclass
class ResultadoGrafo:
    """Resultado de la ejecución de un YeyoGrafo."""
    grafo_id: str
    estado_final: EstadoGrafo
    exito: bool
    duracion_total_ms: float
    nodos_ejecutados: list = field(default_factory=list)
    errores: list = field(default_factory=list)
    mensaje: str = ""


class YeyoGrafo:
    """
    Coordinador de ejecución del YeyoOrquestador.

    Uso:
        grafo = (
            YeyoGrafo("mi_grafo", "Descripción")
                .agregar_nodo(nodo_a)
                .agregar_nodo(nodo_b)
                .inicio("nodo_a")
                .edge("nodo_a", "nodo_b")
                .fin("nodo_b")
        )
        resultado = await grafo.ejecutar({"entrada": "..."})
    """

    def __init__(
        self,
        id: str,
        descripcion: str = "",
        timeout_total: float = 300.0,
    ):
        if not id:
            raise GrafoError("YeyoGrafo debe tener un 'id' no vacío")
        self.id = id
        self.descripcion = descripcion
        self.timeout_total = timeout_total

        self._nodos: dict[str, Nodo] = {}
        self._edges: dict[str, list[Edge]] = {}  # {desde: [edges...]}
        self._nodo_inicio: Optional[str] = None
        self._nodo_fin: Optional[str] = None
        self._on_nodo_event: Optional[CallbackEvento] = None

    # ─── API fluida (method chaining) ────────────────────────────────────────

    def agregar_nodo(self, nodo: Nodo) -> "YeyoGrafo":
        """Agrega un nodo al grafo."""
        if nodo.id in self._nodos:
            raise GrafoError(f"Ya existe un nodo con id '{nodo.id}' en el grafo '{self.id}'")
        self._nodos[nodo.id] = nodo
        return self

    def inicio(self, nodo_id: str) -> "YeyoGrafo":
        """Define el nodo de inicio del grafo."""
        self._nodo_inicio = nodo_id
        return self

    def fin(self, nodo_id: str) -> "YeyoGrafo":
        """Define el nodo de fin del grafo (después de este se termina)."""
        self._nodo_fin = nodo_id
        return self

    def edge(self, desde: str, hasta: str) -> "YeyoGrafo":
        """Agrega un EdgeDirecto entre dos nodos."""
        e = EdgeDirecto(desde=desde, hasta=hasta)
        self._agregar_edge(e)
        return self

    def edge_condicional(self, desde: str, fn: FnCondicion) -> "YeyoGrafo":
        """Agrega un EdgeCondicional con función de decisión."""
        e = EdgeCondicional(desde=desde, fn=fn)
        self._agregar_edge(e)
        return self

    def agregar_edge(self, edge_obj: Edge) -> "YeyoGrafo":
        """Agrega un Edge pre-construido (EdgeDirecto o EdgeCondicional)."""
        self._agregar_edge(edge_obj)
        return self

    def on_evento(self, callback: CallbackEvento) -> "YeyoGrafo":
        """Registra callback de eventos de nodo (para WebSocket en 4.22)."""
        self._on_nodo_event = callback
        return self

    def _agregar_edge(self, edge_obj: Edge) -> None:
        if edge_obj.desde not in self._edges:
            self._edges[edge_obj.desde] = []
        self._edges[edge_obj.desde].append(edge_obj)

    # ─── Validación ───────────────────────────────────────────────────────────

    def _validar(self) -> None:
        """Valida la configuración del grafo antes de ejecutar."""
        if not self._nodo_inicio:
            raise GrafoError(f"Grafo '{self.id}' no tiene nodo de inicio (.inicio())")
        if self._nodo_inicio not in self._nodos:
            raise GrafoError(
                f"Nodo de inicio '{self._nodo_inicio}' no existe en el grafo '{self.id}'"
            )
        if self._nodo_fin and self._nodo_fin not in self._nodos:
            raise GrafoError(
                f"Nodo de fin '{self._nodo_fin}' no existe en el grafo '{self.id}'"
            )

    # ─── Ejecución ────────────────────────────────────────────────────────────

    async def ejecutar(
        self,
        entrada: Union[dict, EstadoGrafo],
        on_evento: Optional[CallbackEvento] = None,
    ) -> ResultadoGrafo:
        """
        Ejecuta el grafo desde el nodo de inicio hasta el fin.
        Retorna ResultadoGrafo con el estado final y métricas.
        """
        self._validar()

        callback = on_evento or self._on_nodo_event

        # Crear o reutilizar EstadoGrafo
        if isinstance(entrada, EstadoGrafo):
            estado = entrada
        else:
            estado = EstadoGrafo(entrada=entrada)

        t_inicio = datetime.now(timezone.utc)

        try:
            estado = await asyncio.wait_for(
                self._ejecutar_loop(estado, callback),
                timeout=self.timeout_total
            )
            t_fin = datetime.now(timezone.utc)
            duracion_ms = (t_fin - t_inicio).total_seconds() * 1000

            return ResultadoGrafo(
                grafo_id=self.id,
                estado_final=estado,
                exito=not estado.tiene_errores(),
                duracion_total_ms=duracion_ms,
                nodos_ejecutados=list(estado.historial),
                errores=list(estado.errores),
                mensaje="Grafo completado exitosamente" if not estado.tiene_errores() else "Grafo completado con errores",
            )

        except asyncio.TimeoutError:
            t_fin = datetime.now(timezone.utc)
            duracion_ms = (t_fin - t_inicio).total_seconds() * 1000
            estado.registrar_error(
                estado.nodo_actual or "grafo",
                f"Timeout total del grafo ({self.timeout_total}s) excedido"
            )
            return ResultadoGrafo(
                grafo_id=self.id,
                estado_final=estado,
                exito=False,
                duracion_total_ms=duracion_ms,
                nodos_ejecutados=list(estado.historial),
                errores=list(estado.errores),
                mensaje=f"Grafo cancelado por timeout ({self.timeout_total}s)",
            )

    async def _ejecutar_loop(
        self,
        estado: EstadoGrafo,
        callback: Optional[CallbackEvento],
    ) -> EstadoGrafo:
        """Bucle principal de ejecución de nodos."""
        nodo_actual_id = self._nodo_inicio
        nodos_totales = len(self._nodos)
        nodos_ejecutados = 0

        while nodo_actual_id and nodo_actual_id != FIN_GRAFO:
            if nodo_actual_id not in self._nodos:
                raise GrafoError(
                    f"Nodo '{nodo_actual_id}' no encontrado en grafo '{self.id}'"
                )

            nodo = self._nodos[nodo_actual_id]
            estado.marcar_nodo_actual(nodo_actual_id)

            # Emitir evento "activo"
            await self._emitir_evento(callback, estado, nodo_actual_id, "activo",
                                       nodos_ejecutados / max(nodos_totales, 1),
                                       f"Ejecutando {nodo_actual_id}...")

            # Ejecutar con reintentos
            exito = False
            for intento in range(nodo.max_intentos):
                estado.incrementar_intento(nodo_actual_id)
                try:
                    estado = await nodo.ejecutar_con_timeout(estado)
                    exito = True
                    break
                except (NodoError, NodoTimeoutError) as e:
                    estado.registrar_error(nodo_actual_id, str(e))
                    if intento < nodo.max_intentos - 1:
                        # Pequeño backoff antes de reintentar
                        await asyncio.sleep(0.1 * (intento + 1))
                except Exception as e:
                    estado.registrar_error(nodo_actual_id, f"Error inesperado: {e}", e)
                    if intento < nodo.max_intentos - 1:
                        await asyncio.sleep(0.1 * (intento + 1))
                    # Continuar al siguiente intento (no break)

            nodos_ejecutados += 1
            progreso = nodos_ejecutados / max(nodos_totales, 1)

            if not exito:
                # Emitir evento "error" y terminar
                await self._emitir_evento(callback, estado, nodo_actual_id, "error",
                                           progreso, estado.ultimo_error()["mensaje"] if estado.ultimo_error() else "Error")
                break

            # Nodo completado exitosamente
            estado.registrar_nodo_completado(nodo_actual_id)
            await self._emitir_evento(callback, estado, nodo_actual_id, "completado",
                                       progreso, f"{nodo_actual_id} completado")

            # Determinar siguiente nodo
            if nodo_actual_id == self._nodo_fin:
                break

            nodo_actual_id = await self._siguiente_nodo(nodo_actual_id, estado)

        return estado

    async def _siguiente_nodo(self, nodo_id: str, estado: EstadoGrafo) -> Optional[str]:
        """Determina el siguiente nodo usando los edges configurados."""
        edges_desde = self._edges.get(nodo_id, [])

        if not edges_desde:
            return None  # Sin edges = fin del grafo

        # Usar el primer edge (o evaluar el condicional)
        for edge_obj in edges_desde:
            destino = await edge_obj.evaluar(estado)
            if destino == FIN_GRAFO:
                return None
            return destino

        return None

    async def _emitir_evento(
        self,
        callback: Optional[CallbackEvento],
        estado: EstadoGrafo,
        nodo_id: str,
        estado_nodo: str,
        progreso: float,
        mensaje: str,
    ) -> None:
        """Emite un evento de nodo via callback (para WebSocket)."""
        if callback is None:
            return
        try:
            evento: EventoNodo = {
                "type": "graph_event",
                "grafo_id": self.id,
                "nodo_id": nodo_id,
                "estado": estado_nodo,
                "progreso": min(1.0, max(0.0, progreso)),
                "mensaje": mensaje,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "nodos_totales": len(self._nodos),
            }
            await callback(evento)
        except Exception:
            pass  # Los errores de callback no deben interrumpir la ejecución

    # ─── Sub-grafo como nodo ──────────────────────────────────────────────────

    def como_nodo(self, timeout: Optional[float] = None) -> Nodo:
        """
        Convierte este YeyoGrafo en un Nodo para usarlo como sub-grafo
        dentro de otro YeyoGrafo.
        """
        grafo = self
        timeout_nodo = timeout or self.timeout_total

        async def fn_subgrafo(estado: EstadoGrafo) -> EstadoGrafo:
            resultado = await grafo.ejecutar(estado)
            if not resultado.exito:
                raise NodoError(
                    grafo.id,
                    f"Sub-grafo '{grafo.id}' falló: {resultado.mensaje}"
                )
            return resultado.estado_final

        return NodoFuncion(
            id=self.id,
            fn=fn_subgrafo,
            timeout=timeout_nodo,
            max_intentos=1,
            nombre_display=f"SubGrafo:{self.id}",
        )

    def __repr__(self) -> str:
        return (
            f"YeyoGrafo(id={self.id!r}, "
            f"nodos={list(self._nodos.keys())}, "
            f"inicio={self._nodo_inicio!r})"
        )
