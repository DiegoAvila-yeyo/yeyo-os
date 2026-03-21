"""
YeyoOS — MemoryExtractor (Extracción de Memorias)
Micro-fase 2.9 — Capa 2: Cerebro

Analiza conversaciones usando IA para extraer información memorable:
- Preferencias: "me gusta Python", "prefiero café"
- Hechos: "mi nombre es Diego", "trabajo en Google"
- Correcciones: "no, no es X, es Y"

Las memorias extraídas se almacenan en Flash Memory y NUNCA se borran.
"""

import json
import logging
from typing import Optional

from src.ia.interfaces import IAProvider, IAMessage

logger = logging.getLogger("yeyoos.extraction")

# Tokens mínimos para intentar extracción
MIN_TOKENS_FOR_EXTRACTION = 20

EXTRACTION_PROMPT = """Analiza el siguiente intercambio de conversación y extrae información memorable.

Mensaje del usuario: {user_message}
Respuesta del asistente: {assistant_message}

Extrae SOLO información personal o relevante. Tipos válidos:
- "preference": gustos, preferencias del usuario (ej: "me gusta Python", "prefiero modo oscuro")
- "fact": hechos sobre el usuario (ej: "mi nombre es Diego", "trabajo en empresa X", "tengo un gato")
- "correction": correcciones del usuario (ej: "no, mi nombre no es Juan, es Diego")

Responde SOLO con un JSON array. Si no hay nada memorable, responde con [].
Formato:
[
  {{"content": "descripción concisa de la memoria", "type": "preference|fact|correction", "metadata": {{"original_text": "texto original del usuario"}}}}
]

IMPORTANTE: Solo extrae información CLARA y EXPLÍCITA. No inventes ni asumas.
Responde SOLO con el JSON, sin texto adicional."""


class MemoryExtractor:
    """
    Extrae memorias de conversaciones usando análisis de IA.
    Solo procesa mensajes suficientemente largos y que parezcan
    contener información personal.
    """

    def __init__(self, ia_provider: IAProvider):
        self.ia = ia_provider

    async def extract_from_message(
        self,
        user_message: str,
        assistant_message: str,
    ) -> list[dict]:
        """
        Analiza un intercambio user/assistant y extrae memorias.
        Retorna lista de {content, type, metadata} o [] si no hay nada.
        """
        if not await self.should_extract(user_message):
            return []

        prompt = EXTRACTION_PROMPT.format(
            user_message=user_message,
            assistant_message=assistant_message,
        )

        try:
            messages = [
                IAMessage(
                    role="system",
                    content="Eres un extractor de información. Respondes SOLO con JSON válido.",
                ),
                IAMessage(role="user", content=prompt),
            ]

            response = await self.ia.chat(messages, temperature=0.1)
            extracted = self._parse_extraction(response.content)

            if extracted:
                logger.info(f"Memorias extraídas: {len(extracted)} de mensaje")
            return extracted

        except Exception as e:
            logger.error(f"Error extrayendo memorias: {e}")
            return []

    async def should_extract(self, message: str) -> bool:
        """
        Determina si un mensaje vale la pena analizar para extracción.
        Criterios:
        - Contiene indicadores de información personal (prioridad)
        - O mensaje > 50 tokens (suficientemente largo para intentar)
        - Mínimo ~5 tokens para evitar ruido en frases con indicadores
        """
        if not message or not message.strip():
            return False

        # Aproximación de tokens
        token_count = max(1, len(message) // 4)

        # Indicadores de información personal (heurística rápida)
        personal_indicators = [
            "me llamo", "mi nombre", "soy ", "trabajo en", "vivo en",
            "me gusta", "prefiero", "mi favorit", "no me gusta",
            "mi edad", "tengo ", "mi correo", "mi email",
            "no, ", "en realidad", "corrección", "error",
            "siempre ", "nunca ", "odio ", "amo ",
            "me encanta", "detesto", "mi pasión",
        ]

        message_lower = message.lower()
        for indicator in personal_indicators:
            if indicator in message_lower:
                # Requiere al menos 5 tokens para evitar ruido puro
                if token_count >= 5:
                    return True

        # Sin indicador personal — requiere mínimo de tokens
        if token_count < MIN_TOKENS_FOR_EXTRACTION:
            return False

        # Mensajes largos siempre se intentan extraer
        if token_count > 50:
            return True

        return False

    def _parse_extraction(self, response_text: str) -> list[dict]:
        """
        Parsea la respuesta del modelo a lista de memorias.
        Maneja JSON malformado grácilmente.
        """
        if not response_text:
            return []

        text = response_text.strip()

        # Intentar encontrar JSON array en la respuesta
        start = text.find("[")
        end = text.rfind("]")

        if start == -1 or end == -1 or end <= start:
            return []

        json_text = text[start:end + 1]

        try:
            parsed = json.loads(json_text)
            if not isinstance(parsed, list):
                return []

            valid_memories = []
            valid_types = {"preference", "fact", "correction"}

            for item in parsed:
                if not isinstance(item, dict):
                    continue
                if "content" not in item or "type" not in item:
                    continue
                if item["type"] not in valid_types:
                    continue
                if not item["content"] or not item["content"].strip():
                    continue

                valid_memories.append({
                    "content": item["content"].strip(),
                    "type": item["type"],
                    "metadata": item.get("metadata", {}),
                })

            return valid_memories

        except json.JSONDecodeError:
            logger.warning(f"Error parseando JSON de extracción: {json_text[:100]}")
            return []
