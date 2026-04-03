"""
YeyoOS — RAGPipeline (Retrieval-Augmented Generation)
Micro-fase 2.12 — Capa 2: Cerebro

Pipeline completo que:
1. Busca contexto relevante en Flash Memory (Retrieval)
2. Construye prompt enriquecido con contexto (Augmented)
3. Genera respuesta con el modelo (Generation)
4. Verifica contra hechos conocidos (Anti-Hallucination)
"""

import logging
from typing import Optional

from src.ia.interfaces import IAProvider, IAMessage, IAResponse
from src.ia.embeddings import EmbeddingService
from src.ia.anti_hallucination import AntiHallucination, VerificationResult
from src.memory.flash_memory import FlashMemory
from src.memory.models import Memory
from src.chat.token_budget import TokenBudget

logger = logging.getLogger("yeyoos.rag")


class RAGResult:
    """Resultado de una consulta RAG."""

    def __init__(
        self,
        answer: str,
        sources: list[Memory] = None,
        confidence: float = 1.0,
        verified: bool = True,
        verification: Optional[VerificationResult] = None,
        tokens_used: int = 0,
    ):
        self.answer = answer
        self.sources = sources or []
        self.confidence = min(1.0, max(0.0, confidence))
        self.verified = verified
        self.verification = verification
        self.tokens_used = tokens_used

    def to_dict(self) -> dict:
        return {
            "answer": self.answer,
            "sources": [
                {
                    "id": s.id,
                    "content": s.content,
                    "type": s.type,
                    "tier": s.tier,
                }
                for s in self.sources
            ],
            "confidence": self.confidence,
            "verified": self.verified,
            "tokens_used": self.tokens_used,
        }


class RAGPipeline:
    """
    Pipeline de Retrieval-Augmented Generation.
    Combina búsqueda semántica + generación + verificación.
    """

    def __init__(
        self,
        ia: IAProvider,
        memory: FlashMemory,
        embeddings: EmbeddingService,
        anti_hallucination: Optional[AntiHallucination] = None,
    ):
        self.ia = ia
        self.memory = memory
        self.embeddings = embeddings
        self.verifier = anti_hallucination

    async def query(self, question: str) -> RAGResult:
        """
        Ejecuta el pipeline RAG completo:
        1. Embed question
        2. Search Flash Memory semantically
        3. Build context from retrieved memories
        4. Generate response with context
        5. Verify with anti-hallucination

        Retorna RAGResult con respuesta, fuentes y confianza.
        """
        if not question or not question.strip():
            return RAGResult(
                answer="No recibí ninguna pregunta. ¿En qué puedo ayudarte?",
                confidence=1.0,
            )

        # 1. Generar embedding de la pregunta
        logger.info(f"RAG: Procesando pregunta ({len(question)} chars)")
        question_embedding = self.embeddings.generate(question)

        # 2. Buscar memorias relevantes
        sources = await self._retrieve(question_embedding)
        logger.info(f"RAG: {len(sources)} memorias recuperadas")

        # 3. Construir contexto y generar respuesta
        answer, tokens_used = await self._generate(question, sources)

        # 4. Calcular confianza base
        confidence = self._calculate_confidence(sources, answer)

        # 5. Verificar con anti-alucinación (si disponible)
        verification = None
        verified = True
        if self.verifier:
            verification = await self.verifier.verify(answer)
            verified = verification.verified
            if not verified:
                confidence = min(confidence, verification.confidence)
                logger.warning(
                    f"RAG: Verificación falló con confianza {verification.confidence}"
                )

        result = RAGResult(
            answer=answer,
            sources=sources,
            confidence=confidence,
            verified=verified,
            verification=verification,
            tokens_used=tokens_used,
        )

        logger.info(
            f"RAG: Respuesta generada. Confianza={confidence:.2f}, "
            f"Verificada={verified}, Fuentes={len(sources)}"
        )
        return result

    async def _retrieve(
        self,
        embedding: list[float],
        limit: int = 5,
        threshold: float = 0.5,
    ) -> list[Memory]:
        """Fase de Retrieval: buscar memorias relevantes."""
        try:
            # Validate embedding dimensions
            if not embedding or len(embedding) != self.embeddings.dimension:
                logger.error(
                    f"RAG Retrieve: Invalid embedding dimensions. "
                    f"Expected {self.embeddings.dimension}, got {len(embedding) if embedding else 0}"
                )
                return []
            
            memories = await self.memory.search_semantic(
                embedding=embedding,
                threshold=threshold,
                limit=limit,
            )
            # Filtrar por budget de tokens
            return TokenBudget.fit_memories(memories, TokenBudget.MEMORIES)
        except Exception as e:
            logger.error(f"RAG Retrieve error: {e}")
            return []

    async def _generate(
        self,
        question: str,
        sources: list[Memory],
    ) -> tuple[str, int]:
        """Fase de Generation: generar respuesta con contexto."""
        # Construir contexto
        context_text = ""
        if sources:
            context_lines = [
                f"- [{s.type}] {s.content}" for s in sources
            ]
            context_text = "\n".join(context_lines)

        system_prompt = (
            "Eres YeyoOS, un asistente de IA con memoria persistente. "
            "Usa la información de contexto proporcionada para dar respuestas "
            "precisas y personalizadas. Si no tienes información suficiente, "
            "dilo honestamente."
        )

        # Truncar al budget
        system_prompt = TokenBudget.truncate_to_budget(
            system_prompt, TokenBudget.SYSTEM
        )
        question = TokenBudget.truncate_to_budget(
            question, TokenBudget.INPUT
        )

        messages = [
            IAMessage(role="system", content=system_prompt),
        ]

        if context_text:
            context_msg = TokenBudget.truncate_to_budget(
                f"[CONTEXTO DE MEMORIA]\n{context_text}",
                TokenBudget.MEMORIES,
            )
            messages.append(IAMessage(role="system", content=context_msg))

        messages.append(IAMessage(role="user", content=question))

        try:
            response: IAResponse = await self.ia.chat(messages)
            return response.content, response.tokens_used
        except Exception as e:
            logger.error(f"RAG Generate error: {e}")
            return (
                "Lo siento, hubo un error generando la respuesta. "
                "Por favor intenta de nuevo.",
                0,
            )

    def _calculate_confidence(
        self, sources: list[Memory], answer: str
    ) -> float:
        """
        Calcula confianza base de la respuesta.
        - Más fuentes = más confianza
        - Sin fuentes = confianza base de 0.1 (muy baja)
        - Con 5 fuentes = 1.0
        """
        if not sources:
            return 0.1  # No sources = very low confidence

        # Base: 0.1 + 0.18 per source (5 sources = 1.0)
        source_bonus = min(0.9, len(sources) * 0.18)
        confidence = 0.1 + source_bonus

        return min(1.0, confidence)
