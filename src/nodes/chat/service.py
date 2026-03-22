"""
YeyoOS — Chat Node
Micro-fase 5.1 — Capa 5: Órganos

Nodo de chat completo: multi-conversación, búsqueda,
export a markdown, placeholder de voz.
Usa ContextualChatService de Capa 2.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass, field

from src.nodes.base import NodeBase, PrivilegeLevel


@dataclass
class ChatMessage:
    """Mensaje individual en una conversación."""
    id: str
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Conversation:
    """Una conversación con historial de mensajes."""
    id: str
    title: str
    messages: list[ChatMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ChatNode(NodeBase):
    """
    Nodo de Chat — órgano de comunicación con la IA.
    Multi-conversación, búsqueda, export, streaming.
    """

    def __init__(self):
        super().__init__(
            name="Chat",
            version="1.0.0",
            privilege_level=PrivilegeLevel.SANDBOX,
            container_config={"memory_limit": "512m", "cpu_shares": 512},
        )
        self._conversations: dict[str, Conversation] = {}
        self._active_conversation_id: Optional[str] = None

    async def initialize(self) -> None:
        """Inicializa el servicio de chat contextual."""
        default_conv = self._create_conversation("Nueva conversación")
        self._active_conversation_id = default_conv.id

    async def render_ui(self) -> dict:
        """Retorna configuración del componente React."""
        return {
            "component": "ChatNode",
            "props": {
                "conversations": [
                    {"id": c.id, "title": c.title, "messageCount": len(c.messages)}
                    for c in self._conversations.values()
                ],
                "activeConversationId": self._active_conversation_id,
            },
        }

    async def process(self, input_data: dict) -> dict:
        """Procesa un mensaje del usuario y genera respuesta."""
        message = input_data.get("message", "")
        conv_id = input_data.get("conversation_id", self._active_conversation_id)

        if not conv_id or conv_id not in self._conversations:
            return {"error": "Conversación no encontrada"}

        conv = self._conversations[conv_id]

        user_msg = ChatMessage(
            id=f"msg-{uuid.uuid4().hex[:8]}",
            role="user",
            content=message,
        )
        conv.messages.append(user_msg)
        conv.updated_at = datetime.now(timezone.utc)

        # Usa ContextualChatService de Capa 2
        from src.chat.contextual_service import ContextualChatService
        chat_service = ContextualChatService()
        response = await chat_service.send_message(message, context={
            "conversation_id": conv_id,
            "history": [
                {"role": m.role, "content": m.content}
                for m in conv.messages[-20:]
            ],
        })

        assistant_msg = ChatMessage(
            id=f"msg-{uuid.uuid4().hex[:8]}",
            role="assistant",
            content=response.get("content", ""),
        )
        conv.messages.append(assistant_msg)
        conv.updated_at = datetime.now(timezone.utc)

        # Auto-title from first user message
        if len(conv.messages) == 2:
            conv.title = message[:50]

        return {
            "message": assistant_msg.content,
            "message_id": assistant_msg.id,
            "conversation_id": conv_id,
        }

    async def cleanup(self) -> None:
        """Limpia recursos del chat node."""
        self._conversations.clear()
        self._active_conversation_id = None

    # ═══════════════════════════════════
    # MÉTODOS ESPECÍFICOS DEL CHAT NODE
    # ═══════════════════════════════════

    def _create_conversation(self, title: str) -> Conversation:
        """Crea una nueva conversación."""
        conv = Conversation(
            id=f"conv-{uuid.uuid4().hex[:8]}",
            title=title,
        )
        self._conversations[conv.id] = conv
        return conv

    async def new_conversation(self, title: str = "Nueva conversación") -> dict:
        """Crea nueva conversación y la activa."""
        conv = self._create_conversation(title)
        self._active_conversation_id = conv.id
        return {"conversation_id": conv.id, "title": conv.title}

    async def switch_conversation(self, conversation_id: str) -> dict:
        """Cambia a otra conversación."""
        if conversation_id not in self._conversations:
            return {"error": "Conversación no encontrada"}
        self._active_conversation_id = conversation_id
        conv = self._conversations[conversation_id]
        return {
            "conversation_id": conv.id,
            "title": conv.title,
            "messages": [
                {"id": m.id, "role": m.role, "content": m.content,
                 "timestamp": m.timestamp.isoformat()}
                for m in conv.messages
            ],
        }

    async def search_messages(self, query: str) -> list[dict]:
        """Busca mensajes en todas las conversaciones."""
        results = []
        query_lower = query.lower()
        for conv in self._conversations.values():
            for msg in conv.messages:
                if query_lower in msg.content.lower():
                    results.append({
                        "conversation_id": conv.id,
                        "conversation_title": conv.title,
                        "message_id": msg.id,
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat(),
                    })
        return results

    async def export_conversation(self, conversation_id: str) -> str:
        """Exporta una conversación a markdown."""
        if conversation_id not in self._conversations:
            raise ValueError("Conversación no encontrada")

        conv = self._conversations[conversation_id]
        lines = [f"# {conv.title}\n"]
        lines.append(f"*Exportado: {datetime.now(timezone.utc).isoformat()}*\n")
        lines.append("---\n")

        for msg in conv.messages:
            if msg.role == "user":
                lines.append(f"**Usuario:** {msg.content}\n")
            elif msg.role == "assistant":
                lines.append(f"**YeyoOS:** {msg.content}\n")
            lines.append("")

        return "\n".join(lines)

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Elimina una conversación."""
        if conversation_id not in self._conversations:
            return False
        del self._conversations[conversation_id]
        if self._active_conversation_id == conversation_id:
            if self._conversations:
                self._active_conversation_id = next(iter(self._conversations))
            else:
                self._active_conversation_id = None
        return True
