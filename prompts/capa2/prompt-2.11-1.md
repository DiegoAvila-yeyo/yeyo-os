## ═══════════════════════════════════════
## MICRO-FASE 2.11 — Anti-Hallucination System
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 2.11-1 [VSCODE] — Implementar sistema anti-alucinación

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 2.11 de Capa 2 (Cerebro): implementar el sistema anti-alucinación que verifica las respuestas de la IA contra hechos conocidos en Flash Memory.

CONTEXTO:
- Micro-fases 2.0-2.10 completadas: Flash Memory, Embeddings, Asociaciones funcionando
- Solo se verifican respuestas >50 tokens (respuestas cortas no necesitan verificación)
- La verificación busca contradicciones con hechos almacenados en Flash Memory
- Si detecta contradicción, sugiere corrección pero NO modifica la respuesta automáticamente
- Hardware: GTX 1060 3GB VRAM, 16GB RAM, WSL2 Ubuntu

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/ia/anti_hallucination.py:

   Ruta: ~/yeyo-os/src/ia/anti_hallucination.py
   Contenido:

   """
   YeyoOS — AntiHallucination (Sistema Anti-Alucinación)
   Micro-fase 2.11 — Capa 2: Cerebro

   Verifica respuestas de la IA contra hechos conocidos en Flash Memory.
   Solo verifica respuestas >50 tokens.
   Detecta contradicciones y sugiere correcciones sin modificar la respuesta.
   """

   import logging
   from typing import Optional

   from src.ia.interfaces import IAProvider, IAMessage, IAResponse
   from src.ia.embeddings import EmbeddingService
   from src.memory.flash_memory import FlashMemory
   from src.memory.models import Memory

   logger = logging.getLogger("yeyoos.anti_hallucination")

   # Umbral mínimo de tokens para activar verificación
   MIN_TOKENS_FOR_VERIFICATION = 50

   VERIFICATION_PROMPT = """Analiza si la siguiente respuesta de IA contradice alguno de los hechos conocidos.

   RESPUESTA DE LA IA:
   {response}

   HECHOS CONOCIDOS:
   {facts}

   Responde SOLO con JSON:
   {{
     "has_contradiction": true/false,
     "contradictions": ["descripción de cada contradicción encontrada"],
     "confidence": 0.0-1.0,
     "corrections": ["corrección sugerida para cada contradicción"]
   }}

   Si no hay contradicciones, responde:
   {{"has_contradiction": false, "contradictions": [], "confidence": 1.0, "corrections": []}}

   IMPORTANTE: Solo marca como contradicción si hay una CLARA inconsistencia con los hechos.
   Responde SOLO con JSON válido."""


   class VerificationResult:
       """Resultado de una verificación anti-alucinación."""

       def __init__(
           self,
           verified: bool,
           confidence: float,
           flags: list[str] = None,
           corrections: list[str] = None,
           skipped: bool = False,
           reason: str = "",
       ):
           self.verified = verified
           self.confidence = min(1.0, max(0.0, confidence))
           self.flags = flags or []
           self.corrections = corrections or []
           self.skipped = skipped
           self.reason = reason

       def to_dict(self) -> dict:
           return {
               "verified": self.verified,
               "confidence": self.confidence,
               "flags": self.flags,
               "corrections": self.corrections,
               "skipped": self.skipped,
               "reason": self.reason,
           }


   class AntiHallucination:
       """
       Sistema de verificación anti-alucinación.
       Compara respuestas de la IA contra hechos en Flash Memory
       para detectar contradicciones e inconsistencias.
       """

       def __init__(
           self,
           ia_provider: IAProvider,
           flash_memory: FlashMemory,
           embeddings: EmbeddingService,
       ):
           self.ia = ia_provider
           self.memory = flash_memory
           self.embeddings = embeddings

       async def verify(
           self,
           response: str,
           context: dict = None,
       ) -> VerificationResult:
           """
           Verifica una respuesta de IA contra hechos conocidos.
           Solo verifica si la respuesta >50 tokens.

           Pasos:
           1. Verificar si la respuesta necesita verificación
           2. Buscar hechos relevantes en Flash Memory
           3. Comparar respuesta contra hechos
           4. Retornar resultado con confianza y flags
           """
           if not await self.should_verify(response):
               return VerificationResult(
                   verified=True,
                   confidence=1.0,
                   skipped=True,
                   reason="Respuesta menor a 50 tokens, verificación omitida",
               )

           # Buscar hechos relevantes en Flash Memory
           facts = await self._get_relevant_facts(response)

           if not facts:
               return VerificationResult(
                   verified=True,
                   confidence=0.8,
                   reason="Sin hechos conocidos para comparar",
               )

           # Verificar con IA
           try:
               result = await self._verify_against_facts(response, facts)
               return result
           except Exception as e:
               logger.error(f"Error en verificación: {e}")
               return VerificationResult(
                   verified=True,
                   confidence=0.5,
                   flags=["Error durante verificación"],
                   reason=f"Error: {str(e)}",
               )

       async def should_verify(self, response: str) -> bool:
           """
           Determina si una respuesta necesita verificación.
           Solo verifica respuestas >50 tokens.
           """
           if not response or not response.strip():
               return False
           token_count = max(1, len(response) // 4)
           return token_count > MIN_TOKENS_FOR_VERIFICATION

       async def _get_relevant_facts(
           self, response: str, limit: int = 10
       ) -> list[Memory]:
           """Busca hechos y correcciones relevantes en Flash Memory."""
           try:
               embedding = self.embeddings.generate(response)

               # Buscar hechos semánticamente relacionados
               facts = await self.memory.search_semantic(
                   embedding=embedding,
                   threshold=0.5,
                   limit=limit,
               )

               # Filtrar solo facts y corrections (los más confiables)
               relevant = [
                   f for f in facts
                   if f.type in ("fact", "correction", "preference")
               ]
               return relevant

           except Exception as e:
               logger.warning(f"Error buscando hechos: {e}")
               return []

       async def _verify_against_facts(
           self, response: str, facts: list[Memory]
       ) -> VerificationResult:
           """Usa IA para verificar respuesta contra hechos."""
           facts_text = "\n".join(
               f"- [{f.type}] {f.content}" for f in facts
           )

           prompt = VERIFICATION_PROMPT.format(
               response=response,
               facts=facts_text,
           )

           messages = [
               IAMessage(
                   role="system",
                   content="Eres un verificador de hechos. Respondes SOLO con JSON válido.",
               ),
               IAMessage(role="user", content=prompt),
           ]

           ia_response = await self.ia.chat(messages, temperature=0.1)

           return self._parse_verification(ia_response.content)

       def _parse_verification(self, response_text: str) -> VerificationResult:
           """Parsea la respuesta del verificador."""
           import json

           if not response_text:
               return VerificationResult(
                   verified=True,
                   confidence=0.5,
                   reason="Respuesta vacía del verificador",
               )

           try:
               # Buscar JSON en la respuesta
               text = response_text.strip()
               start = text.find("{")
               end = text.rfind("}")

               if start == -1 or end == -1:
                   return VerificationResult(
                       verified=True,
                       confidence=0.5,
                       reason="No se encontró JSON en respuesta del verificador",
                   )

               parsed = json.loads(text[start:end + 1])

               has_contradiction = parsed.get("has_contradiction", False)
               contradictions = parsed.get("contradictions", [])
               confidence = parsed.get("confidence", 0.5)
               corrections = parsed.get("corrections", [])

               return VerificationResult(
                   verified=not has_contradiction,
                   confidence=float(confidence),
                   flags=contradictions,
                   corrections=corrections,
               )

           except (json.JSONDecodeError, KeyError, TypeError) as e:
               logger.warning(f"Error parseando verificación: {e}")
               return VerificationResult(
                   verified=True,
                   confidence=0.5,
                   reason=f"Error parseando: {str(e)}",
               )

2. Actualizar src/ia/__init__.py:

   Ruta: ~/yeyo-os/src/ia/__init__.py
   Contenido:

   from .interfaces import IAProvider, IAMessage, IAResponse
   from .ollama_provider import OllamaProvider
   from .embeddings import EmbeddingService
   from .anti_hallucination import AntiHallucination

3. Crear tests:

   Ruta: ~/yeyo-os/tests/unit/ia/test_anti_hallucination.py
   Contenido:

   """
   Tests para AntiHallucination — Micro-fase 2.11
   Tests unitarios con mocks.
   """

   import pytest
   from unittest.mock import AsyncMock, MagicMock
   from src.ia.anti_hallucination import (
       AntiHallucination,
       VerificationResult,
       MIN_TOKENS_FOR_VERIFICATION,
   )
   from src.ia.interfaces import IAProvider, IAResponse
   from src.memory.models import Memory


   @pytest.fixture
   def mock_ia():
       return AsyncMock(spec=IAProvider)


   @pytest.fixture
   def mock_memory():
       fm = AsyncMock()
       fm.search_semantic = AsyncMock(return_value=[])
       return fm


   @pytest.fixture
   def mock_embeddings():
       emb = MagicMock()
       emb.generate.return_value = [0.1] * 384
       return emb


   @pytest.fixture
   def anti_hallucination(mock_ia, mock_memory, mock_embeddings):
       return AntiHallucination(
           ia_provider=mock_ia,
           flash_memory=mock_memory,
           embeddings=mock_embeddings,
       )


   class TestShouldVerify:
       """Tests de umbral de verificación."""

       @pytest.mark.asyncio
       async def test_short_response_skipped(self, anti_hallucination):
           """Respuestas <50 tokens no se verifican."""
           assert await anti_hallucination.should_verify("Hola") is False

       @pytest.mark.asyncio
       async def test_empty_response_skipped(self, anti_hallucination):
           assert await anti_hallucination.should_verify("") is False

       @pytest.mark.asyncio
       async def test_none_response_skipped(self, anti_hallucination):
           assert await anti_hallucination.should_verify(None) is False

       @pytest.mark.asyncio
       async def test_long_response_verified(self, anti_hallucination):
           """Respuestas >50 tokens sí se verifican."""
           long_text = "palabra " * 60  # ~60 tokens
           assert await anti_hallucination.should_verify(long_text) is True

       def test_threshold_is_50(self):
           assert MIN_TOKENS_FOR_VERIFICATION == 50


   class TestVerify:
       """Tests de verificación completa."""

       @pytest.mark.asyncio
       async def test_short_response_returns_verified(self, anti_hallucination):
           """Respuestas cortas se marcan como verificadas sin análisis."""
           result = await anti_hallucination.verify("Respuesta corta")
           assert result.verified is True
           assert result.skipped is True
           assert result.confidence == 1.0

       @pytest.mark.asyncio
       async def test_no_facts_returns_verified(self, anti_hallucination):
           """Sin hechos conocidos, se asume correcto con confianza 0.8."""
           long_response = "Esta es una respuesta larga " * 20
           result = await anti_hallucination.verify(long_response)
           assert result.verified is True
           assert result.confidence == 0.8

       @pytest.mark.asyncio
       async def test_contradiction_detected(
           self, anti_hallucination, mock_ia, mock_memory
       ):
           """Contradicción con hechos conocidos se detecta."""
           mock_memory.search_semantic.return_value = [
               Memory(
                   content="El usuario se llama Diego",
                   type="fact",
                   checksum="a" * 64,
               ),
           ]
           mock_ia.chat.return_value = IAResponse(
               content='{"has_contradiction": true, "contradictions": ["Llama al usuario Juan pero su nombre es Diego"], "confidence": 0.3, "corrections": ["Usar Diego en vez de Juan"]}',
               model="qwen2.5:3b",
               tokens_used=30,
               latency_ms=100.0,
           )

           long_response = "Hola Juan, como te mencioné anteriormente " * 10
           result = await anti_hallucination.verify(long_response)
           assert result.verified is False
           assert len(result.flags) > 0
           assert len(result.corrections) > 0
           assert result.confidence < 1.0

       @pytest.mark.asyncio
       async def test_no_contradiction(
           self, anti_hallucination, mock_ia, mock_memory
       ):
           """Respuesta consistente con hechos pasa la verificación."""
           mock_memory.search_semantic.return_value = [
               Memory(
                   content="El usuario se llama Diego",
                   type="fact",
                   checksum="a" * 64,
               ),
           ]
           mock_ia.chat.return_value = IAResponse(
               content='{"has_contradiction": false, "contradictions": [], "confidence": 0.95, "corrections": []}',
               model="qwen2.5:3b",
               tokens_used=20,
               latency_ms=100.0,
           )

           long_response = "Hola Diego, espero que estés bien " * 10
           result = await anti_hallucination.verify(long_response)
           assert result.verified is True
           assert result.confidence > 0.9


   class TestVerificationResult:
       """Tests del modelo VerificationResult."""

       def test_to_dict(self):
           result = VerificationResult(
               verified=True,
               confidence=0.95,
               flags=["flag1"],
               corrections=["fix1"],
           )
           d = result.to_dict()
           assert d["verified"] is True
           assert d["confidence"] == 0.95
           assert "flag1" in d["flags"]

       def test_confidence_clamped(self):
           result = VerificationResult(verified=True, confidence=1.5)
           assert result.confidence == 1.0

           result2 = VerificationResult(verified=True, confidence=-0.5)
           assert result2.confidence == 0.0

       def test_default_values(self):
           result = VerificationResult(verified=True, confidence=0.8)
           assert result.flags == []
           assert result.corrections == []
           assert result.skipped is False
           assert result.reason == ""

       @pytest.mark.asyncio
       async def test_ia_error_handled_gracefully(
           self, anti_hallucination, mock_ia, mock_memory
       ):
           """Error de IA no crashea — retorna resultado con baja confianza."""
           mock_memory.search_semantic.return_value = [
               Memory(content="Hecho", type="fact", checksum="a" * 64),
           ]
           mock_ia.chat.side_effect = Exception("Ollama caído")

           long_response = "Respuesta que necesita verificación " * 20
           result = await anti_hallucination.verify(long_response)
           assert result.verified is True  # Default: no bloquear
           assert result.confidence == 0.5  # Baja confianza
           assert len(result.flags) > 0  # Flag de error

4. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/ia/test_anti_hallucination.py -v

VERIFICAR:
- [ ] Archivo src/ia/anti_hallucination.py existe
- [ ] Respuestas <50 tokens NO se verifican (skip)
- [ ] Contradicciones con hechos conocidos se detectan
- [ ] Confianza entre 0.0 y 1.0
- [ ] Correcciones sugeridas cuando hay contradicción
- [ ] Errores de IA manejados grácilmente (no crashea)
- [ ] Sin hechos en Flash Memory, asume correcto (confianza 0.8)
- [ ] VerificationResult tiene to_dict()
- [ ] TODOS los tests pasan

SI FALLA:
- Import error: verificar micro-fases 2.1 y 2.3
- AsyncMock: verificar Python 3.8+
- JSON parsing: verificar prompt del verificador

NO HACER:
- No verificar TODAS las respuestas (solo >50 tokens)
- No modificar la respuesta automáticamente (solo sugerir correcciones)
- No bloquear respuestas — incluso si hay contradicción, la respuesta se entrega
- No usar verificación para censurar (solo para detectar inconsistencias factuales)

GATE: AntiHallucination verifica respuestas >50 tokens, detecta contradicciones, sugiere correcciones, maneja errores grácilmente, todos los tests pasan.
```
