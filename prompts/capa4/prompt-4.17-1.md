## ═══════════════════════════════════════
## MICRO-FASE 4.17 — YeyoGrafo Coordinador
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 4.17-1 [VSCODE] — YeyoGrafo con API fluida, método chaining, sub-grafos y ResultadoGrafo

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 4.17 de Capa 4 (Sistema Nervioso): crear YeyoGrafo, el coordinador central del YeyoOrquestador.

CONTEXTO:
- Micro-fases 4.14-4.16 completadas: EstadoGrafo, Nodo (3 formas), Edge (EdgeDirecto, EdgeCondicional)
- YeyoGrafo orquesta la ejecución de nodos en secuencia según los edges configurados
- API fluida (method chaining): .agregar_nodo().inicio().edge().fin()
- Maneja max_intentos por nodo (retry loop con backoff mínimo)
- Maneja timeout total del grafo (asyncio.wait_for sobre todo el grafo)
- ResultadoGrafo dataclass con el resultado final
- como_nodo(): convierte un YeyoGrafo en un Nodo para usarlo como sub-grafo
- FIN_GRAFO = "__fin__" señaliza el fin de la ejecución
- Callback opcional on_nodo_event para notificaciones (se usará en WebSocket en 4.22)

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/orquestador/grafo.py:

   Ruta: ~/yeyo-os/src/orquestador/grafo.py
   Contenido:

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
                       break

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

2. Actualizar src/orquestador/__init__.py:

   Ruta: ~/yeyo-os/src/orquestador/__init__.py
   Contenido:
   """
   YeyoOS — YeyoOrquestador
   Motor de orquestación nativo de YeyoOS.
   Micro-fases 4.14-4.23 — Capa 4: Sistema Nervioso
   """
   from .estado import EstadoGrafo, EstadoGrafoError
   from .nodo import Nodo, NodoFuncion, NodoInline, NodoError, NodoTimeoutError, nodo
   from .edge import Edge, EdgeDirecto, EdgeCondicional, EdgeError, FIN_GRAFO, edge
   from .grafo import YeyoGrafo, ResultadoGrafo, GrafoError, GrafoTimeoutError

3. Crear archivo tests/unit/orquestador/test_grafo.py:

   Ruta: ~/yeyo-os/tests/unit/orquestador/test_grafo.py
   Contenido:

   """Tests para YeyoGrafo y ResultadoGrafo — Micro-fase 4.17"""

   import asyncio
   import pytest
   from src.orquestador.estado import EstadoGrafo
   from src.orquestador.nodo import nodo, NodoInline, NodoError
   from src.orquestador.edge import edge, FIN_GRAFO
   from src.orquestador.grafo import YeyoGrafo, ResultadoGrafo, GrafoError


   # ─── Fixtures de nodos de prueba ──────────────────────────────────────────

   @nodo(id="nodo_a", timeout=5.0)
   async def nodo_a(estado: EstadoGrafo) -> EstadoGrafo:
       estado.salida["a"] = "ejecutado"
       return estado


   @nodo(id="nodo_b", timeout=5.0)
   async def nodo_b(estado: EstadoGrafo) -> EstadoGrafo:
       estado.salida["b"] = "ejecutado"
       return estado


   @nodo(id="nodo_c", timeout=5.0)
   async def nodo_c(estado: EstadoGrafo) -> EstadoGrafo:
       estado.salida["c"] = "ejecutado"
       return estado


   @nodo(id="nodo_falla")
   async def nodo_falla(estado: EstadoGrafo) -> EstadoGrafo:
       raise ValueError("Error simulado en nodo_falla")


   @nodo(id="nodo_lento", timeout=0.1)
   async def nodo_lento(estado: EstadoGrafo) -> EstadoGrafo:
       await asyncio.sleep(1.0)
       return estado


   class TestYeyoGrafoConfiguracion:

       def test_grafo_con_id_valido(self):
           g = YeyoGrafo("mi_grafo", "Descripción")
           assert g.id == "mi_grafo"
           assert g.descripcion == "Descripción"

       def test_grafo_sin_id_falla(self):
           with pytest.raises(GrafoError):
               YeyoGrafo("")

       def test_agregar_nodo_devuelve_grafo(self):
           g = YeyoGrafo("test")
           result = g.agregar_nodo(nodo_a)
           assert result is g  # method chaining

       def test_agregar_nodo_duplicado_falla(self):
           g = YeyoGrafo("test").agregar_nodo(nodo_a)
           with pytest.raises(GrafoError, match="Ya existe"):
               g.agregar_nodo(nodo_a)

       def test_inicio_sin_inicio_falla(self):
           g = YeyoGrafo("test").agregar_nodo(nodo_a)
           with pytest.raises(GrafoError, match="inicio"):
               import asyncio; asyncio.get_event_loop().run_until_complete(g.ejecutar({}))

       def test_repr_informativo(self):
           g = YeyoGrafo("mi_grafo").agregar_nodo(nodo_a).inicio("nodo_a")
           assert "mi_grafo" in repr(g)


   class TestYeyoGrafoEjecucionSimple:

       @pytest.mark.asyncio
       async def test_grafo_un_nodo(self):
           g = (YeyoGrafo("test_uno")
                .agregar_nodo(nodo_a)
                .inicio("nodo_a")
                .fin("nodo_a"))
           resultado = await g.ejecutar({"texto": "hola"})
           assert resultado.exito is True
           assert "nodo_a" in resultado.nodos_ejecutados
           assert resultado.estado_final.salida["a"] == "ejecutado"

       @pytest.mark.asyncio
       async def test_grafo_tres_nodos_en_secuencia(self):
           g = (YeyoGrafo("test_secuencia")
                .agregar_nodo(nodo_a)
                .agregar_nodo(nodo_b)
                .agregar_nodo(nodo_c)
                .inicio("nodo_a")
                .edge("nodo_a", "nodo_b")
                .edge("nodo_b", "nodo_c")
                .fin("nodo_c"))
           resultado = await g.ejecutar({"texto": "hola"})
           assert resultado.exito is True
           assert resultado.nodos_ejecutados == ["nodo_a", "nodo_b", "nodo_c"]
           assert resultado.estado_final.salida["a"] == "ejecutado"
           assert resultado.estado_final.salida["b"] == "ejecutado"
           assert resultado.estado_final.salida["c"] == "ejecutado"

       @pytest.mark.asyncio
       async def test_resultado_tiene_duracion(self):
           g = YeyoGrafo("test").agregar_nodo(nodo_a).inicio("nodo_a").fin("nodo_a")
           resultado = await g.ejecutar({})
           assert resultado.duracion_total_ms >= 0

       @pytest.mark.asyncio
       async def test_acepta_estado_grafo_como_entrada(self):
           g = YeyoGrafo("test").agregar_nodo(nodo_a).inicio("nodo_a").fin("nodo_a")
           estado_previo = EstadoGrafo(entrada={"previo": True})
           estado_previo.contexto["dato_previo"] = "valor"
           resultado = await g.ejecutar(estado_previo)
           assert resultado.estado_final.contexto["dato_previo"] == "valor"


   class TestYeyoGrafoCondicional:

       @pytest.mark.asyncio
       async def test_edge_condicional_elige_ruta_correcta(self):
           @nodo(id="ruta_alta")
           async def ruta_alta(estado: EstadoGrafo) -> EstadoGrafo:
               estado.salida["ruta"] = "alta"
               return estado

           @nodo(id="ruta_baja")
           async def ruta_baja(estado: EstadoGrafo) -> EstadoGrafo:
               estado.salida["ruta"] = "baja"
               return estado

           @nodo(id="evaluador")
           async def evaluador(estado: EstadoGrafo) -> EstadoGrafo:
               estado.contexto["score"] = estado.entrada.get("score", 0)
               return estado

           g = (YeyoGrafo("test_cond")
                .agregar_nodo(evaluador)
                .agregar_nodo(ruta_alta)
                .agregar_nodo(ruta_baja)
                .inicio("evaluador")
                .edge_condicional("evaluador", lambda e: "ruta_alta" if e.contexto["score"] >= 0.8 else "ruta_baja")
                .fin("ruta_alta"))

           resultado_alto = await g.ejecutar({"score": 0.9})
           assert resultado_alto.estado_final.salida["ruta"] == "alta"

           resultado_bajo = await g.ejecutar({"score": 0.3})
           assert resultado_bajo.estado_final.salida["ruta"] == "baja"


   class TestYeyoGrafoErrores:

       @pytest.mark.asyncio
       async def test_nodo_que_falla_retorna_exito_false(self):
           g = (YeyoGrafo("test_falla")
                .agregar_nodo(nodo_falla)
                .inicio("nodo_falla")
                .fin("nodo_falla"))
           resultado = await g.ejecutar({})
           assert resultado.exito is False
           assert len(resultado.errores) > 0

       @pytest.mark.asyncio
       async def test_max_intentos_se_respeta(self):
           contador = {"n": 0}

           @nodo(id="nodo_retry_test", max_intentos=3)
           async def nodo_retry(estado: EstadoGrafo) -> EstadoGrafo:
               contador["n"] += 1
               raise ValueError("Falla siempre")

           g = (YeyoGrafo("test_retry")
                .agregar_nodo(nodo_retry)
                .inicio("nodo_retry_test")
                .fin("nodo_retry_test"))
           resultado = await g.ejecutar({})
           assert resultado.exito is False
           assert contador["n"] == 3  # 3 intentos

       @pytest.mark.asyncio
       async def test_nodo_timeout_se_respeta(self):
           g = (YeyoGrafo("test_timeout")
                .agregar_nodo(nodo_lento)
                .inicio("nodo_lento")
                .fin("nodo_lento"))
           resultado = await g.ejecutar({})
           assert resultado.exito is False
           assert "timeout" in resultado.errores[0]["mensaje"].lower()

       @pytest.mark.asyncio
       async def test_timeout_total_grafo(self):
           @nodo(id="nodo_muy_lento", timeout=10.0)
           async def nodo_muy_lento(estado: EstadoGrafo) -> EstadoGrafo:
               await asyncio.sleep(5.0)
               return estado

           g = (YeyoGrafo("test_timeout_total", timeout_total=0.1)
                .agregar_nodo(nodo_muy_lento)
                .inicio("nodo_muy_lento")
                .fin("nodo_muy_lento"))
           resultado = await g.ejecutar({})
           assert resultado.exito is False


   class TestYeyoGrafoSubgrafo:

       @pytest.mark.asyncio
       async def test_subgrafo_como_nodo(self):
           sub = (YeyoGrafo("sub_grafo")
                  .agregar_nodo(nodo_a)
                  .agregar_nodo(nodo_b)
                  .inicio("nodo_a")
                  .edge("nodo_a", "nodo_b")
                  .fin("nodo_b"))

           @nodo(id="antes")
           async def nodo_antes(estado: EstadoGrafo) -> EstadoGrafo:
               estado.contexto["antes"] = True
               return estado

           principal = (YeyoGrafo("grafo_principal")
                        .agregar_nodo(nodo_antes)
                        .agregar_nodo(sub.como_nodo())
                        .inicio("antes")
                        .edge("antes", "sub_grafo")
                        .fin("sub_grafo"))

           resultado = await principal.ejecutar({"texto": "test"})
           assert resultado.exito is True
           assert resultado.estado_final.salida.get("a") == "ejecutado"
           assert resultado.estado_final.salida.get("b") == "ejecutado"


   class TestYeyoGrafoCallbackEvento:

       @pytest.mark.asyncio
       async def test_callback_recibe_eventos(self):
           eventos_recibidos = []

           async def mi_callback(evento: dict) -> None:
               eventos_recibidos.append(evento)

           g = (YeyoGrafo("test_eventos")
                .agregar_nodo(nodo_a)
                .agregar_nodo(nodo_b)
                .inicio("nodo_a")
                .edge("nodo_a", "nodo_b")
                .fin("nodo_b"))

           await g.ejecutar({}, on_evento=mi_callback)

           # Cada nodo emite 2 eventos: "activo" y "completado"
           assert len(eventos_recibidos) >= 4
           estados = [e["estado"] for e in eventos_recibidos]
           assert "activo" in estados
           assert "completado" in estados

       @pytest.mark.asyncio
       async def test_evento_tiene_estructura_correcta(self):
           eventos = []

           async def callback(evento):
               eventos.append(evento)

           g = YeyoGrafo("test").agregar_nodo(nodo_a).inicio("nodo_a").fin("nodo_a")
           await g.ejecutar({}, on_evento=callback)

           evento = eventos[0]
           assert evento["type"] == "graph_event"
           assert evento["grafo_id"] == "test"
           assert "nodo_id" in evento
           assert "estado" in evento
           assert "progreso" in evento
           assert "timestamp" in evento
           assert 0.0 <= evento["progreso"] <= 1.0

4. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/orquestador/test_grafo.py -v

VERIFICAR:
- [ ] src/orquestador/grafo.py existe con YeyoGrafo y ResultadoGrafo
- [ ] API fluida (method chaining) funciona: .agregar_nodo().inicio().edge().fin()
- [ ] Grafo de 3 nodos ejecuta en orden correcto
- [ ] EdgeCondicional elige la ruta correcta según el estado
- [ ] max_intentos se respeta (3 intentos = 3 llamadas a la función)
- [ ] Timeout por nodo genera NodoTimeoutError
- [ ] Timeout total del grafo termina la ejecución
- [ ] Sub-grafos funcionan como nodos via como_nodo()
- [ ] Callback on_evento recibe eventos con estructura correcta
- [ ] TODOS los tests pasan

SI FALLA:
- asyncio.wait_for en Python 3.11+: verificar compatibilidad de versión
- Method chaining no retorna self: verificar que cada método retorna self
- Sub-grafo falla: verificar que como_nodo() crea NodoFuncion con fn_subgrafo

NO HACER:
- No implementar NodoParalelo aún (eso es micro-fase 4.18)
- No conectar con Ollama aún (eso es micro-fase 4.19)
- No implementar WebSocket events completos aún (eso es micro-fase 4.22)

GATE: YeyoGrafo ejecuta secuencias de nodos, EdgeCondicional elige rutas, sub-grafos funcionan, max_intentos y timeouts se respetan, callbacks de eventos funcionan, todos los tests pasan.
```
