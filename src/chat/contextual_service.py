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

import asyncio
import logging
from typing import AsyncIterator, Optional

from src.ia.interfaces import IAProvider, IAMessage, IAResponse
from src.memory.flash_memory import FlashMemory
from src.memory.models import Memory
from src.memory.extraction import MemoryExtractor
from src.memory.classifier import NamespaceClassifier

logger = logging.getLogger("yeyoos.contextual_chat")

# Token budget constants
BUDGET_SYSTEM = 300
BUDGET_MEMORIES = 1000
BUDGET_HISTORY = 1500
BUDGET_INPUT = 500
BUDGET_RESPONSE = 700
BUDGET_TOTAL = 4000

DEFAULT_SYSTEM_PROMPT = (
    "Eres YeyoOS, la IA central de un sistema operativo AI-nativo. "
    "Tu interfaz tiene nodos: Imagen, Video, Código, Automatización, Chat y Memoria. "
    "REGLAS CRÍTICAS:\n"
    "1. Sé conciso (máx 2-3 oraciones).\n"
    "2. Responde en español.\n"
    "3. Las memorias del [CONTEXTO PERSONAL] son hechos DEL USUARIO, no tuyos. "
    "Cuando respondas sobre ellas usa SEGUNDA PERSONA: 'aprendiste', 'te llamas', 'usas'.\n"
    "4. NUNCA inventes ni agregues información que no esté en el contexto o en la conversación. "
    "Si la memoria dice solo 'aprendí Python', responde exactamente eso, sin añadir detalles.\n"
    "5. Si no tienes la información, di 'No tengo ese dato guardado' — no la inventes.\n"
    "6. Tu memoria es del usuario: nada se borra, todo se recuerda."
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
    truncated = text[:max_chars]
    last_space = truncated.rfind(" ")
    if last_space > 0:
        truncated = truncated[:last_space]
    return truncated + "..."


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
        embeddings,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    ):
        self.ia = ia
        self.memory = memory
        self.embeddings = embeddings
        self.system_prompt = system_prompt
        self._extractor = MemoryExtractor(ia)
        self._classifier = NamespaceClassifier(ia)

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
                "\n\n[CONTEXTO PERSONAL - información que ya sabes sobre el usuario, "
                "úsala naturalmente en tu respuesta SIN copiarla literalmente]\n"
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

    async def _extract_and_store(self, user_input: str, assistant_response: str) -> None:
        """Guarda el mensaje del usuario directamente en Flash Memory."""
        from src.memory.pipeline_events import pipeline_buffer
        try:
            stored = await self._extractor.extract_and_store(
                user_message=user_input,
                flash_memory=self.memory,
                embedding_service=self.embeddings,
                namespace="chat:usuario",  # default, clasificador lo actualiza
                assistant_message=assistant_response,
            )
            if stored:
                memory_id = None
                # Obtener el ID de la memoria recién guardada para clasificar
                async with self.memory.pool.acquire() as conn:
                    row = await conn.fetchrow(
                        """SELECT id FROM flash_memories
                           WHERE content = $1 AND source = 'chat_extraction'
                           ORDER BY created_at DESC LIMIT 1""",
                        user_input,
                    )
                    if row:
                        memory_id = str(row["id"])

                if memory_id:
                    asyncio.create_task(
                        self._classify_and_update_namespace(memory_id, user_input)
                    )
        except Exception as e:
            logger.warning(f"Error guardando memoria (no crítico): {e}")

    async def _classify_and_update_namespace(self, memory_id: str, content: str) -> None:
        """Clasifica el contenido y actualiza el namespace en BD. Corre en background."""
        from src.memory.pipeline_events import pipeline_buffer
        # Find the pipeline_id for this content
        recent = pipeline_buffer.get_recent(50)
        pid = None
        for ev in reversed(recent):
            if ev["step"] == "RECEIVED" and content[:80] in ev.get("detail", ""):
                pid = ev["pipeline_id"]
                break

        try:
            namespace = await self._classifier.classify(content)
            if namespace != "chat:usuario":  # solo actualizar si cambió del default
                async with self.memory.pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE flash_memories SET namespace = $1 WHERE id = $2",
                        namespace,
                        memory_id,
                    )
                logger.debug(f"Namespace actualizado: {memory_id[:8]}... → {namespace}")

            if pid:
                pipeline_buffer.emit(pid, "NAMESPACE_CLASSIFY", "ok",
                                     f"→ {namespace}",
                                     {"namespace": namespace, "memory_id": memory_id})
        except Exception as e:
            logger.warning(f"Error clasificando namespace (no crítico): {e}")
            if pid:
                pipeline_buffer.emit(pid, "NAMESPACE_CLASSIFY", "error",
                                     f"Falló: {str(e)[:100]}",
                                     {"error": str(e)[:200]})

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

        messages = [IAMessage(role="system", content=context["system_prompt"])]
        for msg in context["conversation_history"]:
            messages.append(IAMessage(role=msg["role"], content=msg["content"]))
        messages.append(IAMessage(role="user", content=context["user_input"]))

        try:
            response: IAResponse = await self.ia.chat(messages)
            logger.info(
                f"Chat contextual: tokens={response.tokens_used}, "
                f"latency={response.latency_ms}ms, "
                f"memories={len(context['relevant_memories'])}"
            )
            # Extract and store memorable facts in the background
            asyncio.create_task(self._extract_and_store(user_input, response.content))
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

        messages = [IAMessage(role="system", content=context["system_prompt"])]
        for msg in context["conversation_history"]:
            messages.append(IAMessage(role=msg["role"], content=msg["content"]))
        messages.append(IAMessage(role="user", content=context["user_input"]))

        try:
            full_response = []
            async for chunk in self.ia.chat_stream(messages):
                full_response.append(chunk)
                yield chunk
            # Extract memories from the complete exchange in background
            asyncio.create_task(
                self._extract_and_store(user_input, "".join(full_response))
            )
        except Exception as e:
            logger.error(f"Error en streaming contextual: {e}")
            raise

    async def _search_relevant_memories(
        self, user_input: str, limit: int = 5
    ) -> list[Memory]:
        """Busca memorias semánticamente relevantes al input (todos los namespaces del usuario)."""
        try:
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(None, self.embeddings.generate, user_input)
            return await self.memory.search_semantic(
                embedding=embedding,
                threshold=0.3,
                limit=limit,
                namespaces=["chat:usuario", "codigo:usuario", "personal", "preferencias"],
            )
        except Exception as e:
            logger.warning(f"Error buscando memorias: {e}")
            return []

    def _format_memories(self, memories: list[Memory], max_tokens: int) -> str:
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

    def _truncate_history(self, history: list[dict], max_tokens: int) -> list[dict]:
        """
        Trunca historial para que quepa en el budget.
        Mantiene los mensajes más recientes (elimina los más antiguos).
        """
        if not history:
            return []

        total_tokens = sum(count_tokens(m.get("content", "")) for m in history)
        if total_tokens <= max_tokens:
            return history

        truncated = []
        tokens_used = 0
        for msg in reversed(history):
            msg_tokens = count_tokens(msg.get("content", ""))
            if tokens_used + msg_tokens > max_tokens:
                break
            truncated.insert(0, msg)
            tokens_used += msg_tokens

        return truncated
