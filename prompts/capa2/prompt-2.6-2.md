## ═══════════════════════════════════════
## MICRO-FASE 2.6 — Chat Contextual Tests
## Tipo: VSCODE | Prompts: 2 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 2.6-2 [VSCODE] — Tests del chat contextual con memorias

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 2.6, Prompt 2 de 2: tests completos para ContextualChatService.

CONTEXTO:
- Prompt 2.6-1 completado: ContextualChatService implementado
- Token budget: system(300) + memories(1000) + history(1500) + input(500) + response(700) = 4000
- Los tests deben verificar que el budget se respeta ESTRICTAMENTE
- Memorias se buscan semánticamente y se inyectan en contexto

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo tests/unit/chat/test_contextual_service.py:

   Ruta: ~/yeyo-os/tests/unit/chat/test_contextual_service.py
   Contenido:

   """
   Tests para ContextualChatService — Micro-fase 2.6
   Tests unitarios con mocks de IAProvider, FlashMemory y EmbeddingService.
   """

   import pytest
   from unittest.mock import AsyncMock, MagicMock, patch
   from src.chat.contextual_service import (
       ContextualChatService,
       count_tokens,
       truncate_to_tokens,
       BUDGET_SYSTEM,
       BUDGET_MEMORIES,
       BUDGET_HISTORY,
       BUDGET_INPUT,
       BUDGET_RESPONSE,
       BUDGET_TOTAL,
   )
   from src.ia.interfaces import IAProvider, IAMessage, IAResponse
   from src.memory.models import Memory


   @pytest.fixture
   def mock_ia():
       ia = AsyncMock(spec=IAProvider)
       ia.chat.return_value = IAResponse(
           content="Respuesta contextual",
           model="qwen2.5:3b",
           tokens_used=20,
           latency_ms=200.0,
       )
       return ia


   @pytest.fixture
   def mock_memory():
       fm = AsyncMock()
       fm.search_semantic.return_value = [
           Memory(
               id="mem-1",
               content="El usuario prefiere Python",
               type="preference",
               checksum="a" * 64,
           ),
           Memory(
               id="mem-2",
               content="El usuario se llama Diego",
               type="fact",
               checksum="b" * 64,
           ),
       ]
       return fm


   @pytest.fixture
   def mock_embeddings():
       emb = MagicMock()
       emb.generate.return_value = [0.1] * 384
       return emb


   @pytest.fixture
   def contextual_service(mock_ia, mock_memory, mock_embeddings):
       return ContextualChatService(
           ia=mock_ia,
           memory=mock_memory,
           embeddings=mock_embeddings,
       )


   class TestTokenBudgetConstants:
       """Tests de constantes del token budget."""

       def test_total_budget_is_4000(self):
           assert BUDGET_TOTAL == 4000

       def test_budget_components_sum_to_total(self):
           total = BUDGET_SYSTEM + BUDGET_MEMORIES + BUDGET_HISTORY + BUDGET_INPUT + BUDGET_RESPONSE
           assert total == BUDGET_TOTAL

       def test_system_budget(self):
           assert BUDGET_SYSTEM == 300

       def test_memories_budget(self):
           assert BUDGET_MEMORIES == 1000

       def test_history_budget(self):
           assert BUDGET_HISTORY == 1500

       def test_input_budget(self):
           assert BUDGET_INPUT == 500

       def test_response_budget(self):
           assert BUDGET_RESPONSE == 700


   class TestTokenCounting:
       """Tests de conteo y truncación de tokens."""

       def test_count_tokens_approximation(self):
           text = "Hola mundo test"  # 15 chars ≈ 3-4 tokens
           tokens = count_tokens(text)
           assert tokens > 0
           assert tokens == len(text) // 4 or tokens == max(1, len(text) // 4)

       def test_count_tokens_empty(self):
           assert count_tokens("") == 0

       def test_count_tokens_none(self):
           assert count_tokens(None) == 0

       def test_truncate_short_text(self):
           text = "Hola"
           result = truncate_to_tokens(text, 100)
           assert result == text

       def test_truncate_long_text(self):
           text = "a " * 2000  # ~1000 tokens
           result = truncate_to_tokens(text, 10)
           assert count_tokens(result) <= 15  # Algo de margen por truncación


   class TestBuildContext:
       """Tests de construcción de contexto."""

       @pytest.mark.asyncio
       async def test_build_context_returns_dict(self, contextual_service):
           ctx = await contextual_service.build_context("Hola")
           assert isinstance(ctx, dict)

       @pytest.mark.asyncio
       async def test_build_context_has_all_keys(self, contextual_service):
           ctx = await contextual_service.build_context("Hola")
           assert "system_prompt" in ctx
           assert "relevant_memories" in ctx
           assert "conversation_history" in ctx
           assert "user_input" in ctx
           assert "token_usage" in ctx

       @pytest.mark.asyncio
       async def test_build_context_includes_memories(self, contextual_service):
           ctx = await contextual_service.build_context("¿Qué lenguaje prefiero?")
           assert len(ctx["relevant_memories"]) > 0
           assert "Python" in ctx["system_prompt"]

       @pytest.mark.asyncio
       async def test_build_context_token_usage(self, contextual_service):
           ctx = await contextual_service.build_context("Test")
           usage = ctx["token_usage"]
           assert "system" in usage
           assert "memories" in usage
           assert "history" in usage
           assert "input" in usage
           assert "reserved_response" in usage
           assert usage["reserved_response"] == BUDGET_RESPONSE

       @pytest.mark.asyncio
       async def test_build_context_respects_total_budget(self, contextual_service):
           ctx = await contextual_service.build_context("Test con presupuesto")
           assert ctx["token_usage"]["total"] <= BUDGET_TOTAL

       @pytest.mark.asyncio
       async def test_build_context_empty_history(self, contextual_service):
           ctx = await contextual_service.build_context("Test", conversation_history=[])
           assert ctx["conversation_history"] == []

       @pytest.mark.asyncio
       async def test_build_context_with_history(self, contextual_service):
           history = [
               {"role": "user", "content": "Hola"},
               {"role": "assistant", "content": "¡Hola!"},
           ]
           ctx = await contextual_service.build_context("Otra cosa", history)
           assert len(ctx["conversation_history"]) == 2

       @pytest.mark.asyncio
       async def test_build_context_truncates_long_history(self, contextual_service):
           """Historial largo debe truncarse (eliminar mensajes más antiguos)."""
           history = [
               {"role": "user", "content": "x" * 3000}  # ~750 tokens
               for _ in range(10)  # ~7500 tokens total, excede 1500
           ]
           ctx = await contextual_service.build_context("Test", history)
           total_history_tokens = sum(
               count_tokens(m["content"])
               for m in ctx["conversation_history"]
           )
           assert total_history_tokens <= BUDGET_HISTORY

       @pytest.mark.asyncio
       async def test_build_context_no_memories_found(self, mock_ia, mock_embeddings):
           """Sin memorias relevantes, el contexto sigue funcionando."""
           mock_mem = AsyncMock()
           mock_mem.search_semantic.return_value = []
           service = ContextualChatService(
               ia=mock_ia, memory=mock_mem, embeddings=mock_embeddings
           )
           ctx = await service.build_context("Algo sin memorias")
           assert ctx["relevant_memories"] == []


   class TestSendMessage:
       """Tests de envío de mensajes contextuales."""

       @pytest.mark.asyncio
       async def test_send_message_returns_string(self, contextual_service):
           result = await contextual_service.send_message("Hola")
           assert isinstance(result, str)

       @pytest.mark.asyncio
       async def test_send_message_empty_input(self, contextual_service):
           result = await contextual_service.send_message("")
           assert "No recibí" in result

       @pytest.mark.asyncio
       async def test_send_message_calls_ia(self, contextual_service, mock_ia):
           await contextual_service.send_message("Test")
           mock_ia.chat.assert_called_once()

       @pytest.mark.asyncio
       async def test_send_message_with_conversation_id(self, contextual_service):
           result = await contextual_service.send_message(
               "Test", conversation_id="conv-123"
           )
           assert isinstance(result, str)


   class TestSendMessageStream:
       """Tests de streaming contextual."""

       @pytest.mark.asyncio
       async def test_stream_empty_input(self, contextual_service):
           chunks = []
           async for chunk in contextual_service.send_message_stream(""):
               chunks.append(chunk)
           assert "No recibí" in chunks[0]

       @pytest.mark.asyncio
       async def test_stream_generates_chunks(self, mock_ia, mock_memory, mock_embeddings):
           async def fake_stream(*args, **kwargs):
               for chunk in ["Hola", " ", "Diego"]:
                   yield chunk

           mock_ia.chat_stream = fake_stream
           service = ContextualChatService(
               ia=mock_ia, memory=mock_memory, embeddings=mock_embeddings
           )
           chunks = []
           async for chunk in service.send_message_stream("Test"):
               chunks.append(chunk)
           assert len(chunks) == 3

2. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/chat/test_contextual_service.py -v

VERIFICAR:
- [ ] TODOS los tests pasan
- [ ] Token budget TOTAL = 4000 verificado en tests
- [ ] Componentes del budget suman 4000
- [ ] Contexto se construye correctamente con memorias
- [ ] Historial largo se trunca (mensajes antiguos primero)
- [ ] Sin memorias, el chat sigue funcionando
- [ ] Streaming funciona con contexto
- [ ] Input vacío manejado grácilmente

SI FALLA:
- Import error: verificar que prompt 2.6-1 está completado
- AsyncMock: requiere Python 3.8+
- Budget tests: verificar constantes en contextual_service.py

NO HACER:
- No cambiar el budget total de 4000
- No skip tests de budget — son críticos
- No mockear el token counting — verificar la lógica real

GATE: Todos los tests pasan, budget de 4000 tokens respetado estrictamente, contexto se construye con memorias y historial, truncación funciona correctamente.
```
