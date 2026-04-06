"""
YeyoOS — MemoryExtractor (Guardado Directo de Memorias)
Fase 3 — Arquitectura de Memoria por Namespace

Guarda TODOS los mensajes del usuario directamente en Flash Memory
sin filtros de palabras clave. El clasificador asigna el namespace.
El clasificador de tipo determina si es preference/skill/correction/fact/conversation.

Las memorias NUNCA se borran.
"""

import logging
import re

from src.memory.flash_memory import FlashMemory
from src.memory.pipeline_events import pipeline_buffer

logger = logging.getLogger("yeyoos.extraction")

# Mantener por compatibilidad con tests existentes
MIN_TOKENS_FOR_EXTRACTION = 5

# Palabras de ruido puro — mensajes que no aportan información
_NOISE_WORDS = {
    "ok", "okey", "okay", "sí", "si", "no", "yes", "gracias", "thanks",
    "hola", "hello", "hi", "bye", "adios", "adiós", "perfecto", "listo",
    "bien", "bueno", "claro", "entendido", "dale", "sale", "va",
}

_QUESTION_STARTERS = {
    "qué", "que", "cómo", "como", "cuándo", "cuando", "dónde", "donde",
    "por", "quién", "quien", "cuál", "cual", "cuánto", "cuanto",
    "what", "how", "when", "where", "why", "who", "which",
    "sabes", "puedes", "podrías", "puedo", "hay", "tienes",
}

# ─── Patrones heurísticos para clasificar tipo de memoria ───────────────────────

# PREFERENCE: gustos, preferencias, estilo personal
_PREFERENCE_PATTERNS = [
    r"\b(me gusta|prefiero|me encanta|odio|detesto|no me gusta|me agrada)\b",
    r"\b(i like|i love|i hate|i prefer|i enjoy|i dislike)\b",
    r"\b(mi favorit[oa]|my favorite|mi estilo|prefiero usar)\b",
    r"\b(siempre uso|suelo usar|me inclino por|opto por)\b",
    r"\b(no me convence|me parece mejor|me quedo con)\b",
]

# SKILL: conocimientos, habilidades, experiencia
_SKILL_PATTERNS = [
    r"\b(sé (hacer|usar|programar|configurar|diseñar|crear))\b",
    r"\b(aprendí a|ya sé|domino|manejo|conozco)\b",
    r"\b(tengo experiencia|trabajo con|llevo \d+ (años|meses))\b",
    r"\b(i know how|i can|i learned|i'm experienced|i work with)\b",
    r"\b(mi stack|mis herramientas|uso diario)\b",
    r"\b(especializ[oa]|experto en|nivel avanzado)\b",
]

# CORRECTION: correcciones al asistente
_CORRECTION_PATTERNS = [
    r"\b(no[, ]+(es[oa]?|así|eso)|está mal|estás equivocad[oa]|incorrecto)\b",
    r"\b(te equivocas|error|corrección|corrígelo|arréglalo)\b",
    r"\b(no era|no es así|mal[, ]+es|en realidad es)\b",
    r"\b(that'?s wrong|not correct|actually it'?s|you'?re wrong|fix that)\b",
    r"\b(quise decir|me refiero a|lo que quiero es)\b",
    r"\b(no[, ]+(quiero|necesito|pedí) eso)\b",
]

# Compilar patrones para rendimiento
_PREF_RE = [re.compile(p, re.IGNORECASE) for p in _PREFERENCE_PATTERNS]
_SKILL_RE = [re.compile(p, re.IGNORECASE) for p in _SKILL_PATTERNS]
_CORR_RE = [re.compile(p, re.IGNORECASE) for p in _CORRECTION_PATTERNS]


def classify_memory_type(user_message: str, assistant_message: str | None = None) -> str:
    """
    Clasifica el tipo de memoria basado en heurísticas del mensaje.
    Prioridad: correction > preference > skill > fact
    
    correction tiene prioridad porque corregir un error es lo más valioso.
    """
    text = user_message.strip().lower()

    # CORRECTION — máxima prioridad (evitar repetir errores)
    for pattern in _CORR_RE:
        if pattern.search(text):
            return "correction"

    # PREFERENCE — gustos personales
    for pattern in _PREF_RE:
        if pattern.search(text):
            return "preference"

    # SKILL — habilidades y conocimiento
    for pattern in _SKILL_RE:
        if pattern.search(text):
            return "skill"

    # FACT — default para declaraciones informativas
    return "fact"


def _is_noise(message: str) -> bool:
    """Retorna True si el mensaje es ruido puro o una pregunta (no contiene hechos)."""
    if not message or not message.strip():
        return True

    stripped = message.strip()

    # Preguntas no contienen hechos sobre el usuario — no vale la pena guardarlas
    if stripped.endswith("?"):
        return True

    words = [w.strip(".,!?¿¡").lower() for w in stripped.split()]
    words = [w for w in words if w]

    # Mensajes cortos de ruido puro
    if len(words) <= 2 and all(w in _NOISE_WORDS for w in words):
        return True

    # Empieza con palabra interrogativa
    if words and words[0] in _QUESTION_STARTERS:
        return True

    return False


class MemoryExtractor:
    """
    Guarda mensajes del usuario directamente en Flash Memory.
    No filtra por palabras clave — guarda todo excepto ruido puro.
    Clasifica automáticamente el tipo (preference/skill/correction/fact).
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
        assistant_message: str | None = None,
    ) -> bool:
        """
        Guarda el mensaje del usuario directamente sin filtros.
        Retorna True si se guardó, False si era ruido puro.
        Emite eventos al pipeline_buffer para visualización en MemoryMap.
        """
        pid = pipeline_buffer.new_pipeline(source="chat")
        pipeline_buffer.emit(pid, "RECEIVED", "ok", user_message[:80],
                             {"content": user_message[:200]})

        if _is_noise(user_message):
            pipeline_buffer.emit(pid, "NOISE_CHECK", "skip",
                                 "Filtrado como ruido",
                                 {"reason": "noise"})
            return False

        pipeline_buffer.emit(pid, "NOISE_CHECK", "ok", "Mensaje significativo")

        memory_type = classify_memory_type(user_message, assistant_message)
        pipeline_buffer.emit(pid, "TYPE_CLASSIFY", "ok", f"Tipo: {memory_type}",
                             {"type": memory_type})

        embedding = None
        if embedding_service:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                embedding = await loop.run_in_executor(
                    None, embedding_service.generate, user_message
                )
                pipeline_buffer.emit(pid, "EMBEDDING", "ok",
                                     f"Vector generado ({len(embedding)} dims)",
                                     {"dims": len(embedding) if embedding else 0})
            except Exception as e:
                pipeline_buffer.emit(pid, "EMBEDDING", "error",
                                     f"Falló: {str(e)[:100]}",
                                     {"error": str(e)[:200]})
        else:
            pipeline_buffer.emit(pid, "EMBEDDING", "skip",
                                 "Sin servicio de embedding")

        try:
            await flash_memory.store(
                content=user_message,
                type=memory_type,
                metadata={"original_text": user_message, "classified_type": memory_type},
                embedding=embedding,
                source="chat_extraction",
                namespace=namespace,
            )
            pipeline_buffer.emit(pid, "STORED", "ok",
                                 f"Guardado en {namespace}",
                                 {"namespace": namespace, "type": memory_type})
        except Exception as e:
            pipeline_buffer.emit(pid, "STORED", "error",
                                 f"Error al guardar: {str(e)[:100]}",
                                 {"error": str(e)[:200]})
            return False

        logger.info(f"Memoria [{memory_type}] guardada: {user_message[:60]}")
        return True

    async def should_extract(self, message: str) -> bool:
        """Compatibilidad con código existente — usa _is_noise internamente."""
        return not _is_noise(message)

    async def extract_from_message(self, user_message: str, assistant_message: str) -> list[dict]:
        """Compatibilidad con código existente — retorna el mensaje como un solo hecho."""
        if _is_noise(user_message):
            return []
        memory_type = classify_memory_type(user_message, assistant_message)
        return [{
            "content": user_message,
            "type": memory_type,
            "metadata": {"original_text": user_message, "classified_type": memory_type},
        }]

