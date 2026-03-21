## ═══════════════════════════════════════
## MICRO-FASE 2.6 — Chat with Memory Context
## Tipo: VSCODE | Prompts: 2 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 2.6-1 [VSCODE] — Implementar chat contextual con memorias

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 2.6, Prompt 1 de 2: implementar el servicio de chat contextual que incluye memorias relevantes de Flash Memory en el contexto de la conversación.

CONTEXTO:
- Micro-fase 2.1: FlashMemory CRUD funcionando
- Micro-fase 2.3: EmbeddingService generando vectores de 384d
- Micro-fase 2.5: ChatService básico funcionando
- Token budget TOTAL = 4000: system(300) + memories(1000) + history(1500) + input(500) + response(700)
- El chat contextual busca memorias semánticamente relevantes y las inyecta en el contexto
- Hardware: GTX 1060 3GB VRAM, 16GB RAM, WSL2 Ubuntu

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/chat/contextual_service.py:

   Ruta: ~/yeyo-os/src/chat/contextual_service.py
   Contenido:

   """
   YeyoOS — ContextualChatService (Chat con Contexto de Memoria)
   Micro-fase 2.6 — Capa 2: Cerebro

   Servicio de chat que inyecta memorias relevantes de Flash Memory
   en el contexto de la conversación, respetando el token budget.

   Token Budget:
   - system_prompt:          300 tokens
   - relevant_memories:     1000 tokens
   - conversation_history:  1500 tokens
   - user_input:             500 tokens
   - response (reservado):   700 tokens
   - TOTAL:                 4000 tokens
   """

   import logging
   from typing import AsyncIterator, Optional

   from src.ia.interfaces import IAProvider, IAMessage, IAResponse
   from src.ia.embeddings import EmbeddingService
   from src.memory.flash_memory import FlashMemory
   from src.memory.models import Memory

   logger = logging.getLogger("yeyoos.contextual_chat")

   # Token budget constants
   BUDGET_SYSTEM = 300
   BUDGET_MEMORIES = 1000
   BUDGET_HISTORY = 1500
   BUDGET_INPUT = 500
   BUDGET_RESPONSE = 700
   BUDGET_TOTAL = 4000

   DEFAULT_SYSTEM_PROMPT = (
       "Eres YeyoOS, un asistente de IA integrado en el sistema operativo del usuario. "
       "Eres directo, útil y respetuoso. Respondes en español. "
       "Usas la información de tus memorias para personalizar tus respuestas."
   )


   def count_tokens(text: str) -> int:
       """Aproximación de conteo de tokens: ~4 caracteres por token."""
       if not text:
           return 0
       return max(1, len(text) // 4)


   def truncate_to_tokens(text: str, max_tokens: int) -> str:
       """Trunca texto para que no exceda max_tokens."""
       if count_tokens(text) <= max_tokens:
           return text
       max_chars = max_tokens * 4
       return text[:max_chars].rsplit(" ", 1)[0] + "..."


   class ContextualChatService:
       """
       Servicio de chat que construye contexto rico con memorias.
       Busca memorias semánticamente relevantes y las incluye en
       el prompt, respetando estrictamente el token budget de 4000.
       """

       def __init__(
           self,
           ia: IAProvider,
           memory: FlashMemory,
           embeddings: EmbeddingService,
           system_prompt: str = DEFAULT_SYSTEM_PROMPT,
       ):
           self.ia = ia
           self.memory = memory
           self.embeddings = embeddings
           self.system_prompt = system_prompt

       async def build_context(
           self,
           user_input: str,
           conversation_history: list[dict] = None,
       ) -> dict:
           """
           Construye el contexto completo para el chat.
           1. Genera embedding del input del usuario
           2. Busca memorias semánticamente relevantes (top 5)
           3. Incluye historial de conversación reciente
           4. Aplica token budget estricto

           Retorna dict con las secciones del contexto.
           """
           if conversation_history is None:
               conversation_history = []

           # 1. System prompt (máx 300 tokens)
           system = truncate_to_tokens(self.system_prompt, BUDGET_SYSTEM)

           # 2. Buscar memorias relevantes (máx 1000 tokens)
           relevant_memories = await self._search_relevant_memories(user_input)
           memories_text = self._format_memories(relevant_memories, BUDGET_MEMORIES)

           # 3. Historial de conversación (máx 1500 tokens)
           history = self._truncate_history(conversation_history, BUDGET_HISTORY)

           # 4. Input del usuario (máx 500 tokens)
           truncated_input = truncate_to_tokens(user_input, BUDGET_INPUT)

           # Construir system prompt enriquecido con memorias
           enriched_system = system
           if memories_text:
               enriched_system += (
                   "\n\n[MEMORIAS RELEVANTES - usa esta información para personalizar tu respuesta]\n"
                   + memories_text
               )

           context = {
               "system_prompt": enriched_system,
               "relevant_memories": relevant_memories,
               "conversation_history": history,
               "user_input": truncated_input,
               "token_usage": {
                   "system": count_tokens(enriched_system),
                   "memories": count_tokens(memories_text),
                   "history": sum(count_tokens(m.get("content", "")) for m in history),
                   "input": count_tokens(truncated_input),
                   "reserved_response": BUDGET_RESPONSE,
               },
           }

           total_used = (
               context["token_usage"]["system"]
               + context["token_usage"]["history"]
               + context["token_usage"]["input"]
               + BUDGET_RESPONSE
           )
           context["token_usage"]["total"] = total_used
           context["token_usage"]["remaining"] = BUDGET_TOTAL - total_used

           logger.info(f"Contexto construido: {total_used}/{BUDGET_TOTAL} tokens usados")
           return context

       async def send_message(
           self,
           user_input: str,
           conversation_history: list[dict] = None,
           conversation_id: str = "",
       ) -> str:
           """
           Envía un mensaje con contexto de memoria.
           1. Construye contexto (memorias + historial)
           2. Envía al modelo
           3. Retorna respuesta
           """
           if not user_input or not user_input.strip():
               return "No recibí ningún mensaje. ¿En qué puedo ayudarte?"

           context = await self.build_context(user_input, conversation_history)

           # Construir mensajes para el modelo
           messages = [
               IAMessage(role="system", content=context["system_prompt"]),
           ]

           # Agregar historial
           for msg in context["conversation_history"]:
               messages.append(IAMessage(
                   role=msg["role"],
                   content=msg["content"],
               ))

           # Agregar input del usuario
           messages.append(IAMessage(role="user", content=context["user_input"]))

           try:
               response: IAResponse = await self.ia.chat(messages)
               logger.info(
                   f"Chat contextual: tokens={response.tokens_used}, "
                   f"latency={response.latency_ms}ms, "
                   f"memories={len(context['relevant_memories'])}"
               )
               return response.content
           except Exception as e:
               logger.error(f"Error en chat contextual: {e}")
               raise

       async def send_message_stream(
           self,
           user_input: str,
           conversation_history: list[dict] = None,
           conversation_id: str = "",
       ) -> AsyncIterator[str]:
           """Envía mensaje con contexto y retorna streaming."""
           if not user_input or not user_input.strip():
               yield "No recibí ningún mensaje. ¿En qué puedo ayudarte?"
               return

           context = await self.build_context(user_input, conversation_history)

           messages = [
               IAMessage(role="system", content=context["system_prompt"]),
           ]
           for msg in context["conversation_history"]:
               messages.append(IAMessage(role=msg["role"], content=msg["content"]))
           messages.append(IAMessage(role="user", content=context["user_input"]))

           try:
               async for chunk in self.ia.chat_stream(messages):
                   yield chunk
           except Exception as e:
               logger.error(f"Error en streaming contextual: {e}")
               raise

       async def _search_relevant_memories(
           self, user_input: str, limit: int = 5
       ) -> list[Memory]:
           """Busca memorias semánticamente relevantes al input."""
           try:
               embedding = self.embeddings.generate(user_input)
               memories = await self.memory.search_semantic(
                   embedding=embedding,
                   threshold=0.5,
                   limit=limit,
               )
               return memories
           except Exception as e:
               logger.warning(f"Error buscando memorias: {e}")
               return []

       def _format_memories(
           self, memories: list[Memory], max_tokens: int
       ) -> str:
           """
           Formatea memorias como texto, respetando token budget.
           Incluye las más relevantes primero.
           """
           if not memories:
               return ""

           lines = []
           tokens_used = 0
           for mem in memories:
               line = f"- [{mem.type}] {mem.content}"
               line_tokens = count_tokens(line)
               if tokens_used + line_tokens > max_tokens:
                   break
               lines.append(line)
               tokens_used += line_tokens

           return "\n".join(lines)

       def _truncate_history(
           self, history: list[dict], max_tokens: int
       ) -> list[dict]:
           """
           Trunca historial para que quepa en el budget.
           Mantiene los mensajes más recientes (elimina los más antiguos).
           """
           if not history:
               return []

           # Calcular tokens totales del historial
           total_tokens = sum(count_tokens(m.get("content", "")) for m in history)

           if total_tokens <= max_tokens:
               return history

           # Truncar desde el inicio (mantener los más recientes)
           truncated = []
           tokens_used = 0
           for msg in reversed(history):
               msg_tokens = count_tokens(msg.get("content", ""))
               if tokens_used + msg_tokens > max_tokens:
                   break
               truncated.insert(0, msg)
               tokens_used += msg_tokens

           return truncated

2. Actualizar src/chat/__init__.py:

   Ruta: ~/yeyo-os/src/chat/__init__.py
   Contenido:

   from .service import ChatService
   from .contextual_service import ContextualChatService

VERIFICAR:
- [ ] Archivo src/chat/contextual_service.py existe
- [ ] build_context() retorna dict con todas las secciones
- [ ] Token budget respetado: system(300) + memories(1000) + history(1500) + input(500) + response(700) = 4000
- [ ] Memorias relevantes incluidas en contexto
- [ ] Historial trunca mensajes antiguos primero
- [ ] send_message() funciona con contexto
- [ ] send_message_stream() funciona con contexto
- [ ] Import funciona: `from src.chat.contextual_service import ContextualChatService`

SI FALLA:
- Import error: verificar que micro-fases 2.1, 2.3, 2.5 están completadas
- EmbeddingService no cargado: verificar que sentence-transformers está instalado
- Token counting: verificar aproximación de 4 chars/token

NO HACER:
- No exceder los 4000 tokens totales NUNCA
- No almacenar conversaciones todavía (micro-fase 2.7)
- No extraer memorias del mensaje todavía (micro-fase 2.9)
- No verificar alucinaciones todavía (micro-fase 2.11)

GATE: ContextualChatService construye contexto con memorias, respeta token budget de 4000, historial se trunca correctamente, import funciona.
```
