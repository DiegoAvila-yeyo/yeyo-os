"""
YeyoOS — MemoryExtractor (Guardado Directo de Memorias)
Fase 3 — Arquitectura de Memoria por Namespace

Guarda TODOS los mensajes del usuario directamente en Flash Memory
sin filtros de palabras clave. El clasificador asigna el namespace.

Las memorias NUNCA se borran.
"""

import logging

from src.memory.flash_memory import FlashMemory

logger = logging.getLogger("yeyoos.extraction")

# Mantener por compatibilidad con tests existentes
MIN_TOKENS_FOR_EXTRACTION = 5

# Palabras de ruido puro — mensajes que no aportan información
_NOISE_WORDS = {
    "ok", "okey", "okay", "sí", "si", "no", "yes", "gracias", "thanks",
    "hola", "hello", "hi", "bye", "adios", "adiós", "perfecto", "listo",
    "bien", "bueno", "claro", "entendido", "dale", "sale", "va",
}


def _is_noise(message: str) -> bool:
    """Retorna True si el mensaje es ruido puro (< 3 palabras sin contenido)."""
    if not message or not message.strip():
        return True
    words = [w.strip(".,!?¿¡").lower() for w in message.strip().split()]
    words = [w for w in words if w]
    if len(words) <= 2 and all(w in _NOISE_WORDS for w in words):
        return True
    return False


class MemoryExtractor:
    """
    Guarda mensajes del usuario directamente en Flash Memory.
    No filtra por palabras clave — guarda todo excepto ruido puro.
    El NamespaceClassifier asigna el namespace en background.
    """

    def __init__(self, ia_provider=None):
        # ia_provider se mantiene por compatibilidad, ya no se usa para extracción
        self._ia = ia_provider

    async def extract_and_store(
        self,
        user_message: str,
        flash_memory: FlashMemory,
        embedding_service=None,
        namespace: str = "chat:usuario",
    ) -> bool:
        """
        Guarda el mensaje del usuario directamente sin filtros.
        Retorna True si se guardó, False si era ruido puro.
        """
        if _is_noise(user_message):
            return False

        embedding = None
        if embedding_service:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                embedding = await loop.run_in_executor(
                    None, embedding_service.generate, user_message
                )
            except Exception:
                pass

        await flash_memory.store(
            content=user_message,
            type="fact",
            metadata={"original_text": user_message},
            embedding=embedding,
            source="chat_extraction",
            namespace=namespace,
        )
        logger.debug(f"Mensaje guardado directamente: {user_message[:60]}")
        return True

    async def should_extract(self, message: str) -> bool:
        """Compatibilidad con código existente — usa _is_noise internamente."""
        return not _is_noise(message)

    async def extract_from_message(self, user_message: str, assistant_message: str) -> list[dict]:
        """Compatibilidad con código existente — retorna el mensaje como un solo hecho."""
        if _is_noise(user_message):
            return []
        return [{
            "content": user_message,
            "type": "fact",
            "metadata": {"original_text": user_message},
        }]

