## ═══════════════════════════════════════
## MICRO-FASE 4.18 — NodoParalelo
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 4.18-1 [VSCODE] — NodoParalelo con asyncio.gather y manejo de errores

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 4.18 de Capa 4 (Sistema Nervioso): crear NodoParalelo que ejecuta múltiples nodos simultáneamente con asyncio.gather y combina los resultados.

CONTEXTO:
- Micro-fase 4.17 completada: YeyoGrafo funcionando con API fluida, sub-grafos y callbacks
- NodoParalelo hereda de Nodo y ejecuta múltiples nodos al mismo tiempo
- Los nodos internos reciben copias del mismo EstadoGrafo (cada uno opera independientemente)
- Al terminar, la función combinar fusiona los resultados en el estado final
- Dos modos de error: fail_fast (default) — falla si cualquier nodo falla; continue_on_error — continúa aunque alguno falle
- El tiempo total = tiempo del nodo más lento (no la suma)

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/orquestador/paralelo.py:

   Ruta: ~/yeyo-os/src/orquestador/paralelo.py
   Contenido:

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
           combinar: Callable[[List[EstadoGrafo]], dict],
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
           datos_combinados = self._combinar(resultados)
           if isinstance(datos_combinados, dict):
               estado_original.salida.update(datos_combinados)
           return estado_original

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
   from .paralelo import NodoParalelo

3. Crear archivo tests/unit/orquestador/test_paralelo.py:

   Ruta: ~/yeyo-os/tests/unit/orquestador/test_paralelo.py
   Contenido:

   """Tests para NodoParalelo — Micro-fase 4.18"""

   import asyncio
   import time
   import pytest
   from src.orquestador.estado import EstadoGrafo
   from src.orquestador.nodo import nodo, NodoError
   from src.orquestador.paralelo import NodoParalelo


   # ─── Nodos de prueba ──────────────────────────────────────────────────────

   @nodo(id="gen_a", timeout=5.0)
   async def gen_a(estado: EstadoGrafo) -> EstadoGrafo:
       estado.salida["a"] = "valor_a"
       return estado


   @nodo(id="gen_b", timeout=5.0)
   async def gen_b(estado: EstadoGrafo) -> EstadoGrafo:
       estado.salida["b"] = "valor_b"
       return estado


   @nodo(id="gen_c", timeout=5.0)
   async def gen_c(estado: EstadoGrafo) -> EstadoGrafo:
       estado.salida["c"] = "valor_c"
       return estado


   @nodo(id="gen_lento", timeout=5.0)
   async def gen_lento(estado: EstadoGrafo) -> EstadoGrafo:
       await asyncio.sleep(0.1)
       estado.salida["lento"] = "hecho"
       return estado


   @nodo(id="gen_falla")
   async def gen_falla(estado: EstadoGrafo) -> EstadoGrafo:
       raise ValueError("Fallo simulado en gen_falla")


   def combinar_simple(resultados):
       combinado = {}
       for r in resultados:
           combinado.update(r.salida)
       return combinado


   class TestNodoParaleloConfiguracion:

       def test_creacion_basica(self):
           n = NodoParalelo(
               id="test_paralelo",
               nodos=[gen_a, gen_b],
               combinar=combinar_simple,
           )
           assert n.id == "test_paralelo"
           assert n.modo_error == "fail_fast"

       def test_sin_nodos_falla(self):
           with pytest.raises(ValueError):
               NodoParalelo(id="vacio", nodos=[], combinar=combinar_simple)

       def test_modo_error_invalido_falla(self):
           with pytest.raises(ValueError):
               NodoParalelo(id="test", nodos=[gen_a], combinar=combinar_simple, modo_error="otro_modo")

       def test_modo_continue_on_error_valido(self):
           n = NodoParalelo(
               id="test",
               nodos=[gen_a],
               combinar=combinar_simple,
               modo_error="continue_on_error"
           )
           assert n.modo_error == "continue_on_error"


   class TestNodoParaleloEjecucion:

       @pytest.mark.asyncio
       async def test_ejecuta_nodos_en_paralelo(self):
           n = NodoParalelo(
               id="gen_abc",
               nodos=[gen_a, gen_b, gen_c],
               combinar=combinar_simple,
           )
           estado = EstadoGrafo(entrada={})
           resultado = await n.ejecutar(estado)
           assert resultado.salida["a"] == "valor_a"
           assert resultado.salida["b"] == "valor_b"
           assert resultado.salida["c"] == "valor_c"

       @pytest.mark.asyncio
       async def test_tiempo_total_es_del_nodo_mas_lento_no_la_suma(self):
           """Con 3 nodos de 0.1s cada uno, el tiempo total debe ser ~0.1s (no 0.3s)."""
           @nodo(id="p1", timeout=5.0)
           async def p1(e):
               await asyncio.sleep(0.1)
               e.salida["p1"] = True
               return e

           @nodo(id="p2", timeout=5.0)
           async def p2(e):
               await asyncio.sleep(0.1)
               e.salida["p2"] = True
               return e

           n = NodoParalelo(id="paralelo_time", nodos=[p1, p2], combinar=combinar_simple)
           estado = EstadoGrafo(entrada={})
           t_inicio = time.monotonic()
           resultado = await n.ejecutar(estado)
           t_fin = time.monotonic()
           duracion = t_fin - t_inicio
           # Debe ser ~0.1s, NO ~0.2s
           assert duracion < 0.18, f"Tiempo {duracion:.3f}s debería ser < 0.18s (paralelo)"
           assert resultado.salida.get("p1") is True
           assert resultado.salida.get("p2") is True

       @pytest.mark.asyncio
       async def test_combinar_fusiona_resultados(self):
           def combinar_personalizado(resultados):
               return {
                   "total": sum(r.salida.get("valor", 0) for r in resultados),
                   "count": len(resultados),
               }

           @nodo(id="num1")
           async def num1(e):
               e.salida["valor"] = 10
               return e

           @nodo(id="num2")
           async def num2(e):
               e.salida["valor"] = 20
               return e

           n = NodoParalelo(id="suma_paralelo", nodos=[num1, num2], combinar=combinar_personalizado)
           estado = EstadoGrafo(entrada={})
           resultado = await n.ejecutar(estado)
           assert resultado.salida["total"] == 30
           assert resultado.salida["count"] == 2

       @pytest.mark.asyncio
       async def test_cada_nodo_recibe_copia_independiente(self):
           """Los nodos no deben compartir el mismo EstadoGrafo."""
           estados_recibidos = []

           @nodo(id="captura1")
           async def captura1(e):
               estados_recibidos.append(id(e))
               return e

           @nodo(id="captura2")
           async def captura2(e):
               estados_recibidos.append(id(e))
               return e

           n = NodoParalelo(id="test_copia", nodos=[captura1, captura2], combinar=combinar_simple)
           estado = EstadoGrafo(entrada={})
           await n.ejecutar(estado)
           # Los dos estados deben ser objetos distintos
           assert estados_recibidos[0] != estados_recibidos[1]


   class TestNodoParaleloFailFast:

       @pytest.mark.asyncio
       async def test_fail_fast_falla_si_un_nodo_falla(self):
           n = NodoParalelo(
               id="paralelo_falla",
               nodos=[gen_a, gen_falla],
               combinar=combinar_simple,
               modo_error="fail_fast",
           )
           estado = EstadoGrafo(entrada={})
           with pytest.raises(NodoError):
               await n.ejecutar(estado)

       @pytest.mark.asyncio
       async def test_fail_fast_con_todos_exitosos_funciona(self):
           n = NodoParalelo(
               id="paralelo_ok",
               nodos=[gen_a, gen_b],
               combinar=combinar_simple,
               modo_error="fail_fast",
           )
           estado = EstadoGrafo(entrada={})
           resultado = await n.ejecutar(estado)
           assert resultado.salida.get("a") == "valor_a"
           assert resultado.salida.get("b") == "valor_b"


   class TestNodoParaleloContinueOnError:

       @pytest.mark.asyncio
       async def test_continue_on_error_continua_si_uno_falla(self):
           n = NodoParalelo(
               id="paralelo_continue",
               nodos=[gen_a, gen_falla, gen_b],
               combinar=combinar_simple,
               modo_error="continue_on_error",
           )
           estado = EstadoGrafo(entrada={})
           resultado = await n.ejecutar(estado)
           # Los nodos exitosos deben estar en el resultado
           assert resultado.salida.get("a") == "valor_a"
           assert resultado.salida.get("b") == "valor_b"

       @pytest.mark.asyncio
       async def test_continue_on_error_registra_errores(self):
           n = NodoParalelo(
               id="paralelo_err",
               nodos=[gen_a, gen_falla],
               combinar=combinar_simple,
               modo_error="continue_on_error",
           )
           estado = EstadoGrafo(entrada={})
           resultado = await n.ejecutar(estado)
           assert "errores_paralelo" in resultado.contexto
           assert len(resultado.contexto["errores_paralelo"]) == 1
           assert resultado.contexto["errores_paralelo"][0]["nodo_id"] == "gen_falla"

       @pytest.mark.asyncio
       async def test_continue_on_error_todos_fallan_lanza_error(self):
           @nodo(id="falla2")
           async def falla2(e):
               raise ValueError("falla2")

           n = NodoParalelo(
               id="todos_fallan",
               nodos=[gen_falla, falla2],
               combinar=combinar_simple,
               modo_error="continue_on_error",
           )
           estado = EstadoGrafo(entrada={})
           with pytest.raises(NodoError, match="Todos los nodos paralelos fallaron"):
               await n.ejecutar(estado)

4. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/orquestador/test_paralelo.py -v

VERIFICAR:
- [ ] src/orquestador/paralelo.py existe con NodoParalelo
- [ ] Tres nodos paralelos se ejecutan simultáneamente (no secuencialmente)
- [ ] Tiempo total ≈ tiempo del nodo más lento, no la suma
- [ ] Función combinar fusiona los resultados en estado.salida
- [ ] fail_fast: lanza NodoError si cualquier nodo falla
- [ ] continue_on_error: continúa, registra errores en estado.contexto["errores_paralelo"]
- [ ] Cada nodo recibe copia independiente del EstadoGrafo (no el mismo objeto)
- [ ] TODOS los tests pasan

SI FALLA:
- asyncio.gather con return_exceptions: verificar que en continue_on_error usa return_exceptions=True
- Copia de estado: verificar que estado.clonar() produce objeto separado
- tiempo total mayor al esperado: verificar que las tareas son genuinamente concurrentes (await gather, no secuencial)

NO HACER:
- No implementar límite de concurrencia/semaphore (eso sería un extra futuro)
- No integrar con el grafo aún — NodoParalelo es un Nodo normal que YeyoGrafo puede usar
- No implementar NodoParalelo con timeout por nodo interno diferente al del NodoParalelo

GATE: Nodos paralelos se ejecutan simultáneamente con asyncio.gather, función combinar fusiona resultados, errores manejados en fail_fast y continue_on_error, todos los tests pasan.
```
