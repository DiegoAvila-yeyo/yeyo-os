## ═══════════════════════════════════════
## MICRO-FASE 2.12 — RAG Pipeline
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 2.12-1 [VSCODE] — Implementar pipeline RAG (Retrieval-Augmented Generation)

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 2.12 de Capa 2 (Cerebro): implementar el pipeline RAG que combina búsqueda semántica en Flash Memory con generación de respuestas, verificando con anti-alucinación.

CONTEXTO:
- Micro-fases 2.0-2.11 completadas: Flash Memory, Embeddings, Chat, Anti-Alucinación funcionando
- RAG = Retrieval-Augmented Generation: buscar contexto → generar respuesta → verificar
- El pipeline integra: EmbeddingService + FlashMemory + IAProvider + AntiHallucination
- Token budget: 4000 total (system:300 + memories:1000 + history:1500 + input:500 + response:700)
- Hardware: GTX 1060 3GB VRAM, 16GB RAM, WSL2 Ubuntu

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/ia/rag.py:

   Ruta: ~/yeyo-os/src/ia/rag.py
   Contenido:

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
           - Sin fuentes = confianza base de 0.5
           """
           if not sources:
               return 0.5

           # Base: 0.5 + 0.1 por cada fuente (máx 5 fuentes = 1.0)
           source_bonus = min(0.5, len(sources) * 0.1)
           confidence = 0.5 + source_bonus

           return min(1.0, confidence)

2. Actualizar src/ia/__init__.py:

   Ruta: ~/yeyo-os/src/ia/__init__.py
   Contenido:

   from .interfaces import IAProvider, IAMessage, IAResponse
   from .ollama_provider import OllamaProvider
   from .embeddings import EmbeddingService
   from .anti_hallucination import AntiHallucination
   from .rag import RAGPipeline

3. Crear tests:

   Ruta: ~/yeyo-os/tests/unit/ia/test_rag.py
   Contenido:

   """
   Tests para RAGPipeline — Micro-fase 2.12
   Tests unitarios con mocks.
   """

   import pytest
   from unittest.mock import AsyncMock, MagicMock
   from src.ia.rag import RAGPipeline, RAGResult
   from src.ia.interfaces import IAProvider, IAResponse
   from src.ia.anti_hallucination import VerificationResult
   from src.memory.models import Memory


   @pytest.fixture
   def mock_ia():
       ia = AsyncMock(spec=IAProvider)
       ia.chat.return_value = IAResponse(
           content="Respuesta del RAG pipeline",
           model="qwen2.5:3b",
           tokens_used=30,
           latency_ms=200.0,
       )
       return ia


   @pytest.fixture
   def mock_memory():
       fm = AsyncMock()
       fm.search_semantic.return_value = [
           Memory(
               id="src-1",
               content="Python es el lenguaje favorito del usuario",
               type="preference",
               checksum="a" * 64,
           ),
       ]
       return fm


   @pytest.fixture
   def mock_embeddings():
       emb = MagicMock()
       emb.generate.return_value = [0.1] * 384
       return emb


   @pytest.fixture
   def mock_verifier():
       v = AsyncMock()
       v.verify.return_value = VerificationResult(
           verified=True, confidence=0.95
       )
       return v


   @pytest.fixture
   def rag_pipeline(mock_ia, mock_memory, mock_embeddings, mock_verifier):
       return RAGPipeline(
           ia=mock_ia,
           memory=mock_memory,
           embeddings=mock_embeddings,
           anti_hallucination=mock_verifier,
       )


   class TestRAGQuery:
       """Tests del pipeline completo."""

       @pytest.mark.asyncio
       async def test_query_returns_rag_result(self, rag_pipeline):
           result = await rag_pipeline.query("¿Qué lenguaje prefiero?")
           assert isinstance(result, RAGResult)

       @pytest.mark.asyncio
       async def test_query_has_answer(self, rag_pipeline):
           result = await rag_pipeline.query("¿Cuál es mi nombre?")
           assert isinstance(result.answer, str)
           assert len(result.answer) > 0

       @pytest.mark.asyncio
       async def test_query_includes_sources(self, rag_pipeline):
           result = await rag_pipeline.query("¿Qué lenguaje prefiero?")
           assert isinstance(result.sources, list)
           assert len(result.sources) > 0

       @pytest.mark.asyncio
       async def test_query_has_confidence(self, rag_pipeline):
           result = await rag_pipeline.query("Test")
           assert 0.0 <= result.confidence <= 1.0

       @pytest.mark.asyncio
       async def test_query_is_verified(self, rag_pipeline):
           result = await rag_pipeline.query("Test")
           assert result.verified is True

       @pytest.mark.asyncio
       async def test_empty_question(self, rag_pipeline):
           result = await rag_pipeline.query("")
           assert "No recibí" in result.answer

       @pytest.mark.asyncio
       async def test_no_sources_low_confidence(
           self, mock_ia, mock_embeddings, mock_verifier
       ):
           """Sin fuentes, la confianza debe ser 0.5."""
           empty_memory = AsyncMock()
           empty_memory.search_semantic.return_value = []
           pipeline = RAGPipeline(
               ia=mock_ia,
               memory=empty_memory,
               embeddings=mock_embeddings,
               anti_hallucination=mock_verifier,
           )
           result = await pipeline.query("Algo sin memorias")
           assert result.confidence <= 0.5

       @pytest.mark.asyncio
       async def test_verification_failure_reduces_confidence(
           self, mock_ia, mock_memory, mock_embeddings
       ):
           """Verificación fallida reduce la confianza."""
           failing_verifier = AsyncMock()
           failing_verifier.verify.return_value = VerificationResult(
               verified=False, confidence=0.3, flags=["Contradicción"]
           )
           pipeline = RAGPipeline(
               ia=mock_ia,
               memory=mock_memory,
               embeddings=mock_embeddings,
               anti_hallucination=failing_verifier,
           )
           result = await pipeline.query("Test contradicción")
           assert result.verified is False
           assert result.confidence < 1.0

       @pytest.mark.asyncio
       async def test_without_verifier(self, mock_ia, mock_memory, mock_embeddings):
           """Sin verificador, el pipeline funciona igual."""
           pipeline = RAGPipeline(
               ia=mock_ia,
               memory=mock_memory,
               embeddings=mock_embeddings,
               anti_hallucination=None,
           )
           result = await pipeline.query("Test sin verificador")
           assert result.verified is True


   class TestRAGResult:
       """Tests del modelo RAGResult."""

       def test_to_dict_structure(self):
           result = RAGResult(
               answer="Respuesta",
               sources=[
                   Memory(content="Fuente", type="fact", checksum="a" * 64),
               ],
               confidence=0.9,
               verified=True,
               tokens_used=50,
           )
           d = result.to_dict()
           assert "answer" in d
           assert "sources" in d
           assert "confidence" in d
           assert "verified" in d
           assert "tokens_used" in d

       def test_confidence_clamped(self):
           result = RAGResult(answer="Test", confidence=1.5)
           assert result.confidence == 1.0

       def test_default_values(self):
           result = RAGResult(answer="Test")
           assert result.sources == []
           assert result.verified is True
           assert result.tokens_used == 0


   class TestConfidenceCalculation:
       """Tests de cálculo de confianza."""

       def test_no_sources_half_confidence(self, rag_pipeline):
           conf = rag_pipeline._calculate_confidence([], "answer")
           assert conf == 0.5

       def test_one_source_increases_confidence(self, rag_pipeline):
           sources = [Memory(content="A", type="fact", checksum="a" * 64)]
           conf = rag_pipeline._calculate_confidence(sources, "answer")
           assert conf > 0.5

       def test_five_sources_max_confidence(self, rag_pipeline):
           sources = [
               Memory(content=f"S{i}", type="fact", checksum=f"{i}" * 64)
               for i in range(5)
           ]
           conf = rag_pipeline._calculate_confidence(sources, "answer")
           assert conf == 1.0

       def test_confidence_never_exceeds_one(self, rag_pipeline):
           sources = [
               Memory(content=f"S{i}", type="fact", checksum=f"{i}" * 64)
               for i in range(10)
           ]
           conf = rag_pipeline._calculate_confidence(sources, "answer")
           assert conf <= 1.0

4. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/ia/test_rag.py -v

VERIFICAR:
- [ ] Archivo src/ia/rag.py existe
- [ ] Pipeline completo: retrieve → generate → verify
- [ ] Recupera memorias relevantes como fuentes
- [ ] Incluye fuentes en la respuesta
- [ ] Confianza calculada basada en fuentes
- [ ] Anti-alucinación integrada (si disponible)
- [ ] Verificación fallida reduce confianza
- [ ] Funciona sin verificador (graceful)
- [ ] RAGResult tiene to_dict()
- [ ] TODOS los tests pasan

SI FALLA:
- Import error: verificar micro-fases 2.1, 2.3, 2.8, 2.11
- TokenBudget: verificar import de src.chat.token_budget
- Mock configuration: verificar que mocks retornan tipos correctos

NO HACER:
- No exceder el token budget de 4000
- No cachear resultados RAG (cada query es fresca)
- No modificar respuestas automáticamente basándose en verificación
- No bloquear respuestas por baja confianza (solo informar)

GATE: RAGPipeline ejecuta retrieve→generate→verify, incluye fuentes, calcula confianza, integra anti-alucinación, todos los tests pasan.
```
