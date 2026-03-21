## ═══════════════════════════════════════
## MICRO-FASE 2.5 — Chat Service Basic
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 2.5-1 [VSCODE] — Implementar servicio de chat básico con Ollama

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 2.5 de Capa 2 (Cerebro): implementar el servicio de chat básico que envuelve a Ollama (IAProvider) sin contexto de memoria todavía.

CONTEXTO:
- Capa 1 completada: IAProvider, OllamaProvider definidos y funcionando
- Ollama corriendo con modelo qwen2.5:3b en http://localhost:11434
- Este chat es BÁSICO: solo wrapper de Ollama con system prompt fijo
- El chat con contexto de memoria viene en micro-fase 2.6
- Token budget total: 4000 tokens (system:300 + memories:1000 + history:1500 + input:500 + response:700)
- Hardware: GTX 1060 3GB VRAM, 16GB RAM, WSL2 Ubuntu

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear directorio si no existe:
   mkdir -p src/chat

2. Crear archivo src/chat/__init__.py:

   Ruta: ~/yeyo-os/src/chat/__init__.py
   Contenido:

   from .service import ChatService

3. Crear archivo src/chat/service.py:

   Ruta: ~/yeyo-os/src/chat/service.py
   Contenido:

   """
   YeyoOS — ChatService (Servicio de Chat Básico)
   Micro-fase 2.5 — Capa 2: Cerebro

   Wrapper básico de IAProvider para conversación.
   Sin contexto de memoria — eso viene en micro-fase 2.6.
   """

   import logging
   from typing import AsyncIterator

   from src.ia.interfaces import IAProvider, IAMessage, IAResponse

   logger = logging.getLogger("yeyoos.chat")

   DEFAULT_SYSTEM_PROMPT = (
       "Eres YeyoOS, un asistente de IA integrado en el sistema operativo del usuario. "
       "Eres directo, útil y respetuoso. Respondes en español a menos que el usuario "
       "te hable en otro idioma. Eres conciso pero completo en tus respuestas."
   )


   class ChatService:
       """
       Servicio de chat básico.
       Envuelve IAProvider para conversación simple con system prompt.
       """

       def __init__(
           self,
           ia_provider: IAProvider,
           system_prompt: str = DEFAULT_SYSTEM_PROMPT,
       ):
           self.ia = ia_provider
           self.system_prompt = system_prompt

       async def send_message(self, user_input: str) -> str:
           """
           Envía un mensaje al modelo y retorna la respuesta completa.
           Incluye system prompt automáticamente.
           """
           if not user_input or not user_input.strip():
               return "No recibí ningún mensaje. ¿En qué puedo ayudarte?"

           messages = [
               IAMessage(role="system", content=self.system_prompt),
               IAMessage(role="user", content=user_input.strip()),
           ]

           try:
               response: IAResponse = await self.ia.chat(messages)
               logger.info(
                   f"Chat response: tokens={response.tokens_used}, "
                   f"latency={response.latency_ms}ms"
               )
               return response.content
           except Exception as e:
               logger.error(f"Error en chat: {e}")
               raise

       async def send_message_stream(self, user_input: str) -> AsyncIterator[str]:
           """
           Envía un mensaje y retorna la respuesta en streaming.
           Yield de chunks de texto conforme llegan del modelo.
           """
           if not user_input or not user_input.strip():
               yield "No recibí ningún mensaje. ¿En qué puedo ayudarte?"
               return

           messages = [
               IAMessage(role="system", content=self.system_prompt),
               IAMessage(role="user", content=user_input.strip()),
           ]

           try:
               async for chunk in self.ia.chat_stream(messages):
                   yield chunk
           except Exception as e:
               logger.error(f"Error en streaming: {e}")
               raise

       async def send_with_history(
           self,
           user_input: str,
           history: list[dict] = None,
       ) -> str:
           """
           Envía un mensaje con historial de conversación previo.
           history: lista de {"role": "user"|"assistant", "content": "..."}
           """
           if not user_input or not user_input.strip():
               return "No recibí ningún mensaje. ¿En qué puedo ayudarte?"

           messages = [IAMessage(role="system", content=self.system_prompt)]

           if history:
               for msg in history:
                   messages.append(IAMessage(
                       role=msg["role"],
                       content=msg["content"],
                   ))

           messages.append(IAMessage(role="user", content=user_input.strip()))

           try:
               response: IAResponse = await self.ia.chat(messages)
               return response.content
           except Exception as e:
               logger.error(f"Error en chat con historial: {e}")
               raise

       def get_system_prompt(self) -> str:
           """Retorna el system prompt actual."""
           return self.system_prompt

       def set_system_prompt(self, prompt: str):
           """Actualiza el system prompt."""
           self.system_prompt = prompt

4. Crear tests:

   Ruta: ~/yeyo-os/tests/unit/chat/__init__.py
   Contenido: (archivo vacío)

   Ruta: ~/yeyo-os/tests/unit/chat/test_chat_service.py
   Contenido:

   """
   Tests para ChatService — Micro-fase 2.5
   Tests unitarios con mock de IAProvider.
   """

   import pytest
   from unittest.mock import AsyncMock, MagicMock
   from src.chat.service import ChatService, DEFAULT_SYSTEM_PROMPT
   from src.ia.interfaces import IAProvider, IAMessage, IAResponse


   @pytest.fixture
   def mock_ia_provider():
       provider = AsyncMock(spec=IAProvider)
       provider.chat.return_value = IAResponse(
           content="Hola, soy YeyoOS",
           model="qwen2.5:3b",
           tokens_used=15,
           latency_ms=100.0,
       )
       return provider


   @pytest.fixture
   def chat_service(mock_ia_provider):
       return ChatService(ia_provider=mock_ia_provider)


   class TestChatServiceBasic:
       """Tests básicos del ChatService."""

       def test_has_default_system_prompt(self, chat_service):
           assert "YeyoOS" in chat_service.get_system_prompt()

       def test_default_system_prompt_content(self):
           assert "YeyoOS" in DEFAULT_SYSTEM_PROMPT
           assert "directo" in DEFAULT_SYSTEM_PROMPT
           assert "útil" in DEFAULT_SYSTEM_PROMPT

       def test_custom_system_prompt(self, mock_ia_provider):
           service = ChatService(
               ia_provider=mock_ia_provider,
               system_prompt="Custom prompt",
           )
           assert service.get_system_prompt() == "Custom prompt"

       def test_set_system_prompt(self, chat_service):
           chat_service.set_system_prompt("Nuevo prompt")
           assert chat_service.get_system_prompt() == "Nuevo prompt"


   class TestChatServiceMessages:
       """Tests de envío de mensajes."""

       @pytest.mark.asyncio
       async def test_send_message_returns_string(self, chat_service):
           result = await chat_service.send_message("Hola")
           assert isinstance(result, str)
           assert result == "Hola, soy YeyoOS"

       @pytest.mark.asyncio
       async def test_send_message_includes_system_prompt(
           self, chat_service, mock_ia_provider
       ):
           await chat_service.send_message("Test")
           call_args = mock_ia_provider.chat.call_args
           messages = call_args[0][0] if call_args[0] else call_args[1]["messages"]
           assert messages[0].role == "system"
           assert "YeyoOS" in messages[0].content

       @pytest.mark.asyncio
       async def test_send_message_includes_user_input(
           self, chat_service, mock_ia_provider
       ):
           await chat_service.send_message("Hola mundo")
           call_args = mock_ia_provider.chat.call_args
           messages = call_args[0][0] if call_args[0] else call_args[1]["messages"]
           assert messages[-1].role == "user"
           assert messages[-1].content == "Hola mundo"

       @pytest.mark.asyncio
       async def test_send_empty_message(self, chat_service):
           result = await chat_service.send_message("")
           assert "No recibí" in result

       @pytest.mark.asyncio
       async def test_send_whitespace_message(self, chat_service):
           result = await chat_service.send_message("   ")
           assert "No recibí" in result

       @pytest.mark.asyncio
       async def test_send_message_strips_input(
           self, chat_service, mock_ia_provider
       ):
           await chat_service.send_message("  Hola  ")
           call_args = mock_ia_provider.chat.call_args
           messages = call_args[0][0] if call_args[0] else call_args[1]["messages"]
           assert messages[-1].content == "Hola"

       @pytest.mark.asyncio
       async def test_send_message_error_propagates(self, mock_ia_provider):
           mock_ia_provider.chat.side_effect = Exception("Ollama caído")
           service = ChatService(ia_provider=mock_ia_provider)
           with pytest.raises(Exception, match="Ollama caído"):
               await service.send_message("Test")


   class TestChatServiceStreaming:
       """Tests de streaming."""

       @pytest.mark.asyncio
       async def test_stream_returns_chunks(self, mock_ia_provider):
           async def fake_stream(*args, **kwargs):
               for chunk in ["Hola", " ", "mundo"]:
                   yield chunk

           mock_ia_provider.chat_stream = fake_stream
           service = ChatService(ia_provider=mock_ia_provider)

           chunks = []
           async for chunk in service.send_message_stream("Test"):
               chunks.append(chunk)
           assert len(chunks) == 3
           assert "".join(chunks) == "Hola mundo"

       @pytest.mark.asyncio
       async def test_stream_empty_message(self, chat_service):
           chunks = []
           async for chunk in chat_service.send_message_stream(""):
               chunks.append(chunk)
           assert len(chunks) == 1
           assert "No recibí" in chunks[0]


   class TestChatServiceHistory:
       """Tests de chat con historial."""

       @pytest.mark.asyncio
       async def test_send_with_history(
           self, chat_service, mock_ia_provider
       ):
           history = [
               {"role": "user", "content": "Hola"},
               {"role": "assistant", "content": "¡Hola!"},
           ]
           await chat_service.send_with_history("¿Cómo estás?", history)
           call_args = mock_ia_provider.chat.call_args
           messages = call_args[0][0] if call_args[0] else call_args[1]["messages"]
           assert len(messages) == 4  # system + 2 history + user
           assert messages[0].role == "system"
           assert messages[1].role == "user"
           assert messages[2].role == "assistant"
           assert messages[3].role == "user"
           assert messages[3].content == "¿Cómo estás?"

       @pytest.mark.asyncio
       async def test_send_with_empty_history(
           self, chat_service, mock_ia_provider
       ):
           await chat_service.send_with_history("Test", history=None)
           call_args = mock_ia_provider.chat.call_args
           messages = call_args[0][0] if call_args[0] else call_args[1]["messages"]
           assert len(messages) == 2  # system + user

5. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/chat/test_chat_service.py -v

VERIFICAR:
- [ ] Archivo src/chat/service.py existe
- [ ] ChatService envuelve IAProvider correctamente
- [ ] System prompt incluye "YeyoOS"
- [ ] send_message() retorna string
- [ ] send_message_stream() genera chunks
- [ ] send_with_history() incluye mensajes previos
- [ ] Mensajes vacíos manejados grácilmente
- [ ] Errores de IAProvider se propagan
- [ ] TODOS los tests pasan

SI FALLA:
- Import error IAProvider: verificar que Capa 1 está completada
- AsyncMock: requiere Python 3.8+
- pytest-asyncio: `pip install pytest-asyncio`

NO HACER:
- No agregar contexto de memoria todavía (eso es micro-fase 2.6)
- No almacenar historial en base de datos todavía (micro-fase 2.7)
- No implementar token budget todavía (micro-fase 2.8)
- No agregar anti-alucinación todavía (micro-fase 2.11)

GATE: ChatService funcional, system prompt configurado, send_message y streaming funcionan, manejo de errores, todos los tests pasan.
```
