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
    "Eres YeyoOS, la IA central de un sistema operativo AI-nativo. "
    "Tu interfaz tiene nodos: Imagen, Video, Código, Automatización, Chat y Memoria. "
    "REGLAS: Sé conversacional y útil (2-5 oraciones). Responde en español. "
    "Puedes opinar, sugerir y conversar libremente. Si no sabes algo, dilo honestamente."
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

    async def send_message(
        self,
        user_input: str,
        conversation_history: list[dict] = None,
        conversation_id: str = "",
    ) -> str:
        """
        Envía un mensaje al modelo y retorna la respuesta completa.
        """
        if not user_input or not user_input.strip():
            return "No recibí ningún mensaje. ¿En qué puedo ayudarte?"

        messages = [IAMessage(role="system", content=self.system_prompt)]

        if conversation_history:
            for msg in conversation_history:
                messages.append(IAMessage(role=msg["role"], content=msg["content"]))

        messages.append(IAMessage(role="user", content=user_input.strip()))

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

    async def send_message_stream(
        self,
        user_input: str,
        conversation_history: list[dict] = None,
        conversation_id: str = "",
    ) -> AsyncIterator[str]:
        """
        Envía un mensaje y retorna la respuesta en streaming.
        Acepta conversation_history para compatibilidad con la ruta de streaming.
        """
        if not user_input or not user_input.strip():
            yield "No recibí ningún mensaje. ¿En qué puedo ayudarte?"
            return

        messages = [IAMessage(role="system", content=self.system_prompt)]

        if conversation_history:
            for msg in conversation_history:
                messages.append(IAMessage(role=msg["role"], content=msg["content"]))

        messages.append(IAMessage(role="user", content=user_input.strip()))

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
