## ═══════════════════════════════════════
## MICRO-FASE 5.24 — GeneradorGrafos (IA genera grafos)
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 5.24-1 [VSCODE] — GeneradorGrafos: IA genera código Python de grafos desde descripción

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 5.24 de Capa 5 (Órganos): crear el GeneradorGrafos que permite a la IA generar nuevos YeyoGrafos a partir de una descripción en lenguaje natural.

CONTEXTO:
- Micro-fases 5.22-5.23 completadas: GrafoCheckpoint y NodoCache
- CatalogoNodos en src/orquestador/catalogo.py con 5 nodos base
- GrafoValidador se implementará en micro-fase 5.25 — para esta micro-fase, usar un validador simplificado inline
- Flujo: descripcion → Ollama genera código Python → validar → exec() seguro → retornar YeyoGrafo
- Los grafos generados se guardan en Flash Memory (tipo="grafo_generado", importancia=0.9)
- Los grafos generados se ejecutan SIEMPRE en sandbox (L5)
- El código generado SOLO puede usar nodos del catálogo + YeyoGrafo + clases del orquestador

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/orquestador/generador.py:

   Ruta: ~/yeyo-os/src/orquestador/generador.py
   Contenido:

   """
   YeyoOS — GeneradorGrafos
   Micro-fase 5.24 — Capa 5: Órganos

   Permite a la IA generar YeyoGrafos desde descripción de lenguaje natural.
   Los grafos generados solo pueden usar nodos del catálogo registrado.
   Se ejecutan siempre en sandbox (nivel de privilegio L5).
   """

   import json
   import re
   from datetime import datetime, timezone
   from typing import Optional, Any

   from .estado import EstadoGrafo
   from .grafo import YeyoGrafo
   from .catalogo import CatalogoNodos


   TIPO_GRAFO_GENERADO = "grafo_generado"
   IMPORTANCIA_GRAFO_GENERADO = 0.9

   # Prompt para que Ollama genere el grafo
   PROMPT_GENERADOR = """Eres un experto en YeyoOS, un OS AI-nativo.
Tu tarea es generar código Python para un YeyoGrafo basándote en la descripción del usuario.

NODOS DISPONIBLES EN EL CATÁLOGO (solo puedes usar estos):
{nodos_disponibles}

FORMATO DEL GRAFO (OBLIGATORIO):
```python
from src.orquestador import YeyoGrafo
from src.orquestador.nodo import NodoFuncion

# Definir función del nodo
async def fn_paso1(estado):
    # lógica aquí
    estado.salida["resultado"] = "valor"
    return estado

# Crear nodos del catálogo
nodo_paso1 = NodoFuncion(id="paso1", fn=fn_paso1, timeout=30.0)

# Construir grafo
grafo = (
    YeyoGrafo("nombre_del_grafo", "descripción del grafo")
    .agregar_nodo(nodo_paso1)
    .inicio("paso1")
    .fin("paso1")
)
```

RESTRICCIONES ABSOLUTAS:
- Solo usar NodoFuncion para nodos personalizados
- Los nodos del catálogo se obtienen con: catalogo.obtener("nombre_nodo")
- NO usar imports excepto los ya disponibles
- NO usar eval, exec, __import__, os.system, subprocess
- NO usar bucles infinitos ni recursión
- El código debe ser Python válido y ejecutable
- La variable final debe llamarse exactamente: grafo

DESCRIPCIÓN DEL USUARIO: {descripcion}

Responde SOLO con el código Python del grafo, sin explicaciones adicionales."""


   class GeneradorGrafosError(Exception):
       """Error en el GeneradorGrafos."""
       pass


   class GeneradorGrafos:
       """
       Genera YeyoGrafos desde descripción de lenguaje natural usando Ollama.

       Flujo:
       1. Construir prompt con descripción + catálogo de nodos
       2. Llamar a Ollama para generar código Python
       3. Validar el código (imports peligrosos, estructura básica)
       4. Ejecutar en sandbox limitado
       5. Guardar en Flash Memory
       6. Retornar YeyoGrafo listo para usar
       """

       def __init__(
           self,
           ollama_provider: Any,
           flash_memory: Optional[Any] = None,
           catalogo: Optional[CatalogoNodos] = None,
       ):
           self._ollama = ollama_provider
           self._flash = flash_memory
           self.catalogo = catalogo or CatalogoNodos(
               ollama_provider=ollama_provider,
               flash_memory=flash_memory,
           )
           self.grafos_generados: list[dict] = []  # historial en memoria

       async def generar(
           self,
           descripcion: str,
           usuario_id: str = "anonimo",
           nombre_sugerido: Optional[str] = None,
       ) -> YeyoGrafo:
           """
           Genera un YeyoGrafo desde descripción de lenguaje natural.

           Args:
               descripcion: qué debe hacer el grafo en lenguaje natural
               usuario_id: quién solicita el grafo (para Flash Memory)
               nombre_sugerido: nombre sugerido para el ID del grafo

           Returns:
               YeyoGrafo listo para ejecutar

           Raises:
               GeneradorGrafosError: si el código generado es inválido
           """
           if not descripcion.strip():
               raise GeneradorGrafosError("La descripción no puede estar vacía")

           # Generar código con Ollama
           codigo_generado = await self._llamar_ollama(descripcion)

           # Extraer código Python del bloque markdown si viene así
           codigo_limpio = self._extraer_codigo(codigo_generado)

           # Validación básica de seguridad
           self._validar_codigo_basico(codigo_limpio)

           # Ejecutar en sandbox
           grafo = self._ejecutar_en_sandbox(codigo_limpio)

           if not isinstance(grafo, YeyoGrafo):
               raise GeneradorGrafosError(
                   "El código generado no produjo un YeyoGrafo válido. "
                   f"Tipo obtenido: {type(grafo).__name__}"
               )

           # Guardar en Flash Memory
           grafo_id = grafo.id
           await self._guardar_en_flash(descripcion, codigo_limpio, grafo_id, usuario_id)

           self.grafos_generados.append({
               "id": grafo_id,
               "descripcion": descripcion,
               "usuario_id": usuario_id,
               "timestamp": datetime.now(timezone.utc).isoformat(),
           })

           return grafo

       async def listar_generados(self, usuario_id: str = "anonimo") -> list[dict]:
           """
           Lista los grafos generados por un usuario desde Flash Memory.
           """
           if not self._flash:
               return [g for g in self.grafos_generados if g.get("usuario_id") == usuario_id]

           try:
               resultados = await self._flash.buscar(
                   query=f"usuario_id:{usuario_id}",
                   tipo=TIPO_GRAFO_GENERADO,
                   limite=50,
               )
               grafos = []
               for r in resultados:
                   try:
                       contenido = r.get("contenido", "")
                       if isinstance(contenido, str):
                           data = json.loads(contenido)
                       elif isinstance(contenido, dict):
                           data = contenido
                       else:
                           continue
                       if data.get("usuario_id") == usuario_id:
                           grafos.append(data)
                   except Exception:
                       continue
               return grafos
           except Exception:
               return []

       async def _llamar_ollama(self, descripcion: str) -> str:
           """Llama a Ollama para generar el código del grafo."""
           nodos_disponibles = "\n".join([
               f"- {nodo_id}: {desc}"
               for nodo_id, desc in self.catalogo.describir().items()
           ])

           prompt = PROMPT_GENERADOR.format(
               nodos_disponibles=nodos_disponibles,
               descripcion=descripcion,
           )

           try:
               respuesta = await self._ollama.chat(messages=[
                   {"role": "user", "content": prompt}
               ])
               if hasattr(respuesta, "content"):
                   return respuesta.content
               elif isinstance(respuesta, dict):
                   return respuesta.get("content", "")
               return str(respuesta)
           except Exception as e:
               raise GeneradorGrafosError(f"Error al llamar a Ollama: {e}") from e

       def _extraer_codigo(self, texto: str) -> str:
           """Extrae el bloque de código Python del texto de Ollama."""
           # Buscar bloque ```python ... ```
           patron = r"```python\s*(.*?)\s*```"
           match = re.search(patron, texto, re.DOTALL)
           if match:
               return match.group(1).strip()

           # Buscar bloque ``` ... ```
           patron2 = r"```\s*(.*?)\s*```"
           match2 = re.search(patron2, texto, re.DOTALL)
           if match2:
               return match2.group(1).strip()

           # Asumir que todo el texto es código
           return texto.strip()

       def _validar_codigo_basico(self, codigo: str) -> None:
           """
           Validación básica de seguridad del código generado.
           Para validación completa con AST, ver micro-fase 5.25 (GrafoValidador).
           """
           imports_peligrosos = [
               "import os", "import sys", "import subprocess",
               "import shutil", "import socket", "import requests",
               "__import__", "importlib",
           ]
           patrones_peligrosos = [
               r"\beval\s*\(", r"\bexec\s*\(", r"\bcompile\s*\(",
               r"os\.system", r"os\.popen", r"subprocess\.",
               r"__import__\s*\(",
           ]

           for imp_peligroso in imports_peligrosos:
               if imp_peligroso in codigo:
                   raise GeneradorGrafosError(
                       f"Código peligroso detectado: '{imp_peligroso}' no está permitido"
                   )

           for patron in patrones_peligrosos:
               if re.search(patron, codigo):
                   raise GeneradorGrafosError(
                       f"Patrón peligroso detectado: '{patron}'"
                   )

           if "grafo" not in codigo:
               raise GeneradorGrafosError(
                   "El código debe definir una variable llamada 'grafo'"
               )

       def _ejecutar_en_sandbox(self, codigo: str) -> YeyoGrafo:
           """
           Ejecuta el código en un sandbox con globals limitados.
           Solo expone las clases necesarias del orquestador.
           """
           from .nodo import NodoFuncion, NodoInline
           from .edge import EdgeDirecto, EdgeCondicional

           globals_sandbox = {
               "__builtins__": {
                   "print": print,
                   "len": len,
                   "str": str,
                   "int": int,
                   "float": float,
                   "bool": bool,
                   "list": list,
                   "dict": dict,
                   "tuple": tuple,
                   "set": set,
                   "None": None,
                   "True": True,
                   "False": False,
                   "isinstance": isinstance,
                   "hasattr": hasattr,
                   "getattr": getattr,
               },
               "YeyoGrafo": YeyoGrafo,
               "NodoFuncion": NodoFuncion,
               "NodoInline": NodoInline,
               "EdgeDirecto": EdgeDirecto,
               "EdgeCondicional": EdgeCondicional,
               "EstadoGrafo": EstadoGrafo,
               "catalogo": self.catalogo,
           }

           locals_sandbox: dict = {}

           try:
               exec(codigo, globals_sandbox, locals_sandbox)
           except Exception as e:
               raise GeneradorGrafosError(f"Error ejecutando código generado: {e}") from e

           grafo = locals_sandbox.get("grafo") or globals_sandbox.get("grafo")
           if grafo is None:
               raise GeneradorGrafosError(
                   "El código no definió la variable 'grafo'"
               )
           return grafo

       async def _guardar_en_flash(
           self,
           descripcion: str,
           codigo: str,
           grafo_id: str,
           usuario_id: str,
       ) -> None:
           """Guarda el grafo generado en Flash Memory."""
           if not self._flash:
               return
           try:
               data = {
                   "grafo_id": grafo_id,
                   "descripcion": descripcion,
                   "codigo": codigo,
                   "usuario_id": usuario_id,
                   "tipo": TIPO_GRAFO_GENERADO,
                   "generado_en": datetime.now(timezone.utc).isoformat(),
               }
               await self._flash.guardar(
                   dato=json.dumps(data, ensure_ascii=False),
                   metadata={
                       "tipo": TIPO_GRAFO_GENERADO,
                       "grafo_id": grafo_id,
                       "usuario_id": usuario_id,
                       "importancia": IMPORTANCIA_GRAFO_GENERADO,
                   }
               )
           except Exception:
               pass  # Fallos de flash no interrumpen la generación

2. Actualizar src/orquestador/__init__.py:

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

3. Crear archivo tests/unit/orquestador/test_generador.py:

   Ruta: ~/yeyo-os/tests/unit/orquestador/test_generador.py
   Contenido:

   """Tests para GeneradorGrafos — Micro-fase 5.24"""

   import pytest
   from unittest.mock import AsyncMock, MagicMock
   from src.orquestador.grafo import YeyoGrafo
   from src.orquestador.generador import GeneradorGrafos, GeneradorGrafosError


   # ─── Mock de Ollama ────────────────────────────────────────────────────────

   CODIGO_GRAFO_SIMPLE = '''
from src.orquestador.nodo import NodoFuncion

async def fn_nodo(estado):
    estado.salida["ok"] = True
    return estado

nodo_test = NodoFuncion(id="nodo_generado", fn=fn_nodo, timeout=30.0)
grafo = (
    YeyoGrafo("grafo_generado_ia", "Grafo generado por IA")
    .agregar_nodo(nodo_test)
    .inicio("nodo_generado")
    .fin("nodo_generado")
)
'''

   CODIGO_CON_EVAL = '''
grafo = eval("YeyoGrafo('malicioso', 'malo')")
'''

   CODIGO_CON_OS = '''
import os
os.system("rm -rf /")
grafo = YeyoGrafo("hack", "hack")
'''

   CODIGO_SIN_GRAFO = '''
x = 42
'''


   def mock_ollama_genera_codigo(codigo: str):
       m = AsyncMock()
       resp = MagicMock()
       resp.content = f"```python\n{codigo}\n```"
       m.chat = AsyncMock(return_value=resp)
       return m


   def mock_flash_memory():
       m = AsyncMock()
       m.guardar = AsyncMock(return_value="mem-gen-001")
       m.buscar = AsyncMock(return_value=[])
       return m


   class TestGeneradorGrafosBasico:

       @pytest.mark.asyncio
       async def test_generar_produce_yeyo_grafo(self):
           ollama = mock_ollama_genera_codigo(CODIGO_GRAFO_SIMPLE)
           gen = GeneradorGrafos(ollama)
           grafo = await gen.generar("Un grafo simple que guarda ok=True")
           assert isinstance(grafo, YeyoGrafo)

       @pytest.mark.asyncio
       async def test_grafo_generado_tiene_id_correcto(self):
           ollama = mock_ollama_genera_codigo(CODIGO_GRAFO_SIMPLE)
           gen = GeneradorGrafos(ollama)
           grafo = await gen.generar("Grafo de prueba")
           assert grafo.id == "grafo_generado_ia"

       @pytest.mark.asyncio
       async def test_grafo_generado_es_ejecutable(self):
           ollama = mock_ollama_genera_codigo(CODIGO_GRAFO_SIMPLE)
           gen = GeneradorGrafos(ollama)
           grafo = await gen.generar("Grafo ejecutable")
           resultado = await grafo.ejecutar({})
           assert resultado.exito is True
           assert resultado.estado_final.salida.get("ok") is True

       @pytest.mark.asyncio
       async def test_descripcion_vacia_falla(self):
           ollama = mock_ollama_genera_codigo(CODIGO_GRAFO_SIMPLE)
           gen = GeneradorGrafos(ollama)
           with pytest.raises(GeneradorGrafosError):
               await gen.generar("")

       @pytest.mark.asyncio
       async def test_guarda_en_flash_memory(self):
           ollama = mock_ollama_genera_codigo(CODIGO_GRAFO_SIMPLE)
           flash = mock_flash_memory()
           gen = GeneradorGrafos(ollama, flash_memory=flash)
           await gen.generar("Grafo con memoria")
           flash.guardar.assert_called_once()

       @pytest.mark.asyncio
       async def test_grafo_agregado_a_historial_interno(self):
           ollama = mock_ollama_genera_codigo(CODIGO_GRAFO_SIMPLE)
           gen = GeneradorGrafos(ollama)
           await gen.generar("Primero", usuario_id="u1")
           await gen.generar("Segundo", usuario_id="u1")
           assert len(gen.grafos_generados) == 2

       @pytest.mark.asyncio
       async def test_listar_generados_retorna_lista(self):
           ollama = mock_ollama_genera_codigo(CODIGO_GRAFO_SIMPLE)
           gen = GeneradorGrafos(ollama)
           await gen.generar("Grafo 1", usuario_id="u1")
           lista = await gen.listar_generados("u1")
           assert isinstance(lista, list)


   class TestGeneradorGrafosSeguridad:

       @pytest.mark.asyncio
       async def test_rechaza_codigo_con_eval(self):
           ollama = mock_ollama_genera_codigo(CODIGO_CON_EVAL)
           gen = GeneradorGrafos(ollama)
           with pytest.raises(GeneradorGrafosError, match="peligroso"):
               await gen.generar("Grafo malicioso")

       @pytest.mark.asyncio
       async def test_rechaza_codigo_con_import_os(self):
           ollama = mock_ollama_genera_codigo(CODIGO_CON_OS)
           gen = GeneradorGrafos(ollama)
           with pytest.raises(GeneradorGrafosError, match="peligroso"):
               await gen.generar("Grafo con os")

       @pytest.mark.asyncio
       async def test_rechaza_codigo_sin_variable_grafo(self):
           ollama = mock_ollama_genera_codigo(CODIGO_SIN_GRAFO)
           gen = GeneradorGrafos(ollama)
           with pytest.raises(GeneradorGrafosError):
               await gen.generar("Código sin grafo")

       @pytest.mark.asyncio
       async def test_rechaza_codigo_con_exec(self):
           codigo_con_exec = 'exec("malicioso")\ngrafo = YeyoGrafo("x", "x")'
           ollama = mock_ollama_genera_codigo(codigo_con_exec)
           gen = GeneradorGrafos(ollama)
           with pytest.raises(GeneradorGrafosError, match="peligroso"):
               await gen.generar("Grafo con exec")

       @pytest.mark.asyncio
       async def test_sandbox_no_tiene_acceso_a_os(self):
           codigo_sandbox_test = '''
grafo = YeyoGrafo("sandbox_test", "prueba sandbox")
try:
    import os  # intento de import
except:
    pass
'''
           ollama = mock_ollama_genera_codigo(codigo_sandbox_test)
           gen = GeneradorGrafos(ollama)
           # El import os está en la lista negra textual
           with pytest.raises(GeneradorGrafosError):
               await gen.generar("Test sandbox")


   class TestGeneradorGrafosExtraerCodigo:

       def test_extrae_codigo_de_bloque_markdown_python(self):
           gen = GeneradorGrafos(AsyncMock())
           texto = "Aquí está el código:\n```python\ngrafo = YeyoGrafo('x', 'y')\n```"
           codigo = gen._extraer_codigo(texto)
           assert "grafo" in codigo
           assert "```" not in codigo

       def test_extrae_codigo_de_bloque_markdown_generico(self):
           gen = GeneradorGrafos(AsyncMock())
           texto = "```\ngrafo = YeyoGrafo('x', 'y')\n```"
           codigo = gen._extraer_codigo(texto)
           assert "grafo" in codigo

       def test_retorna_texto_completo_si_no_hay_bloque(self):
           gen = GeneradorGrafos(AsyncMock())
           texto = "grafo = YeyoGrafo('x', 'y')"
           codigo = gen._extraer_codigo(texto)
           assert codigo == texto

4. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/orquestador/test_generador.py -v

VERIFICAR:
- [ ] src/orquestador/generador.py existe con GeneradorGrafos
- [ ] generar() retorna YeyoGrafo ejecutable
- [ ] Código con eval, exec, import os — rechazado con GeneradorGrafosError
- [ ] Código sin variable "grafo" — rechazado
- [ ] Sandbox limita acceso a globals peligrosos
- [ ] Grafo generado se guarda en Flash Memory
- [ ] listar_generados() retorna lista de grafos del usuario
- [ ] _extraer_codigo() maneja bloques markdown ```python y ``` ```
- [ ] TODOS los tests pasan

SI FALLA:
- exec() en sandbox falla con NameError en NodoFuncion: verificar que globals_sandbox incluye NodoFuncion
- El grafo generado importa módulos: la validación básica debe capturarlo antes del exec
- Flash Memory no guarda: verificar que el try/except no silencia el error en tests

NO HACER:
- No implementar GrafoValidador completo con AST (eso es micro-fase 5.25)
- No conectar con Ollama real — solo mock en tests
- No implementar empaquetado como .ypkg (sería un paso posterior)

GATE: GeneradorGrafos produce grafos válidos desde descripción de texto, rechaza código peligroso (eval, exec, import os), sandbox limita globals, todos los tests pasan.
```
