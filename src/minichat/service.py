"""
YeyoOS — MiniChat v2 Service (Node Context)
Micro-fase 5.18 — Capa 5: Órganos

MiniChat v2: conoce el nodo activo y proporciona ayuda contextual.
System prompt se adapta al nodo. Sugerencias contextuales.
"""

from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone


NODE_CONTEXTS: dict[str, dict] = {
    "chat": {
        "system_prompt": "Estás en el nodo de Chat de YeyoOS. Ayudas con conversaciones, "
                         "búsqueda de mensajes y exportación.",
        "suggestions": [
            "Busca en mis conversaciones anteriores",
            "Exporta esta conversación",
            "Crea una nueva conversación sobre...",
        ],
    },
    "image": {
        "system_prompt": "Estás en el nodo de Imagen de YeyoOS. Puedes describir imágenes, "
                         "generar variaciones y transformar imágenes.",
        "suggestions": [
            "Describe esta imagen",
            "Genera una variación de esta imagen",
            "Cambia el estilo a pixel art",
            "¿Qué objetos hay en la imagen?",
        ],
    },
    "video": {
        "system_prompt": "Estás en el nodo de Video de YeyoOS. Ayudas con edición de video "
                         "usando FFmpeg, subtítulos y TTS.",
        "suggestions": [
            "Recorta del minuto 2 al 5",
            "Transcribe este video",
            "Genera subtítulos",
            "Concatena estos videos",
        ],
    },
    "code": {
        "system_prompt": "Estás en el nodo de Código de YeyoOS. Ayudas con edición, "
                         "explicación, debugging y ejecución de código.",
        "suggestions": [
            "Explica este código",
            "Encuentra bugs en este código",
            "Ejecuta este código",
            "Genera un commit message",
        ],
    },
    "automation": {
        "system_prompt": "Estás en el nodo de Automatización de YeyoOS. Ayudas con "
                         "pipelines visuales y conexiones entre nodos.",
        "suggestions": [
            "Crea un pipeline que...",
            "Conecta estos pasos",
            "Valida este pipeline",
            "Programa una publicación",
        ],
    },
    "files": {
        "system_prompt": "Estás en el nodo de Archivos de YeyoOS. Ayudas con búsqueda "
                         "de archivos, organización y preview.",
        "suggestions": [
            "Busca mis documentos de impuestos",
            "Organiza esta carpeta",
            "¿Qué archivos grandes tengo?",
        ],
    },
    "browser": {
        "system_prompt": "Estás en el nodo de Browser de YeyoOS. Ayudas con navegación "
                         "web y resumen de páginas.",
        "suggestions": [
            "Resume esta página",
            "¿De qué trata este sitio?",
            "Guarda en marcadores",
        ],
    },
    "config": {
        "system_prompt": "Estás en el nodo de Configuración de YeyoOS. Ayudas con "
                         "ajustes del sistema, modelos y GPU.",
        "suggestions": [
            "¿Cuánta VRAM estoy usando?",
            "Descarga un nuevo modelo",
            "¿Qué modelos tengo instalados?",
        ],
    },
}

DEFAULT_CONTEXT = {
    "system_prompt": "Estás en YeyoOS, un OS AI-nativo. ¿En qué puedo ayudarte?",
    "suggestions": ["¿Qué puedo hacer aquí?"],
}


@dataclass
class MiniChatV2Message:
    role: str
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MiniChatV2Service:
    """
    MiniChat v2 — chat contextual por nodo.
    Sabe en qué nodo está y adapta su comportamiento.
    """

    def __init__(self):
        self._messages: list[MiniChatV2Message] = []
        self._current_node_type: Optional[str] = None
        self._current_node_id: Optional[str] = None

    def set_context(self, node_type: str, node_id: str) -> dict:
        self._current_node_type = node_type
        self._current_node_id = node_id
        self._messages.clear()

        context = NODE_CONTEXTS.get(node_type, DEFAULT_CONTEXT)
        return {
            "node_type": node_type,
            "suggestions": context["suggestions"],
            "greeting": f"MiniChat activo en nodo {node_type}. ¿En qué te ayudo?",
        }

    def get_suggestions(self) -> list[str]:
        context = NODE_CONTEXTS.get(self._current_node_type, DEFAULT_CONTEXT)
        return context["suggestions"]

    def get_system_prompt(self) -> str:
        context = NODE_CONTEXTS.get(self._current_node_type, DEFAULT_CONTEXT)
        return context["system_prompt"]

    async def send_message(self, message: str) -> dict:
        user_msg = MiniChatV2Message(role="user", content=message)
        self._messages.append(user_msg)

        system_prompt = self.get_system_prompt()

        from src.ia.ollama_provider import OllamaProvider
        provider = OllamaProvider()
        from src.ia.interfaces import IAMessage

        messages = [IAMessage(role="system", content=system_prompt)]
        for m in self._messages[-10:]:
            messages.append(IAMessage(role=m.role, content=m.content))

        response = await provider.chat(messages, temperature=0.7)

        assistant_msg = MiniChatV2Message(
            role="assistant", content=response.content
        )
        self._messages.append(assistant_msg)

        return {
            "response": response.content,
            "node_type": self._current_node_type,
            "suggestions": self.get_suggestions(),
        }

    def get_messages(self) -> list[dict]:
        return [
            {"role": m.role, "content": m.content, "timestamp": m.timestamp.isoformat()}
            for m in self._messages
        ]

    def clear(self) -> None:
        self._messages.clear()
        self._current_node_type = None
        self._current_node_id = None
