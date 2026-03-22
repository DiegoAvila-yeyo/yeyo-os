## ═══════════════════════════════════════
## MICRO-FASE 4.19 — YeyoOrquestador + Ollama Tool Calling
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 4.19-1 [VSCODE] — YeyoOrquestador que registra grafos como tools de Ollama

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 4.19 de Capa 4 (Sistema Nervioso): crear YeyoOrquestador que integra YeyoGrafo con Ollama tool calling — Ollama elige qué grafo ejecutar según el mensaje del usuario.

CONTEXTO:
- Micro-fases 4.14-4.18 completadas: EstadoGrafo, Nodo, Edge, YeyoGrafo, NodoParalelo
- OllamaProvider existente en src/ia/ollama_provider.py (interfaz IAProvider)
- OllamaProvider.chat() acepta messages y tools para tool calling
- Formato de tool para Ollama: {"type": "function", "function": {"name", "description", "parameters"}}
- YeyoOrquestador.registrar_grafo(grafo): lo agrega al registro interno
- YeyoOrquestador.registrar_grafo_como_tool(grafo): lo registra para que Ollama lo pueda invocar
- YeyoOrquestador.procesar(mensaje, contexto): Ollama decide qué grafo ejecutar
- Si Ollama retorna tool_call, ejecuta el grafo correspondiente
- Si Ollama no retorna tool_call, retorna la respuesta textual directamente

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/orquestador/orquestador.py:

   Ruta: ~/yeyo-os/src/orquestador/orquestador.py
   Contenido:

   """
   YeyoOS — YeyoOrquestador
   Micro-fase 4.19 — Capa 4: Sistema Nervioso

   Conecta YeyoGrafo con Ollama tool calling.
   Ollama analiza el mensaje y decide qué grafo ejecutar.
   """

   import json
   from typing import Optional, Any

   from .estado import EstadoGrafo
   from .grafo import YeyoGrafo, ResultadoGrafo


   class OrquestadorError(Exception):
       """Error en el YeyoOrquestador."""
       pass


   class RespuestaOrquestador:
       """Respuesta del YeyoOrquestador al procesar un mensaje."""

       def __init__(
           self,
           texto: str,
           grafo_ejecutado: Optional[str] = None,
           resultado_grafo: Optional[ResultadoGrafo] = None,
           exito: bool = True,
       ):
           self.texto = texto
           self.grafo_ejecutado = grafo_ejecutado
           self.resultado_grafo = resultado_grafo
           self.exito = exito

       def __repr__(self) -> str:
           return (
               f"RespuestaOrquestador("
               f"grafo={self.grafo_ejecutado!r}, "
               f"exito={self.exito}, "
               f"texto={self.texto[:50]!r})"
           )


   class YeyoOrquestador:
       """
       Orquestador central de YeyoOS.

       Registra grafos como tools de Ollama.
       Cuando el usuario envía un mensaje, Ollama decide qué grafo ejecutar.
       Si no hay tool_call, retorna la respuesta textual de Ollama directamente.
       """

       def __init__(self, ollama_provider: Any, modelo: str = "llama3.2"):
           """
           Args:
               ollama_provider: instancia de OllamaProvider (o mock)
               modelo: nombre del modelo Ollama a usar
           """
           self._ollama = ollama_provider
           self.modelo = modelo
           self._grafos: dict[str, YeyoGrafo] = {}
           self._tools: dict[str, dict] = {}  # {grafo_id: tool_definition}

       # ─── Registro de grafos ───────────────────────────────────────────────────

       def registrar_grafo(self, grafo: YeyoGrafo) -> "YeyoOrquestador":
           """Registra un grafo para ejecución directa (sin tool calling)."""
           self._grafos[grafo.id] = grafo
           return self

       def registrar_grafo_como_tool(self, grafo: YeyoGrafo) -> "YeyoOrquestador":
           """
           Registra un grafo como tool de Ollama.
           Ollama podrá invocar este grafo automáticamente.
           """
           self.registrar_grafo(grafo)
           tool_def = self._grafo_a_tool(grafo)
           self._tools[grafo.id] = tool_def
           return self

       def _grafo_a_tool(self, grafo: YeyoGrafo) -> dict:
           """Convierte un YeyoGrafo en la definición de tool para Ollama."""
           return {
               "type": "function",
               "function": {
                   "name": grafo.id,
                   "description": grafo.descripcion or f"Ejecutar el grafo {grafo.id}",
                   "parameters": {
                       "type": "object",
                       "properties": {
                           "entrada": {
                               "type": "string",
                               "description": "Instrucción o dato de entrada para el grafo"
                           }
                       },
                       "required": ["entrada"],
                   },
               },
           }

       def listar_grafos(self) -> list[str]:
           """Lista los IDs de todos los grafos registrados."""
           return list(self._grafos.keys())

       def listar_tools(self) -> list[str]:
           """Lista los IDs de grafos registrados como tools."""
           return list(self._tools.keys())

       # ─── Procesamiento ────────────────────────────────────────────────────────

       async def procesar(
           self,
           mensaje: str,
           contexto: Optional[dict] = None,
           on_evento: Optional[Any] = None,
       ) -> RespuestaOrquestador:
           """
           Procesa un mensaje:
           1. Llama a Ollama con los tools registrados
           2. Si Ollama retorna tool_call → ejecuta el grafo correspondiente
           3. Si no hay tool_call → retorna la respuesta textual
           """
           contexto = contexto or {}

           messages = self._construir_messages(mensaje, contexto)
           tools = list(self._tools.values()) if self._tools else None

           try:
               respuesta_ollama = await self._llamar_ollama(messages, tools)
           except Exception as e:
               raise OrquestadorError(f"Error al llamar a Ollama: {e}") from e

           # Verificar si hay tool_call
           tool_call = self._extraer_tool_call(respuesta_ollama)

           if tool_call:
               return await self._ejecutar_tool_call(tool_call, contexto, on_evento)

           # Sin tool_call: retornar respuesta textual
           texto = self._extraer_texto(respuesta_ollama)
           return RespuestaOrquestador(
               texto=texto,
               grafo_ejecutado=None,
               resultado_grafo=None,
               exito=True,
           )

       async def ejecutar_grafo_directo(
           self,
           grafo_id: str,
           entrada: dict,
           on_evento: Optional[Any] = None,
       ) -> ResultadoGrafo:
           """Ejecuta un grafo directamente por ID, sin pasar por Ollama."""
           if grafo_id not in self._grafos:
               raise OrquestadorError(f"Grafo '{grafo_id}' no registrado")
           grafo = self._grafos[grafo_id]
           return await grafo.ejecutar(entrada, on_evento=on_evento)

       # ─── Helpers privados ─────────────────────────────────────────────────────

       def _construir_messages(self, mensaje: str, contexto: dict) -> list[dict]:
           """Construye la lista de messages para Ollama."""
           messages = []

           # System prompt con contexto
           system_content = "Eres YeyoOS, un asistente AI nativo. Usa los tools disponibles cuando sea apropiado."
           if contexto.get("sistema"):
               system_content = contexto["sistema"]
           messages.append({"role": "system", "content": system_content})

           # Historial si existe
           if "historial" in contexto:
               messages.extend(contexto["historial"])

           # Mensaje del usuario
           messages.append({"role": "user", "content": mensaje})

           return messages

       async def _llamar_ollama(self, messages: list[dict], tools: Optional[list]) -> Any:
           """Llama al OllamaProvider con messages y tools opcionales."""
           kwargs: dict = {"messages": messages}
           if tools:
               kwargs["tools"] = tools
           return await self._ollama.chat(**kwargs)

       def _extraer_tool_call(self, respuesta: Any) -> Optional[dict]:
           """
           Extrae el tool_call de la respuesta de Ollama.
           Formato esperado: respuesta con .tool_calls o dict con "tool_calls"
           """
           # Soportar objeto con atributo tool_calls
           if hasattr(respuesta, "tool_calls") and respuesta.tool_calls:
               tc = respuesta.tool_calls[0]
               if hasattr(tc, "function"):
                   return {
                       "name": tc.function.name,
                       "arguments": tc.function.arguments or {},
                   }

           # Soportar dict
           if isinstance(respuesta, dict):
               tool_calls = respuesta.get("tool_calls") or []
               if tool_calls:
                   tc = tool_calls[0]
                   fn = tc.get("function", {})
                   args = fn.get("arguments", {})
                   if isinstance(args, str):
                       try:
                           args = json.loads(args)
                       except json.JSONDecodeError:
                           args = {"entrada": args}
                   return {"name": fn.get("name", ""), "arguments": args}

           return None

       def _extraer_texto(self, respuesta: Any) -> str:
           """Extrae el texto de la respuesta de Ollama."""
           if hasattr(respuesta, "content"):
               return str(respuesta.content)
           if hasattr(respuesta, "message") and hasattr(respuesta.message, "content"):
               return str(respuesta.message.content)
           if isinstance(respuesta, dict):
               return str(respuesta.get("content") or respuesta.get("message", {}).get("content", ""))
           return str(respuesta)

       async def _ejecutar_tool_call(
           self,
           tool_call: dict,
           contexto: dict,
           on_evento: Optional[Any],
       ) -> RespuestaOrquestador:
           """Ejecuta el grafo correspondiente al tool_call de Ollama."""
           grafo_id = tool_call["name"]
           args = tool_call.get("arguments", {})

           if grafo_id not in self._grafos:
               return RespuestaOrquestador(
                   texto=f"Error: grafo '{grafo_id}' no encontrado",
                   grafo_ejecutado=grafo_id,
                   exito=False,
               )

           entrada = {
               "mensaje": args.get("entrada", ""),
               "contexto_usuario": contexto,
               **args,
           }

           grafo = self._grafos[grafo_id]
           resultado = await grafo.ejecutar(entrada, on_evento=on_evento)

           texto_respuesta = resultado.estado_final.salida.get(
               "respuesta",
               resultado.estado_final.salida.get(
                   "texto",
                   f"Grafo '{grafo_id}' completado"
               )
           )

           return RespuestaOrquestador(
               texto=str(texto_respuesta),
               grafo_ejecutado=grafo_id,
               resultado_grafo=resultado,
               exito=resultado.exito,
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
   from .paralelo import NodoParalelo
   from .orquestador import YeyoOrquestador, RespuestaOrquestador, OrquestadorError

3. Crear archivo tests/unit/orquestador/test_orquestador.py:

   Ruta: ~/yeyo-os/tests/unit/orquestador/test_orquestador.py
   Contenido:

   """Tests para YeyoOrquestador — Micro-fase 4.19"""

   import pytest
   from unittest.mock import AsyncMock, MagicMock, patch
   from src.orquestador.estado import EstadoGrafo
   from src.orquestador.nodo import nodo
   from src.orquestador.grafo import YeyoGrafo
   from src.orquestador.orquestador import YeyoOrquestador, RespuestaOrquestador, OrquestadorError


   # ─── Fixtures ─────────────────────────────────────────────────────────────

   @nodo(id="nodo_chat_test")
   async def nodo_chat_test(estado: EstadoGrafo) -> EstadoGrafo:
       estado.salida["respuesta"] = f"Respuesta a: {estado.entrada.get('mensaje', '')}"
       return estado


   @nodo(id="nodo_imagen_test")
   async def nodo_imagen_test(estado: EstadoGrafo) -> EstadoGrafo:
       estado.salida["respuesta"] = "imagen_generada.png"
       return estado


   def crear_grafo_chat() -> YeyoGrafo:
       return (YeyoGrafo("grafo_chat", "Conversación con el usuario")
               .agregar_nodo(nodo_chat_test)
               .inicio("nodo_chat_test")
               .fin("nodo_chat_test"))


   def crear_grafo_imagen() -> YeyoGrafo:
       return (YeyoGrafo("grafo_imagen", "Genera imágenes con IA")
               .agregar_nodo(nodo_imagen_test)
               .inicio("nodo_imagen_test")
               .fin("nodo_imagen_test"))


   def mock_ollama_sin_tool_call(contenido="Hola, soy YeyoOS"):
       """Mock de OllamaProvider que retorna respuesta textual sin tool_call."""
       mock = AsyncMock()
       respuesta = MagicMock()
       respuesta.tool_calls = None
       respuesta.content = contenido
       mock.chat = AsyncMock(return_value=respuesta)
       return mock


   def mock_ollama_con_tool_call(grafo_id: str, entrada: str = "test"):
       """Mock de OllamaProvider que retorna tool_call para ejecutar un grafo."""
       mock = AsyncMock()
       tool_call_mock = MagicMock()
       tool_call_mock.function.name = grafo_id
       tool_call_mock.function.arguments = {"entrada": entrada}
       respuesta = MagicMock()
       respuesta.tool_calls = [tool_call_mock]
       respuesta.content = ""
       mock.chat = AsyncMock(return_value=respuesta)
       return mock


   class TestYeyoOrquestadorRegistro:

       def test_registrar_grafo(self):
           ollama = mock_ollama_sin_tool_call()
           orq = YeyoOrquestador(ollama)
           orq.registrar_grafo(crear_grafo_chat())
           assert "grafo_chat" in orq.listar_grafos()

       def test_registrar_grafo_como_tool(self):
           ollama = mock_ollama_sin_tool_call()
           orq = YeyoOrquestador(ollama)
           orq.registrar_grafo_como_tool(crear_grafo_chat())
           assert "grafo_chat" in orq.listar_grafos()
           assert "grafo_chat" in orq.listar_tools()

       def test_registrar_grafo_normal_no_en_tools(self):
           ollama = mock_ollama_sin_tool_call()
           orq = YeyoOrquestador(ollama)
           orq.registrar_grafo(crear_grafo_chat())
           assert "grafo_chat" not in orq.listar_tools()

       def test_method_chaining_registro(self):
           ollama = mock_ollama_sin_tool_call()
           result = (YeyoOrquestador(ollama)
                     .registrar_grafo_como_tool(crear_grafo_chat())
                     .registrar_grafo_como_tool(crear_grafo_imagen()))
           assert len(result.listar_tools()) == 2


   class TestYeyoOrquestadorProcesar:

       @pytest.mark.asyncio
       async def test_procesar_sin_tool_call_retorna_texto(self):
           ollama = mock_ollama_sin_tool_call("Hola desde Ollama")
           orq = YeyoOrquestador(ollama)
           orq.registrar_grafo_como_tool(crear_grafo_chat())
           respuesta = await orq.procesar("Hola")
           assert isinstance(respuesta, RespuestaOrquestador)
           assert respuesta.texto == "Hola desde Ollama"
           assert respuesta.grafo_ejecutado is None

       @pytest.mark.asyncio
       async def test_procesar_con_tool_call_ejecuta_grafo(self):
           ollama = mock_ollama_con_tool_call("grafo_chat", "Hola mundo")
           orq = YeyoOrquestador(ollama)
           orq.registrar_grafo_como_tool(crear_grafo_chat())
           respuesta = await orq.procesar("Hola mundo")
           assert respuesta.grafo_ejecutado == "grafo_chat"
           assert respuesta.exito is True

       @pytest.mark.asyncio
       async def test_procesar_tool_call_grafo_imagen(self):
           ollama = mock_ollama_con_tool_call("grafo_imagen", "logo cyberpunk")
           orq = YeyoOrquestador(ollama)
           orq.registrar_grafo_como_tool(crear_grafo_imagen())
           respuesta = await orq.procesar("genera un logo cyberpunk")
           assert respuesta.grafo_ejecutado == "grafo_imagen"
           assert "imagen_generada" in respuesta.texto

       @pytest.mark.asyncio
       async def test_procesar_tool_call_grafo_no_registrado(self):
           ollama = mock_ollama_con_tool_call("grafo_inexistente")
           orq = YeyoOrquestador(ollama)
           respuesta = await orq.procesar("test")
           assert respuesta.exito is False
           assert "grafo_inexistente" in respuesta.texto

       @pytest.mark.asyncio
       async def test_ollama_error_lanza_excepcion(self):
           ollama = AsyncMock()
           ollama.chat = AsyncMock(side_effect=ConnectionError("Ollama no disponible"))
           orq = YeyoOrquestador(ollama)
           with pytest.raises(OrquestadorError):
               await orq.procesar("Hola")

       @pytest.mark.asyncio
       async def test_procesar_pasa_tools_a_ollama(self):
           ollama = mock_ollama_sin_tool_call()
           orq = YeyoOrquestador(ollama)
           orq.registrar_grafo_como_tool(crear_grafo_chat())
           await orq.procesar("test")
           # Verificar que se pasó tools a ollama.chat
           call_kwargs = ollama.chat.call_args.kwargs
           assert "tools" in call_kwargs
           assert len(call_kwargs["tools"]) == 1
           assert call_kwargs["tools"][0]["type"] == "function"

       @pytest.mark.asyncio
       async def test_procesar_sin_tools_no_pasa_tools(self):
           ollama = mock_ollama_sin_tool_call()
           orq = YeyoOrquestador(ollama)  # Sin grafos como tools
           orq.registrar_grafo(crear_grafo_chat())  # Solo registrar, no como tool
           await orq.procesar("test")
           call_kwargs = ollama.chat.call_args.kwargs
           assert call_kwargs.get("tools") is None

       @pytest.mark.asyncio
       async def test_ejecutar_grafo_directo(self):
           ollama = mock_ollama_sin_tool_call()
           orq = YeyoOrquestador(ollama)
           orq.registrar_grafo(crear_grafo_chat())
           resultado = await orq.ejecutar_grafo_directo("grafo_chat", {"mensaje": "hola"})
           assert resultado.exito is True

       @pytest.mark.asyncio
       async def test_ejecutar_grafo_directo_no_registrado_falla(self):
           ollama = mock_ollama_sin_tool_call()
           orq = YeyoOrquestador(ollama)
           with pytest.raises(OrquestadorError):
               await orq.ejecutar_grafo_directo("grafo_no_existe", {})


   class TestToolDefinition:

       def test_tool_definition_tiene_estructura_correcta(self):
           ollama = mock_ollama_sin_tool_call()
           orq = YeyoOrquestador(ollama)
           grafo = crear_grafo_chat()
           orq.registrar_grafo_como_tool(grafo)
           tool = orq._tools["grafo_chat"]
           assert tool["type"] == "function"
           assert tool["function"]["name"] == "grafo_chat"
           assert "description" in tool["function"]
           assert "parameters" in tool["function"]

       def test_tool_usa_descripcion_del_grafo(self):
           ollama = mock_ollama_sin_tool_call()
           orq = YeyoOrquestador(ollama)
           grafo = YeyoGrafo("mi_grafo", "Descripción personalizada del grafo")
           # Agregar un nodo dummy para que el grafo sea válido
           nodo_dummy = MagicMock()
           nodo_dummy.id = "dummy"
           orq.registrar_grafo_como_tool(crear_grafo_chat())
           tool = orq._tools["grafo_chat"]
           assert "Conversación" in tool["function"]["description"]

4. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/orquestador/test_orquestador.py -v

VERIFICAR:
- [ ] src/orquestador/orquestador.py existe con YeyoOrquestador
- [ ] registrar_grafo() agrega al registro interno
- [ ] registrar_grafo_como_tool() convierte grafo en tool de Ollama
- [ ] procesar() llama a Ollama con tools correctamente formateadas
- [ ] Si Ollama retorna tool_call → grafo correspondiente se ejecuta
- [ ] Si Ollama no retorna tool_call → retorna texto directamente
- [ ] Error de Ollama → lanza OrquestadorError
- [ ] Grafo inexistente en tool_call → respuesta con exito=False
- [ ] TODOS los tests pasan

SI FALLA:
- Mock de tool_calls: verificar que MagicMock.tool_calls es una lista no vacía
- Arguments como string vs dict: verificar _extraer_tool_call maneja ambos formatos
- OllamaProvider no disponible: el mock es suficiente para tests unitarios

NO HACER:
- No crear el CatalogoNodos aún (eso es micro-fase 4.20)
- No implementar grafos estáticos reales aún (eso es micro-fase 4.21)
- No conectar con OllamaProvider real — usar el mock siempre en tests

GATE: YeyoOrquestador registra grafos como tools, Ollama elige el grafo correcto vía tool calling, ejecuta el grafo y retorna RespuestaOrquestador, todos los tests pasan.
```
