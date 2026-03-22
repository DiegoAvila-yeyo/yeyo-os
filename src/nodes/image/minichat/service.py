"""
YeyoOS — MiniChat v1 Service
Micro-fase 5.4 — Capa 5: Órganos

Primera versión de MiniChat: Q&A básico sobre imágenes.
Usa LLaVA para responder preguntas contextuales sobre la imagen.
"""

from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.nodes.image.analysis import ImageAnalysisService


@dataclass
class MiniChatMessage:
    role: str  # "user" | "assistant"
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MiniChatV1Service:
    """
    MiniChat v1 — chat básico sobre imágenes.
    Click en imagen → overlay → preguntas sobre la imagen.
    """

    def __init__(self):
        self._analysis_service = ImageAnalysisService()
        self._messages: list[MiniChatMessage] = []
        self._image_data: Optional[bytes] = None
        self._image_description: Optional[str] = None

    async def open_for_image(self, image_data: bytes) -> dict:
        """Abre MiniChat para una imagen específica."""
        self._image_data = image_data
        self._messages.clear()

        result = await self._analysis_service.analyze(
            image_data, "Describe esta imagen brevemente."
        )

        if "error" not in result:
            self._image_description = result["description"]
            greeting = f"Estoy viendo tu imagen. {result['description'][:100]}... ¿Qué quieres saber?"
        else:
            self._image_description = None
            greeting = "No pude analizar la imagen, pero puedo intentar responder preguntas."

        assistant_msg = MiniChatMessage(role="assistant", content=greeting)
        self._messages.append(assistant_msg)

        return {"message": greeting, "model_used": result.get("model_used")}

    async def ask(self, question: str) -> dict:
        """Hace una pregunta sobre la imagen actual."""
        if self._image_data is None:
            return {"error": "No hay imagen abierta en MiniChat"}

        user_msg = MiniChatMessage(role="user", content=question)
        self._messages.append(user_msg)

        result = await self._analysis_service.analyze(
            self._image_data, question
        )

        if "error" not in result:
            answer = result["description"]
        else:
            answer = "No pude analizar la imagen para responder tu pregunta."

        assistant_msg = MiniChatMessage(role="assistant", content=answer)
        self._messages.append(assistant_msg)

        return {
            "answer": answer,
            "model_used": result.get("model_used"),
            "question": question,
        }

    def get_messages(self) -> list[dict]:
        """Retorna historial de mensajes."""
        return [
            {"role": m.role, "content": m.content, "timestamp": m.timestamp.isoformat()}
            for m in self._messages
        ]

    def close(self) -> None:
        """Cierra MiniChat."""
        self._messages.clear()
        self._image_data = None
        self._image_description = None
