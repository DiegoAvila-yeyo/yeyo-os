## ═══════════════════════════════════════
## MICRO-FASE 5.25 — GrafoValidador (Seguridad AST)
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 5.25-1 [VSCODE] — GrafoValidador con análisis AST para código generado por IA

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 5.25 de Capa 5 (Órganos): crear el GrafoValidador que analiza código Python generado por IA usando el módulo ast para detectar patrones peligrosos antes de ejecutarlo.

CONTEXTO:
- Micro-fase 5.24 completada: GeneradorGrafos con validación básica de strings
- GrafoValidador reemplaza y mejora la validación básica del GeneradorGrafos
- Usa análisis AST (Abstract Syntax Tree) para analizar el código sin ejecutarlo
- Detecta: imports no permitidos, eval/exec/compile, __import__, os.system, atributos peligrosos
- Verifica que solo usa nodos del catálogo registrado (si se pasa el catálogo)
- Retorna ValidationResult con is_valid y lista de errores descriptivos
- GrafoValidador se integra con GeneradorGrafos en lugar de la validación básica

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/orquestador/validador.py:

   Ruta: ~/yeyo-os/src/orquestador/validador.py
   Contenido:

   """
   YeyoOS — GrafoValidador
   Micro-fase 5.25 — Capa 5: Órganos

   Análisis AST de código Python generado por IA.
   Detecta patrones peligrosos antes de ejecutar el código.
   """

   import ast
   from dataclasses import dataclass, field
   from typing import Optional


   # Imports que están completamente prohibidos
   IMPORTS_PROHIBIDOS = frozenset({
       "os", "sys", "subprocess", "shutil", "socket", "urllib",
       "http", "ftplib", "smtplib", "paramiko", "requests",
       "importlib", "ctypes", "cffi", "multiprocessing", "threading",
       "pickle", "shelve", "marshal", "tempfile",
   })

   # Nombres de builtins peligrosos
   BUILTINS_PELIGROSOS = frozenset({
       "eval", "exec", "compile", "__import__", "open",
       "input", "breakpoint", "memoryview",
   })

   # Atributos de objetos peligrosos
   ATRIBUTOS_PELIGROSOS = frozenset({
       "__class__", "__subclasses__", "__bases__", "__mro__",
       "__globals__", "__locals__", "__builtins__", "__code__",
       "__func__", "__closure__", "__dict__",
   })

   # Módulos del orquestador permitidos explícitamente
   IMPORTS_PERMITIDOS = frozenset({
       "src.orquestador", "src.orquestador.nodo",
       "src.orquestador.edge", "src.orquestador.grafo",
       "src.orquestador.estado",
   })


   @dataclass
   class ValidationResult:
       """Resultado de la validación de código de grafo."""
       is_valid: bool
       errores: list[str] = field(default_factory=list)
       advertencias: list[str] = field(default_factory=list)

       def agregar_error(self, mensaje: str) -> None:
           self.errores.append(mensaje)
           self.is_valid = False

       def agregar_advertencia(self, mensaje: str) -> None:
           self.advertencias.append(mensaje)

       def __repr__(self) -> str:
           return (
               f"ValidationResult(is_valid={self.is_valid}, "
               f"errores={len(self.errores)}, "
               f"advertencias={len(self.advertencias)})"
           )


   class GrafoValidador:
       """
       Valida código Python de grafos generados por IA usando análisis AST.

       Realiza tres tipos de análisis:
       1. Análisis de imports: imports prohibidos o de módulos externos
       2. Análisis de builtins: uso de eval, exec, __import__, etc.
       3. Análisis de estructura: presencia de variable 'grafo' de tipo YeyoGrafo
       """

       def __init__(self, nodos_permitidos: Optional[list[str]] = None):
           """
           Args:
               nodos_permitidos: lista de IDs de nodos del catálogo que se pueden usar.
                                 Si None, no se valida el uso de nodos específicos.
           """
           self.nodos_permitidos = nodos_permitidos

       def validar(self, codigo: str) -> ValidationResult:
           """
           Valida el código Python del grafo.
           Retorna ValidationResult con is_valid y lista de errores.
           """
           result = ValidationResult(is_valid=True)

           if not codigo.strip():
               result.agregar_error("El código está vacío")
               return result

           # Parsear AST
           try:
               arbol = ast.parse(codigo)
           except SyntaxError as e:
               result.agregar_error(f"Error de sintaxis: {e}")
               return result

           # Ejecutar análisis
           self._analizar_imports(arbol, result)
           self._analizar_builtins(arbol, result)
           self._analizar_atributos_peligrosos(arbol, result)
           self._analizar_estructura(arbol, result)

           if self.nodos_permitidos:
               self._analizar_uso_de_nodos(arbol, result)

           return result

       # ─── Análisis de imports ──────────────────────────────────────────────────

       def _analizar_imports(self, arbol: ast.AST, result: ValidationResult) -> None:
           """Detecta imports de módulos prohibidos."""
           for nodo in ast.walk(arbol):
               if isinstance(nodo, ast.Import):
                   for alias in nodo.names:
                       modulo_raiz = alias.name.split(".")[0]
                       if modulo_raiz in IMPORTS_PROHIBIDOS:
                           result.agregar_error(
                               f"Import prohibido: '{alias.name}'. "
                               f"Los módulos del sistema no están permitidos."
                           )

               elif isinstance(nodo, ast.ImportFrom):
                   if nodo.module is None:
                       continue
                   modulo_raiz = nodo.module.split(".")[0]
                   if modulo_raiz in IMPORTS_PROHIBIDOS:
                       result.agregar_error(
                           f"Import prohibido: 'from {nodo.module} import ...'. "
                           f"Los módulos del sistema no están permitidos."
                       )
                   # Avisar si importa desde fuera del orquestador
                   elif not any(nodo.module.startswith(p) for p in IMPORTS_PERMITIDOS):
                       result.agregar_advertencia(
                           f"Import externo detectado: 'from {nodo.module} import ...'. "
                           f"Solo se permiten imports del orquestador."
                       )

       # ─── Análisis de builtins peligrosos ──────────────────────────────────────

       def _analizar_builtins(self, arbol: ast.AST, result: ValidationResult) -> None:
           """Detecta llamadas a builtins peligrosos (eval, exec, compile, etc.)."""
           for nodo in ast.walk(arbol):
               if isinstance(nodo, ast.Call):
                   # Llamada directa: eval(...), exec(...)
                   if isinstance(nodo.func, ast.Name):
                       if nodo.func.id in BUILTINS_PELIGROSOS:
                           result.agregar_error(
                               f"Función peligrosa detectada: '{nodo.func.id}()'. "
                               f"No está permitida en grafos generados."
                           )
                   # Llamada con atributo: __builtins__['eval'](...)
                   elif isinstance(nodo.func, ast.Attribute):
                       if nodo.func.attr in BUILTINS_PELIGROSOS:
                           result.agregar_error(
                               f"Atributo peligroso en llamada: '.{nodo.func.attr}()'"
                           )

               # Acceso a nombre directo como variable: x = eval
               elif isinstance(nodo, ast.Name):
                   if nodo.id in BUILTINS_PELIGROSOS and isinstance(nodo.ctx, ast.Load):
                       # Solo reportar si no es parte de una llamada (ya capturada arriba)
                       pass  # Capturado en ast.Call

       # ─── Análisis de atributos peligrosos ────────────────────────────────────

       def _analizar_atributos_peligrosos(self, arbol: ast.AST, result: ValidationResult) -> None:
           """Detecta acceso a atributos peligrosos de objetos."""
           for nodo in ast.walk(arbol):
               if isinstance(nodo, ast.Attribute):
                   if nodo.attr in ATRIBUTOS_PELIGROSOS:
                       result.agregar_error(
                           f"Atributo peligroso detectado: '.{nodo.attr}'. "
                           f"Acceso a internos de Python no está permitido."
                       )

       # ─── Análisis de estructura ───────────────────────────────────────────────

       def _analizar_estructura(self, arbol: ast.AST, result: ValidationResult) -> None:
           """Verifica que el código define la variable 'grafo'."""
           tiene_variable_grafo = False

           for nodo in ast.walk(arbol):
               if isinstance(nodo, ast.Assign):
                   for target in nodo.targets:
                       if isinstance(target, ast.Name) and target.id == "grafo":
                           tiene_variable_grafo = True
                           break

           if not tiene_variable_grafo:
               result.agregar_error(
                   "El código no define la variable 'grafo'. "
                   "Debe asignar el YeyoGrafo a una variable llamada exactamente 'grafo'."
               )

       # ─── Análisis de uso de nodos del catálogo ────────────────────────────────

       def _analizar_uso_de_nodos(self, arbol: ast.AST, result: ValidationResult) -> None:
           """
           Verifica que solo se usen nodos del catálogo permitido.
           Busca llamadas como catalogo.obtener("nodo_x") y verifica el nodo_x.
           """
           if not self.nodos_permitidos:
               return

           for nodo in ast.walk(arbol):
               if (isinstance(nodo, ast.Call)
                       and isinstance(nodo.func, ast.Attribute)
                       and nodo.func.attr == "obtener"
                       and nodo.args):
                   arg = nodo.args[0]
                   if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                       nodo_id = arg.value
                       if nodo_id not in self.nodos_permitidos:
                           result.agregar_error(
                               f"Nodo '{nodo_id}' no está en el catálogo permitido. "
                               f"Disponibles: {self.nodos_permitidos}"
                           )

2. Actualizar src/orquestador/generador.py — integrar GrafoValidador:

   En src/orquestador/generador.py, MODIFICAR el método _validar_codigo_basico para usar GrafoValidador:

   Ruta: ~/yeyo-os/src/orquestador/generador.py
   MODIFICAR (agregar al inicio de la clase GeneradorGrafos, después de los imports):

   Agregar import al inicio del archivo:
   from .validador import GrafoValidador, ValidationResult

   Reemplazar el método _validar_codigo_basico() con:

       def _validar_codigo_completo(self, codigo: str) -> None:
           """
           Validación completa con AST via GrafoValidador.
           Reemplaza la validación básica de strings.
           """
           nodos_permitidos = self.catalogo.listar()
           validador = GrafoValidador(nodos_permitidos=nodos_permitidos)
           resultado = validador.validar(codigo)
           if not resultado.is_valid:
               errores_str = "; ".join(resultado.errores)
               raise GeneradorGrafosError(
                   f"Código inválido ({len(resultado.errores)} errores): {errores_str}"
               )

   En el método generar(), cambiar self._validar_codigo_basico(codigo_limpio) por:
       self._validar_codigo_completo(codigo_limpio)

3. Actualizar src/orquestador/__init__.py:

   Ruta: ~/yeyo-os/src/orquestador/__init__.py
   Contenido:
   """
   YeyoOS — YeyoOrquestador
   Motor de orquestación nativo de YeyoOS.
   Micro-fases 4.14-4.23 + 5.22-5.25 — Capas 4-5
   """
   from .estado import EstadoGrafo, EstadoGrafoError
   from .nodo import Nodo, NodoFuncion, NodoInline, NodoError, NodoTimeoutError, nodo
   from .edge import Edge, EdgeDirecto, EdgeCondicional, EdgeError, FIN_GRAFO, edge
   from .grafo import YeyoGrafo, ResultadoGrafo, GrafoError, GrafoTimeoutError
   from .paralelo import NodoParalelo
   from .orquestador import YeyoOrquestador, RespuestaOrquestador, OrquestadorError
   from .catalogo import CatalogoNodos, CatalogoError
   from .eventos import GraphEventEmitter, crear_evento_grafo
   from .checkpoint import GrafoCheckpoint, CheckpointError
   from .cache import NodoCache, CacheError
   from .generador import GeneradorGrafos, GeneradorGrafosError
   from .validador import GrafoValidador, ValidationResult

4. Crear archivo tests/unit/orquestador/test_validador.py:

   Ruta: ~/yeyo-os/tests/unit/orquestador/test_validador.py
   Contenido:

   """Tests para GrafoValidador con análisis AST — Micro-fase 5.25"""

   import pytest
   from src.orquestador.validador import GrafoValidador, ValidationResult


   # ─── Código válido de referencia ──────────────────────────────────────────

   CODIGO_VALIDO = '''
async def fn_nodo(estado):
    estado.salida["resultado"] = "ok"
    return estado

nodo_test = NodoFuncion(id="paso1", fn=fn_nodo, timeout=30.0)
grafo = (
    YeyoGrafo("grafo_valido", "Grafo de prueba")
    .agregar_nodo(nodo_test)
    .inicio("paso1")
    .fin("paso1")
)
'''


   class TestValidacionCodeValido:

       def test_codigo_valido_pasa(self):
           v = GrafoValidador()
           result = v.validar(CODIGO_VALIDO)
           assert result.is_valid is True
           assert len(result.errores) == 0

       def test_codigo_vacio_falla(self):
           v = GrafoValidador()
           result = v.validar("")
           assert result.is_valid is False

       def test_codigo_con_solo_espacio_falla(self):
           v = GrafoValidador()
           result = v.validar("   \n  ")
           assert result.is_valid is False

       def test_validation_result_tiene_errores(self):
           v = GrafoValidador()
           result = v.validar("")
           assert isinstance(result.errores, list)
           assert isinstance(result.advertencias, list)


   class TestValidacionImports:

       def test_import_os_rechazado(self):
           v = GrafoValidador()
           result = v.validar("import os\ngrafo = YeyoGrafo('x', 'y')")
           assert result.is_valid is False
           assert any("os" in e for e in result.errores)

       def test_import_sys_rechazado(self):
           v = GrafoValidador()
           result = v.validar("import sys\ngrafo = YeyoGrafo('x', 'y')")
           assert result.is_valid is False

       def test_import_subprocess_rechazado(self):
           v = GrafoValidador()
           result = v.validar("import subprocess\ngrafo = YeyoGrafo('x', 'y')")
           assert result.is_valid is False

       def test_from_os_import_rechazado(self):
           v = GrafoValidador()
           result = v.validar("from os import system\ngrafo = YeyoGrafo('x', 'y')")
           assert result.is_valid is False

       def test_import_orquestador_permitido(self):
           v = GrafoValidador()
           result = v.validar(
               "from src.orquestador.nodo import NodoFuncion\n"
               "grafo = YeyoGrafo('x', 'y')"
           )
           # No debe haber errores de import
           errores_import = [e for e in result.errores if "Import prohibido" in e]
           assert len(errores_import) == 0

       def test_import_socket_rechazado(self):
           v = GrafoValidador()
           result = v.validar("import socket\ngrafo = YeyoGrafo('x', 'y')")
           assert result.is_valid is False

       def test_import_requests_rechazado(self):
           v = GrafoValidador()
           result = v.validar("import requests\ngrafo = YeyoGrafo('x', 'y')")
           assert result.is_valid is False


   class TestValidacionBuiltins:

       def test_eval_rechazado(self):
           v = GrafoValidador()
           result = v.validar("x = eval('1+1')\ngrafo = YeyoGrafo('x', 'y')")
           assert result.is_valid is False
           assert any("eval" in e for e in result.errores)

       def test_exec_rechazado(self):
           v = GrafoValidador()
           result = v.validar("exec('print(1)')\ngrafo = YeyoGrafo('x', 'y')")
           assert result.is_valid is False
           assert any("exec" in e for e in result.errores)

       def test_compile_rechazado(self):
           v = GrafoValidador()
           result = v.validar("c = compile('x=1', '', 'exec')\ngrafo = YeyoGrafo('x', 'y')")
           assert result.is_valid is False

       def test_open_rechazado(self):
           v = GrafoValidador()
           result = v.validar("f = open('/etc/passwd')\ngrafo = YeyoGrafo('x', 'y')")
           assert result.is_valid is False

       def test_dunder_import_rechazado(self):
           v = GrafoValidador()
           result = v.validar(
               "m = __import__('os')\ngrafo = YeyoGrafo('x', 'y')"
           )
           assert result.is_valid is False


   class TestValidacionAtributos:

       def test_dunder_class_rechazado(self):
           v = GrafoValidador()
           result = v.validar(
               "x = YeyoGrafo.__class__\ngrafo = YeyoGrafo('x', 'y')"
           )
           assert result.is_valid is False

       def test_dunder_subclasses_rechazado(self):
           v = GrafoValidador()
           result = v.validar(
               "x = object.__subclasses__()\ngrafo = YeyoGrafo('x', 'y')"
           )
           assert result.is_valid is False

       def test_dunder_globals_rechazado(self):
           v = GrafoValidador()
           result = v.validar(
               "x = fn.__globals__\ngrafo = YeyoGrafo('x', 'y')"
           )
           assert result.is_valid is False


   class TestValidacionEstructura:

       def test_sin_variable_grafo_falla(self):
           v = GrafoValidador()
           result = v.validar("x = 42\ny = 'hola'")
           assert result.is_valid is False
           assert any("grafo" in e.lower() for e in result.errores)

       def test_con_variable_grafo_pasa(self):
           v = GrafoValidador()
           result = v.validar("grafo = YeyoGrafo('mi_grafo', 'desc')")
           assert result.is_valid is True

       def test_error_sintaxis_falla(self):
           v = GrafoValidador()
           result = v.validar("def fn(:\n    pass")
           assert result.is_valid is False
           assert any("sintaxis" in e.lower() for e in result.errores)


   class TestValidacionNodosCatalogo:

       def test_nodo_del_catalogo_aceptado(self):
           v = GrafoValidador(nodos_permitidos=["nodo_chat", "nodo_log"])
           result = v.validar(
               'nodo = catalogo.obtener("nodo_chat")\n'
               'grafo = YeyoGrafo("g", "d")'
           )
           assert result.is_valid is True

       def test_nodo_fuera_del_catalogo_rechazado(self):
           v = GrafoValidador(nodos_permitidos=["nodo_chat"])
           result = v.validar(
               'nodo = catalogo.obtener("nodo_secreto")\n'
               'grafo = YeyoGrafo("g", "d")'
           )
           assert result.is_valid is False
           assert any("nodo_secreto" in e for e in result.errores)

       def test_sin_nodos_permitidos_no_valida_nodos(self):
           v = GrafoValidador(nodos_permitidos=None)
           result = v.validar(
               'nodo = catalogo.obtener("cualquier_nodo")\n'
               'grafo = YeyoGrafo("g", "d")'
           )
           # Sin lista de permitidos, no valida nodos
           assert result.is_valid is True


   class TestValidationResultHelper:

       def test_agregar_error_marca_invalido(self):
           r = ValidationResult(is_valid=True)
           r.agregar_error("Error de prueba")
           assert r.is_valid is False
           assert len(r.errores) == 1

       def test_agregar_advertencia_no_invalida(self):
           r = ValidationResult(is_valid=True)
           r.agregar_advertencia("Advertencia de prueba")
           assert r.is_valid is True
           assert len(r.advertencias) == 1

       def test_repr_informativo(self):
           r = ValidationResult(is_valid=False, errores=["e1", "e2"])
           assert "is_valid=False" in repr(r)
           assert "errores=2" in repr(r)

5. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/orquestador/test_validador.py -v

VERIFICAR:
- [ ] src/orquestador/validador.py existe con GrafoValidador y ValidationResult
- [ ] import os, sys, subprocess, socket, requests — todos rechazados
- [ ] eval(), exec(), compile(), __import__(), open() — todos rechazados
- [ ] __class__, __subclasses__, __globals__ — todos rechazados
- [ ] Código sin variable "grafo" rechazado
- [ ] Error de sintaxis Python detectado y reportado
- [ ] Nodos fuera del catálogo rechazados (si se pasa nodos_permitidos)
- [ ] Código válido acepta sin falsos positivos
- [ ] TODOS los tests pasan

SI FALLA:
- ast.parse falla en Python 3.8: verificar que usa ast.walk correctamente
- Falsos positivos en imports: verificar que solo se bloquea el módulo raíz, no subpaths
- ValidationResult.agregar_error no marca is_valid=False: verificar la implementación

NO HACER:
- No reemplazar todo GeneradorGrafos — solo integrar el validador
- No usar RestrictedPython (requiere instalación extra) — ast es suficiente
- No implementar sandboxing a nivel de OS (seccomp, namespaces) — eso es responsabilidad de Podman/Capa 4

GATE: Código malicioso rechazado con errores descriptivos, código válido aceptado sin falsos positivos, todos los tests pasan.
```
