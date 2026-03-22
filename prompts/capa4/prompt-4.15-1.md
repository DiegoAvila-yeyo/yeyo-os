## ═══════════════════════════════════════
## MICRO-FASE 4.15 — Nodo Base + Decoradores
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 4.15-1 [VSCODE] — Clase Nodo base, NodoFuncion, NodoClase, NodoInline y decorador @nodo

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 4.15 de Capa 4 (Sistema Nervioso): crear la clase Nodo base y las tres formas de definir nodos en el YeyoOrquestador.

CONTEXTO:
- Micro-fase 4.14 completada: EstadoGrafo en src/orquestador/estado.py funcionando con tests
- Un Nodo recibe un EstadoGrafo, lo procesa, y retorna el estado actualizado
- Tres formas: 1) decorador @nodo, 2) herencia de clase Nodo, 3) Nodo(id, fn=lambda)
- El decorador @nodo(id, timeout, max_intentos) envuelve funciones async
- timeout: segundos máximos (asyncio.wait_for), default 30s
- max_intentos: reintentos en caso de error, default 1 (sin reintentos)

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/orquestador/nodo.py:

   Ruta: ~/yeyo-os/src/orquestador/nodo.py
   Contenido:

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


   # Tipo para la función de un nodo
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
       """
       Clase base abstracta para nodos del YeyoOrquestador.

       Un nodo tiene:
       - id: identificador único dentro del grafo
       - timeout: segundos máximos de ejecución
       - max_intentos: reintentos en caso de error (1 = sin reintentos)
       """

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
           # Permitir sobreescribir atributos de clase en instancia
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
           """
           Ejecuta la lógica del nodo.
           Sobreescribir en subclases (forma 2: herencia).
           Si se pasó fn en el constructor (forma 3: inline), la usa.
           """
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
       """
       Nodo creado a partir de una función async (forma 1: decorador @nodo).
       """

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
       """
       Nodo creado inline con una función lambda (forma 3: inline).
       Compatible con funciones sync y async.
       """

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
       """
       Decorador para crear NodoFuncion desde una función async.

       Uso:
           @nodo(id="mi_nodo", timeout=60, max_intentos=3)
           async def mi_nodo(estado: EstadoGrafo) -> EstadoGrafo:
               ...
               return estado
       """
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
           # Preservar metadatos de la función original
           functools.update_wrapper(nodo_func, fn)
           return nodo_func

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

3. Crear archivo tests/unit/orquestador/test_nodo.py:

   Ruta: ~/yeyo-os/tests/unit/orquestador/test_nodo.py
   Contenido:

   """Tests para Nodo, NodoFuncion, NodoInline y decorador @nodo — Micro-fase 4.15"""

   import asyncio
   import pytest
   from src.orquestador.estado import EstadoGrafo
   from src.orquestador.nodo import (
       Nodo, NodoFuncion, NodoInline, NodoError, NodoTimeoutError, nodo
   )


   # ─── Fixtures ─────────────────────────────────────────────────────────────

   def estado_simple() -> EstadoGrafo:
       return EstadoGrafo(entrada={"texto": "hola"})


   # ─── Tests: Forma 1 — Decorador @nodo ─────────────────────────────────────

   class TestDecoradorNodo:

       @pytest.mark.asyncio
       async def test_decorador_crea_nodo_funcion(self):
           @nodo(id="test_nodo")
           async def mi_fn(estado: EstadoGrafo) -> EstadoGrafo:
               estado.salida["resultado"] = "ok"
               return estado

           assert isinstance(mi_fn, NodoFuncion)
           assert mi_fn.id == "test_nodo"

       @pytest.mark.asyncio
       async def test_decorador_ejecuta_correctamente(self):
           @nodo(id="suma")
           async def sumar(estado: EstadoGrafo) -> EstadoGrafo:
               estado.salida["total"] = estado.entrada.get("a", 0) + estado.entrada.get("b", 0)
               return estado

           estado = EstadoGrafo(entrada={"a": 3, "b": 4})
           resultado = await sumar.ejecutar(estado)
           assert resultado.salida["total"] == 7

       def test_decorador_timeout_configurado(self):
           @nodo(id="nodo_lento", timeout=120.0)
           async def fn(estado):
               return estado

           assert fn.timeout == 120.0

       def test_decorador_max_intentos_configurado(self):
           @nodo(id="nodo_retry", max_intentos=3)
           async def fn(estado):
               return estado

           assert fn.max_intentos == 3

       def test_decorador_id_vacio_falla(self):
           with pytest.raises(ValueError):
               @nodo(id="")
               async def fn(estado):
                   return estado

       @pytest.mark.asyncio
       async def test_decorador_timeout_se_respeta(self):
           @nodo(id="nodo_muy_lento", timeout=0.05)
           async def fn_lenta(estado: EstadoGrafo) -> EstadoGrafo:
               await asyncio.sleep(0.2)
               return estado

           estado = estado_simple()
           with pytest.raises(NodoTimeoutError):
               await fn_lenta.ejecutar_con_timeout(estado)

       @pytest.mark.asyncio
       async def test_nodo_rapido_no_timeout(self):
           @nodo(id="nodo_rapido", timeout=2.0)
           async def fn_rapida(estado: EstadoGrafo) -> EstadoGrafo:
               estado.salida["ok"] = True
               return estado

           estado = estado_simple()
           resultado = await fn_rapida.ejecutar_con_timeout(estado)
           assert resultado.salida["ok"] is True


   # ─── Tests: Forma 2 — Herencia de Nodo ─────────────────────────────────────

   class TestNodoClase:

       @pytest.mark.asyncio
       async def test_nodo_por_herencia_ejecuta(self):
           class MiNodo(Nodo):
               id = "nodo_herencia"
               timeout = 10.0
               max_intentos = 2

               async def ejecutar(self, estado: EstadoGrafo) -> EstadoGrafo:
                   estado.salida["tipo"] = "herencia"
                   return estado

           nodo_inst = MiNodo()
           estado = estado_simple()
           resultado = await nodo_inst.ejecutar(estado)
           assert resultado.salida["tipo"] == "herencia"

       def test_nodo_herencia_atributos_clase(self):
           class NodoConfig(Nodo):
               id = "nodo_config"
               timeout = 45.0
               max_intentos = 5

               async def ejecutar(self, estado):
                   return estado

           n = NodoConfig()
           assert n.id == "nodo_config"
           assert n.timeout == 45.0
           assert n.max_intentos == 5

       def test_nodo_sin_id_falla(self):
           class NodoSinId(Nodo):
               async def ejecutar(self, estado):
                   return estado

           with pytest.raises(ValueError):
               NodoSinId()

       def test_nodo_timeout_invalido_falla(self):
           with pytest.raises(ValueError):
               NodoFuncion(id="test", fn=lambda e: e, timeout=-1.0)

       def test_nodo_max_intentos_cero_falla(self):
           with pytest.raises(ValueError):
               NodoFuncion(id="test", fn=lambda e: e, max_intentos=0)

       @pytest.mark.asyncio
       async def test_nodo_sin_override_falla(self):
           class NodoBase(Nodo):
               id = "nodo_base"
               # No sobreescribe ejecutar()

           n = NodoBase()
           estado = estado_simple()
           with pytest.raises(NotImplementedError):
               await n.ejecutar(estado)


   # ─── Tests: Forma 3 — Inline ───────────────────────────────────────────────

   class TestNodoInline:

       @pytest.mark.asyncio
       async def test_nodo_inline_con_lambda(self):
           nodo_passthrough = NodoInline(
               id="passthrough",
               fn=lambda estado: estado
           )
           estado = estado_simple()
           resultado = await nodo_passthrough.ejecutar(estado)
           assert resultado is estado  # mismo objeto

       @pytest.mark.asyncio
       async def test_nodo_inline_con_async_fn(self):
           async def fn_async(estado: EstadoGrafo) -> EstadoGrafo:
               estado.salida["procesado"] = True
               return estado

           nodo_inst = NodoInline(id="async_inline", fn=fn_async)
           estado = estado_simple()
           resultado = await nodo_inst.ejecutar(estado)
           assert resultado.salida["procesado"] is True

       def test_nodo_inline_configuracion(self):
           n = NodoInline(id="test", fn=lambda e: e, timeout=15.0, max_intentos=2)
           assert n.id == "test"
           assert n.timeout == 15.0
           assert n.max_intentos == 2

       @pytest.mark.asyncio
       async def test_nodo_inline_modifica_estado(self):
           def fn_modificadora(estado: EstadoGrafo) -> EstadoGrafo:
               estado.salida["clave"] = "valor"
               estado.contexto["flag"] = True
               return estado

           n = NodoInline(id="modificador", fn=fn_modificadora)
           estado = estado_simple()
           resultado = await n.ejecutar(estado)
           assert resultado.salida["clave"] == "valor"
           assert resultado.contexto["flag"] is True


   # ─── Tests: NodoError y NodoTimeoutError ───────────────────────────────────

   class TestNodoErrors:

       def test_nodo_error_tiene_nodo_id(self):
           error = NodoError("mi_nodo", "algo falló")
           assert error.nodo_id == "mi_nodo"
           assert "mi_nodo" in str(error)

       def test_nodo_timeout_error_es_nodo_error(self):
           error = NodoTimeoutError("nodo_lento", "timeout")
           assert isinstance(error, NodoError)

       def test_nodo_error_con_causa(self):
           causa = ValueError("causa original")
           error = NodoError("nodo", "fallo", causa=causa)
           assert error.causa is causa


   # ─── Tests: repr y metadata ────────────────────────────────────────────────

   class TestNodoRepr:

       def test_repr_nodo_funcion(self):
           @nodo(id="mi_nodo", timeout=10.0)
           async def fn(e):
               return e
           assert "mi_nodo" in repr(fn)

       def test_nodo_inline_repr(self):
           n = NodoInline(id="inline_test", fn=lambda e: e)
           assert "inline_test" in repr(n)

4. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   pip install pytest-asyncio
   python -m pytest tests/unit/orquestador/test_nodo.py -v

VERIFICAR:
- [ ] src/orquestador/nodo.py existe con Nodo, NodoFuncion, NodoInline, decorador @nodo
- [ ] Las 3 formas de definir nodos funcionan correctamente
- [ ] @nodo(id, timeout, max_intentos) crea NodoFuncion con atributos correctos
- [ ] Herencia de Nodo permite sobreescribir ejecutar()
- [ ] NodoInline funciona con lambda sync y async
- [ ] timeout se respeta con asyncio.wait_for → NodoTimeoutError
- [ ] Nodo sin id falla con ValueError
- [ ] max_intentos=0 falla con ValueError
- [ ] TODOS los tests pasan

SI FALLA:
- pytest-asyncio no instalado: pip install pytest-asyncio
- asyncio.TimeoutError no captura correctamente: verificar asyncio.wait_for en ejecutar_con_timeout
- Lambda sync no funciona como coroutine: verificar _llamar_fn que usa asyncio.iscoroutine()

NO HACER:
- No implementar la ejecución del grafo aún (eso es micro-fase 4.17)
- No implementar retry logic aún (el max_intentos lo gestiona YeyoGrafo en 4.17)
- No conectar con EstadoGrafo de Flash Memory (eso es micro-fase 5.22)

GATE: Las 3 formas de definir nodos funcionan, timeout y max_intentos son atributos configurables, NodoTimeoutError se lanza correctamente, todos los tests pasan.
```
