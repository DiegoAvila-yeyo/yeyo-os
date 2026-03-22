## ═══════════════════════════════════════
## MICRO-FASE 4.16 — Edge + Condiciones
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 4.16-1 [VSCODE] — Edge, EdgeDirecto, EdgeCondicional y decorador @edge

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 4.16 de Capa 4 (Sistema Nervioso): crear los tipos de Edge que definen cómo fluye el EstadoGrafo entre nodos del YeyoOrquestador.

CONTEXTO:
- Micro-fase 4.15 completada: Nodo, NodoFuncion, NodoInline y decorador @nodo
- Un Edge conecta dos nodos: desde (nodo origen) → hasta (nodo destino)
- EdgeDirecto: siempre va al mismo nodo destino
- EdgeCondicional: una función decide el nodo destino según el estado
- El decorador @edge(desde) convierte una función en EdgeCondicional
- Las funciones de EdgeCondicional pueden ser sync o async
- FIN_GRAFO = "__fin__" es el nodo especial que indica fin del grafo

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/orquestador/edge.py:

   Ruta: ~/yeyo-os/src/orquestador/edge.py
   Contenido:

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

3. Crear archivo tests/unit/orquestador/test_edge.py:

   Ruta: ~/yeyo-os/tests/unit/orquestador/test_edge.py
   Contenido:

   """Tests para Edge, EdgeDirecto, EdgeCondicional y decorador @edge — Micro-fase 4.16"""

   import pytest
   from src.orquestador.estado import EstadoGrafo
   from src.orquestador.edge import (
       Edge, EdgeDirecto, EdgeCondicional, EdgeError, FIN_GRAFO, edge
   )


   def estado_con_score(score: float) -> EstadoGrafo:
       e = EstadoGrafo(entrada={"prompt": "test"})
       e.contexto["score"] = score
       return e


   class TestFIN_GRAFO:
       def test_fin_grafo_es_string(self):
           assert isinstance(FIN_GRAFO, str)

       def test_fin_grafo_valor(self):
           assert FIN_GRAFO == "__fin__"


   class TestEdgeDirecto:

       @pytest.mark.asyncio
       async def test_evalua_siempre_al_mismo_destino(self):
           e = EdgeDirecto(desde="nodo_a", hasta="nodo_b")
           estado = EstadoGrafo(entrada={})
           assert await e.evaluar(estado) == "nodo_b"

       @pytest.mark.asyncio
       async def test_evalua_siempre_igual_independiente_del_estado(self):
           e = EdgeDirecto(desde="a", hasta="b")
           for _ in range(5):
               estado = EstadoGrafo(entrada={"x": _})
               assert await e.evaluar(estado) == "b"

       @pytest.mark.asyncio
       async def test_puede_apuntar_a_fin_grafo(self):
           e = EdgeDirecto(desde="ultimo", hasta=FIN_GRAFO)
           estado = EstadoGrafo(entrada={})
           assert await e.evaluar(estado) == FIN_GRAFO

       def test_desde_vacio_falla(self):
           with pytest.raises(EdgeError):
               EdgeDirecto(desde="", hasta="nodo_b")

       def test_hasta_vacio_falla(self):
           with pytest.raises(EdgeError):
               EdgeDirecto(desde="nodo_a", hasta="")

       def test_atributos_correctos(self):
           e = EdgeDirecto(desde="origen", hasta="destino")
           assert e.desde == "origen"
           assert e.hasta == "destino"

       def test_repr_informativo(self):
           e = EdgeDirecto(desde="a", hasta="b")
           assert "a" in repr(e)
           assert "b" in repr(e)


   class TestEdgeCondicional:

       @pytest.mark.asyncio
       async def test_evalua_con_funcion_sync(self):
           def fn(estado: EstadoGrafo) -> str:
               return "alto" if estado.contexto.get("score", 0) >= 0.8 else "bajo"

           e = EdgeCondicional(desde="evaluar", fn=fn)
           assert await e.evaluar(estado_con_score(0.9)) == "alto"
           assert await e.evaluar(estado_con_score(0.5)) == "bajo"

       @pytest.mark.asyncio
       async def test_evalua_con_funcion_async(self):
           async def fn(estado: EstadoGrafo) -> str:
               return "alto" if estado.contexto.get("score", 0) >= 0.8 else "bajo"

           e = EdgeCondicional(desde="evaluar", fn=fn)
           assert await e.evaluar(estado_con_score(0.9)) == "alto"
           assert await e.evaluar(estado_con_score(0.3)) == "bajo"

       @pytest.mark.asyncio
       async def test_puede_retornar_fin_grafo(self):
           e = EdgeCondicional(
               desde="chequear",
               fn=lambda estado: FIN_GRAFO if estado.contexto.get("terminar") else "continuar"
           )
           estado = EstadoGrafo(entrada={})
           estado.contexto["terminar"] = True
           assert await e.evaluar(estado) == FIN_GRAFO

       @pytest.mark.asyncio
       async def test_multiples_destinos_posibles(self):
           def fn(estado: EstadoGrafo) -> str:
               score = estado.contexto.get("score", 0)
               if score >= 0.8:
                   return "upscale"
               elif score >= 0.5:
                   return "refinar"
               else:
                   return "regenerar"

           e = EdgeCondicional(desde="evaluar", fn=fn)
           assert await e.evaluar(estado_con_score(0.9)) == "upscale"
           assert await e.evaluar(estado_con_score(0.6)) == "refinar"
           assert await e.evaluar(estado_con_score(0.2)) == "regenerar"

       @pytest.mark.asyncio
       async def test_retornar_no_string_falla(self):
           e = EdgeCondicional(desde="test", fn=lambda e: 42)
           estado = EstadoGrafo(entrada={})
           with pytest.raises(EdgeError, match="string"):
               await e.evaluar(estado)

       @pytest.mark.asyncio
       async def test_retornar_string_vacio_falla(self):
           e = EdgeCondicional(desde="test", fn=lambda e: "")
           estado = EstadoGrafo(entrada={})
           with pytest.raises(EdgeError):
               await e.evaluar(estado)

       def test_fn_none_falla(self):
           with pytest.raises(EdgeError):
               EdgeCondicional(desde="test", fn=None)

       def test_desde_vacio_falla(self):
           with pytest.raises(EdgeError):
               EdgeCondicional(desde="", fn=lambda e: "x")

       def test_repr_informativo(self):
           e = EdgeCondicional(desde="evaluar", fn=lambda e: "x", nombre="mi_fn")
           assert "evaluar" in repr(e)
           assert "mi_fn" in repr(e)


   class TestDecoradorEdge:

       @pytest.mark.asyncio
       async def test_decorador_crea_edge_condicional(self):
           @edge(desde="evaluar")
           def siguiente(estado: EstadoGrafo) -> str:
               return "ok"

           assert isinstance(siguiente, EdgeCondicional)
           assert siguiente.desde == "evaluar"

       @pytest.mark.asyncio
       async def test_decorador_sync_evalua_correctamente(self):
           @edge(desde="evaluar")
           def siguiente(estado: EstadoGrafo) -> str:
               return "alto" if estado.contexto.get("score", 0) >= 0.8 else "bajo"

           assert await siguiente.evaluar(estado_con_score(0.9)) == "alto"
           assert await siguiente.evaluar(estado_con_score(0.3)) == "bajo"

       @pytest.mark.asyncio
       async def test_decorador_async_evalua_correctamente(self):
           @edge(desde="evaluar")
           async def siguiente(estado: EstadoGrafo) -> str:
               return "resultado_async"

           estado = EstadoGrafo(entrada={})
           assert await siguiente.evaluar(estado) == "resultado_async"

       def test_decorador_desde_vacio_falla(self):
           with pytest.raises(EdgeError):
               @edge(desde="")
               def fn(e):
                   return "x"

       def test_decorador_preserva_nombre_funcion(self):
           @edge(desde="nodo_a")
           def mi_logica_de_routing(estado: EstadoGrafo) -> str:
               return "destino"

           assert mi_logica_de_routing.nombre == "mi_logica_de_routing"

4. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/orquestador/test_edge.py -v

VERIFICAR:
- [ ] src/orquestador/edge.py existe con Edge, EdgeDirecto, EdgeCondicional, decorador @edge
- [ ] FIN_GRAFO = "__fin__" definido como constante
- [ ] EdgeDirecto siempre retorna el mismo nodo destino independientemente del estado
- [ ] EdgeCondicional evalúa función sync y async correctamente
- [ ] Múltiples destinos posibles en EdgeCondicional
- [ ] EdgeCondicional falla si la función retorna no-string o string vacío
- [ ] Decorador @edge(desde) crea EdgeCondicional
- [ ] TODOS los tests pasan

SI FALLA:
- asyncio.iscoroutine check: verificar que el resultado de fn() sea coroutine, no la fn misma
- Import error: verificar que edge.py importa de .estado correctamente

NO HACER:
- No implementar el YAML declarativo aún (es un extra de micro-fase 4.17)
- No implementar el edge "IA decide" (eso es parte del YeyoOrquestador en 4.19)
- No conectar con el grafo aún (eso es micro-fase 4.17)

GATE: EdgeDirecto siempre va al mismo nodo, EdgeCondicional evalúa correctamente funciones sync y async, FIN_GRAFO señaliza fin del grafo, todos los tests pasan.
```
