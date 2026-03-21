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
