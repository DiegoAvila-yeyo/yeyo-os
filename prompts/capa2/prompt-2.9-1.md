## ═══════════════════════════════════════
## MICRO-FASE 2.9 — Memory Extraction
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 2.9-1 [VSCODE] — Implementar extracción de memorias desde conversaciones

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 2.9 de Capa 2 (Cerebro): implementar el MemoryExtractor que analiza conversaciones y extrae memorias relevantes (preferencias, hechos, correcciones) para almacenar en Flash Memory.

CONTEXTO:
- Micro-fases 2.0-2.8 completadas: Flash Memory, Cache, Chat, Token Budget funcionando
- El extractor usa Ollama (IAProvider) para analizar mensajes y detectar información memorable
- Tipos de memoria a extraer: preference, fact, correction
- Solo extrae de mensajes >20 tokens (mensajes cortos raramente contienen info personal)
- Las memorias extraídas se almacenan en Flash Memory (NUNCA se borran)
- Hardware: GTX 1060 3GB VRAM, 16GB RAM, WSL2 Ubuntu

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/memory/extraction.py:

   Ruta: ~/yeyo-os/src/memory/extraction.py
   Contenido:

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
           - Mensaje > 20 tokens (~80 caracteres)
           - Contiene indicadores de información personal
           """
           if not message or not message.strip():
               return False

           # Aproximación de tokens
           token_count = max(1, len(message) // 4)
           if token_count < MIN_TOKENS_FOR_EXTRACTION:
               return False

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
                   return True

           # Si es suficientemente largo, intentar de todas formas
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

           # Limpiar respuesta
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

               # Validar cada memoria extraída
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

2. Actualizar src/memory/__init__.py:

   Ruta: ~/yeyo-os/src/memory/__init__.py
   Contenido:

   from .flash_memory import FlashMemory
   from .models import Memory
   from .cache import MemoryCache
   from .tier_manager import TierManager
   from .extraction import MemoryExtractor

3. Crear tests:

   Ruta: ~/yeyo-os/tests/unit/memory/test_extraction.py
   Contenido:

   """
   Tests para MemoryExtractor — Micro-fase 2.9
   Tests unitarios con mock de IAProvider.
   """

   import pytest
   import json
   from unittest.mock import AsyncMock
   from src.memory.extraction import (
       MemoryExtractor,
       MIN_TOKENS_FOR_EXTRACTION,
   )
   from src.ia.interfaces import IAProvider, IAResponse


   @pytest.fixture
   def mock_ia():
       return AsyncMock(spec=IAProvider)


   @pytest.fixture
   def extractor(mock_ia):
       return MemoryExtractor(ia_provider=mock_ia)


   class TestShouldExtract:
       """Tests de la heurística should_extract."""

       @pytest.mark.asyncio
       async def test_empty_message(self, extractor):
           assert await extractor.should_extract("") is False

       @pytest.mark.asyncio
       async def test_none_message(self, extractor):
           assert await extractor.should_extract(None) is False

       @pytest.mark.asyncio
       async def test_short_message(self, extractor):
           """Mensajes < 20 tokens no se extraen."""
           assert await extractor.should_extract("Hola") is False

       @pytest.mark.asyncio
       async def test_preference_detected(self, extractor):
           assert await extractor.should_extract(
               "Me gusta programar en Python porque es muy elegante y productivo"
           ) is True

       @pytest.mark.asyncio
       async def test_fact_detected(self, extractor):
           assert await extractor.should_extract(
               "Mi nombre es Diego y trabajo en una empresa de tecnología"
           ) is True

       @pytest.mark.asyncio
       async def test_correction_detected(self, extractor):
           assert await extractor.should_extract(
               "No, en realidad mi nombre no es Juan, es Diego. Siempre lo confunden."
           ) is True

       @pytest.mark.asyncio
       async def test_long_message_always_extracted(self, extractor):
           """Mensajes >50 tokens siempre se intentan extraer."""
           long_msg = "palabra " * 60  # ~60 tokens
           assert await extractor.should_extract(long_msg) is True

       @pytest.mark.asyncio
       async def test_min_tokens_threshold(self):
           assert MIN_TOKENS_FOR_EXTRACTION == 20


   class TestExtractFromMessage:
       """Tests de extracción completa."""

       @pytest.mark.asyncio
       async def test_extracts_preference(self, extractor, mock_ia):
           mock_ia.chat.return_value = IAResponse(
               content='[{"content": "Prefiere Python", "type": "preference", "metadata": {}}]',
               model="qwen2.5:3b",
               tokens_used=20,
               latency_ms=100.0,
           )
           result = await extractor.extract_from_message(
               "Me gusta mucho programar en Python, es mi lenguaje favorito para todo",
               "¡Genial! Python es muy versátil.",
           )
           assert len(result) == 1
           assert result[0]["type"] == "preference"
           assert "Python" in result[0]["content"]

       @pytest.mark.asyncio
       async def test_extracts_fact(self, extractor, mock_ia):
           mock_ia.chat.return_value = IAResponse(
               content='[{"content": "Se llama Diego", "type": "fact", "metadata": {}}]',
               model="qwen2.5:3b",
               tokens_used=15,
               latency_ms=100.0,
           )
           result = await extractor.extract_from_message(
               "Mi nombre es Diego y soy programador senior en una startup",
               "¡Hola Diego! Encantado de conocerte.",
           )
           assert len(result) == 1
           assert result[0]["type"] == "fact"

       @pytest.mark.asyncio
       async def test_extracts_correction(self, extractor, mock_ia):
           mock_ia.chat.return_value = IAResponse(
               content='[{"content": "Su nombre es Diego, no Juan", "type": "correction", "metadata": {}}]',
               model="qwen2.5:3b",
               tokens_used=20,
               latency_ms=100.0,
           )
           result = await extractor.extract_from_message(
               "No, en realidad mi nombre no es Juan, es Diego. Por favor recuérdalo.",
               "Disculpa, Diego. Lo tendré en cuenta.",
           )
           assert len(result) == 1
           assert result[0]["type"] == "correction"

       @pytest.mark.asyncio
       async def test_short_message_returns_empty(self, extractor):
           result = await extractor.extract_from_message("OK", "OK")
           assert result == []

       @pytest.mark.asyncio
       async def test_no_memories_found(self, extractor, mock_ia):
           mock_ia.chat.return_value = IAResponse(
               content="[]",
               model="qwen2.5:3b",
               tokens_used=5,
               latency_ms=50.0,
           )
           result = await extractor.extract_from_message(
               "Me gusta el clima de hoy, está muy agradable para salir a caminar por el parque",
               "Sí, el clima es agradable.",
           )
           assert result == []

       @pytest.mark.asyncio
       async def test_malformed_json_returns_empty(self, extractor, mock_ia):
           mock_ia.chat.return_value = IAResponse(
               content="esto no es json para nada",
               model="qwen2.5:3b",
               tokens_used=5,
               latency_ms=50.0,
           )
           result = await extractor.extract_from_message(
               "Me gusta Python mucho, es mi lenguaje favorito de todos los tiempos",
               "Genial!",
           )
           assert result == []

       @pytest.mark.asyncio
       async def test_extraction_format_correct(self, extractor, mock_ia):
           mock_ia.chat.return_value = IAResponse(
               content='[{"content": "Test", "type": "fact", "metadata": {"key": "val"}}]',
               model="qwen2.5:3b",
               tokens_used=10,
               latency_ms=50.0,
           )
           result = await extractor.extract_from_message(
               "Mi nombre es Test y tengo treinta años, vivo en una ciudad grande",
               "Hola Test",
           )
           assert len(result) == 1
           assert "content" in result[0]
           assert "type" in result[0]
           assert "metadata" in result[0]

       @pytest.mark.asyncio
       async def test_invalid_type_filtered(self, extractor, mock_ia):
           mock_ia.chat.return_value = IAResponse(
               content='[{"content": "Test", "type": "invalid_type", "metadata": {}}]',
               model="qwen2.5:3b",
               tokens_used=10,
               latency_ms=50.0,
           )
           result = await extractor.extract_from_message(
               "Me gusta Python mucho, es mi lenguaje favorito de todos los tiempos",
               "Genial",
           )
           assert result == []

       @pytest.mark.asyncio
       async def test_ia_error_returns_empty(self, extractor, mock_ia):
           mock_ia.chat.side_effect = Exception("Ollama error")
           result = await extractor.extract_from_message(
               "Mi nombre es Diego y soy programador, trabajo en tecnología",
               "Hola Diego",
           )
           assert result == []

4. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/memory/test_extraction.py -v

VERIFICAR:
- [ ] Archivo src/memory/extraction.py existe
- [ ] Extrae preferencias ("me gusta Python")
- [ ] Extrae hechos ("mi nombre es Diego")
- [ ] Extrae correcciones ("no, no es X, es Y")
- [ ] Mensajes cortos (<20 tokens) retornan []
- [ ] JSON malformado retorna [] (no crash)
- [ ] Tipos inválidos filtrados
- [ ] Errores de IA manejados grácilmente
- [ ] Formato de salida correcto: {content, type, metadata}
- [ ] TODOS los tests pasan

SI FALLA:
- Import IAProvider: verificar Capa 1
- Mock async: verificar AsyncMock usage
- JSON parsing: verificar que el prompt genera JSON válido

NO HACER:
- No extraer memorias de mensajes cortos (ruido)
- No inventar memorias — solo extraer lo explícito
- No almacenar directamente (el caller decide cuándo almacenar en Flash Memory)
- No ejecutar extracción en cada mensaje (usar should_extract primero)

GATE: MemoryExtractor extrae preferencias, hechos y correcciones correctamente, filtra mensajes cortos, maneja errores, todos los tests pasan.
```
