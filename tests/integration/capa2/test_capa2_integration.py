"""
YeyoOS — Test de Integración Capa 2: Cerebro
Micro-fase 2.18

Flujo completo: memoria → chat → verificación → feedback
Requiere: PostgreSQL + Redis + Ollama corriendo
Ejecutar: pytest tests/integration/capa2/ -v -m integration
"""

import pytest
import os
import asyncio
from datetime import datetime, timezone

pytestmark = pytest.mark.integration

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://yeyo:yeyo@localhost:5432/yeyoos"
)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


# ============================================
# FIXTURES
# ============================================

@pytest.fixture
async def flash_memory():
    from src.memory.flash_memory import FlashMemory
    fm = await FlashMemory.create(DATABASE_URL)
    yield fm
    await fm.close()


@pytest.fixture
async def memory_cache():
    from src.memory.cache import MemoryCache
    cache = MemoryCache(redis_url=REDIS_URL)
    await cache.connect()
    yield cache
    await cache.clear_all()
    await cache.disconnect()


@pytest.fixture(scope="module")
def embedding_service():
    from src.ia.embeddings import EmbeddingService
    return EmbeddingService()


@pytest.fixture
async def conversation_manager():
    from src.chat.conversation import ConversationManager
    cm = await ConversationManager.create(DATABASE_URL)
    yield cm
    await cm.close()



# ============================================
# TEST 1: Flash Memory — Almacenamiento y Recuperación
# ============================================

class TestFlashMemoryIntegration:
    """Tests de Flash Memory end-to-end."""

    @pytest.mark.asyncio
    async def test_store_and_recall(self, flash_memory):
        """Almacenar memoria y recuperarla."""
        mem = await flash_memory.store(
            content="Integration test: Python es mi lenguaje favorito",
            type="preference",
            metadata={"test": "capa2_integration"},
        )
        assert mem.id is not None
        assert mem.checksum != ""
        assert len(mem.checksum) == 64

        found = await flash_memory.get_by_id(mem.id)
        assert found is not None
        assert found.content == mem.content

    @pytest.mark.asyncio
    async def test_store_all_types(self, flash_memory):
        """Todos los tipos de memoria se almacenan correctamente."""
        types = ["conversation", "preference", "fact", "correction", "skill"]
        for t in types:
            mem = await flash_memory.store(
                content=f"Integration test tipo {t}",
                type=t,
            )
            assert mem.type == t
            assert mem.tier == "WARM"

    @pytest.mark.asyncio
    async def test_delete_forbidden(self, flash_memory):
        """DELETE debe ser IMPOSIBLE — trigger lo previene."""
        import asyncpg
        mem = await flash_memory.store(
            content="Memory that must never be deleted",
            type="fact",
        )
        async with flash_memory.pool.acquire() as conn:
            with pytest.raises(asyncpg.RaiseError):
                await conn.execute(
                    "DELETE FROM flash_memories WHERE id = $1",
                    __import__('uuid').UUID(mem.id),
                )

    @pytest.mark.asyncio
    async def test_tier_promotion_demotion(self, flash_memory):
        """Promoción y degradación de tiers funciona."""
        mem = await flash_memory.store(content="Tier test", type="fact")
        assert mem.tier == "WARM"

        promoted = await flash_memory.promote_tier(mem.id)
        assert promoted.tier == "HOT"

        demoted = await flash_memory.demote_tier(mem.id)
        assert demoted.tier == "WARM"

        demoted2 = await flash_memory.demote_tier(mem.id)
        assert demoted2.tier == "COLD"

    @pytest.mark.asyncio
    async def test_stats(self, flash_memory):
        """Estadísticas de memoria son correctas."""
        stats = await flash_memory.get_stats()
        assert stats["total_memories"] > 0
        assert isinstance(stats["by_tier"], dict)
        assert isinstance(stats["by_type"], dict)

    @pytest.mark.asyncio
    async def test_health_check(self, flash_memory):
        """Health check retorna True."""
        assert await flash_memory.health_check() is True


# ============================================
# TEST 2: Cache Redis
# ============================================

class TestCacheIntegration:
    """Tests de caché Redis."""

    @pytest.mark.asyncio
    async def test_cache_set_get(self, memory_cache, flash_memory):
        """Almacenar y recuperar del caché."""
        mem = await flash_memory.store(
            content="Cache integration test",
            type="preference",
        )
        await memory_cache.set(mem)
        cached = await memory_cache.get(mem.id)
        assert cached is not None
        assert cached.content == mem.content

    @pytest.mark.asyncio
    async def test_cache_miss(self, memory_cache):
        """Cache miss retorna None."""
        result = await memory_cache.get("nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_invalidation(self, memory_cache, flash_memory):
        """Invalidar memoria del caché."""
        mem = await flash_memory.store(
            content="Invalidation test",
            type="fact",
        )
        await memory_cache.set(mem)
        assert await memory_cache.get(mem.id) is not None
        await memory_cache.invalidate(mem.id)
        assert await memory_cache.get(mem.id) is None

    @pytest.mark.asyncio
    async def test_cache_health(self, memory_cache):
        assert await memory_cache.health_check() is True


# ============================================
# TEST 3: Embeddings
# ============================================

class TestEmbeddingsIntegration:
    """Tests de embeddings."""

    def test_generate_embedding(self, embedding_service):
        """Generar embedding de 384 dimensiones."""
        emb = embedding_service.generate("Test de embeddings")
        assert len(emb) == 384
        assert all(isinstance(x, float) for x in emb)

    def test_similar_texts(self, embedding_service):
        """Textos similares tienen alta similitud."""
        emb1 = embedding_service.generate("Me gusta programar en Python")
        emb2 = embedding_service.generate("Disfruto codear con Python")
        sim = embedding_service.similarity(emb1, emb2)
        assert sim > 0.5

    def test_different_texts(self, embedding_service):
        """Textos diferentes tienen baja similitud."""
        emb1 = embedding_service.generate("Programación en Python")
        emb2 = embedding_service.generate("Receta de pastel de chocolate")
        sim = embedding_service.similarity(emb1, emb2)
        assert sim < 0.5

    def test_batch_generation(self, embedding_service):
        """Generación en batch funciona."""
        results = embedding_service.generate_batch(
            ["Hola", "Mundo", "Python"]
        )
        assert len(results) == 3
        assert all(len(r) == 384 for r in results)


# ============================================
# TEST 4: Conversaciones
# ============================================

class TestConversationIntegration:
    """Tests de conversaciones."""

    @pytest.mark.asyncio
    async def test_full_conversation_flow(self, conversation_manager):
        """Flujo completo de conversación."""
        conv_id = await conversation_manager.create_conversation(
            title="Integration test"
        )
        assert len(conv_id) == 36  # UUID

        await conversation_manager.add_message(
            conv_id, "user", "Hola YeyoOS"
        )
        await conversation_manager.add_message(
            conv_id, "assistant", "¡Hola! ¿En qué puedo ayudarte?"
        )

        history = await conversation_manager.get_history(conv_id)
        assert len(history) == 2
        assert history[0].role == "user"
        assert history[1].role == "assistant"

    @pytest.mark.asyncio
    async def test_list_conversations(self, conversation_manager):
        """Listar conversaciones funciona."""
        convos = await conversation_manager.list_conversations()
        assert isinstance(convos, list)
        assert len(convos) > 0


# ============================================
# TEST 5: Token Budget
# ============================================

class TestTokenBudgetIntegration:
    """Tests de token budget."""

    def test_total_is_4000(self):
        from src.chat.token_budget import TokenBudget
        assert TokenBudget.TOTAL == 4000

    def test_components_sum(self):
        from src.chat.token_budget import TokenBudget
        total = (
            TokenBudget.SYSTEM + TokenBudget.MEMORIES
            + TokenBudget.HISTORY + TokenBudget.INPUT
            + TokenBudget.RESPONSE
        )
        assert total == 4000

    def test_fit_memories(self):
        from src.chat.token_budget import TokenBudget
        from src.memory.models import Memory
        memories = [
            Memory(content="x" * 2000, type="fact", checksum="a" * 64),
            Memory(content="x" * 2000, type="fact", checksum="b" * 64),
        ]
        fitted = TokenBudget.fit_memories(memories, 1000)
        assert len(fitted) < 2


# ============================================
# TEST 6: System Prompt
# ============================================

class TestSystemPromptIntegration:
    """Tests de system prompt."""

    @pytest.mark.asyncio
    async def test_base_prompt(self):
        from src.chat.system_prompt import SystemPromptBuilder
        builder = SystemPromptBuilder()
        prompt = await builder.build()
        assert "YeyoOS" in prompt

    @pytest.mark.asyncio
    async def test_prompt_fits_budget(self):
        from src.chat.system_prompt import SystemPromptBuilder
        from src.chat.token_budget import TokenBudget
        builder = SystemPromptBuilder()
        prompt = await builder.build()
        assert TokenBudget.count_tokens(prompt) <= 300


# ============================================
# TEST 7: Background Task Manager
# ============================================

class TestBackgroundTasksIntegration:
    """Tests de tareas de fondo."""

    @pytest.mark.asyncio
    async def test_start_stop(self):
        from src.core.background import BackgroundTaskManager
        tm = BackgroundTaskManager()
        await tm.start()
        assert tm.is_running is True
        await tm.stop()
        assert tm.is_running is False


# ============================================
# TEST 8: Verificaciones de Regresión
# ============================================

class TestRegressionCapa1:
    """Verificar que Capa 1 sigue funcionando."""

    def test_ia_interfaces_importable(self):
        from src.ia.interfaces import IAProvider, IAMessage, IAResponse
        assert IAProvider is not None
        assert IAMessage is not None
        assert IAResponse is not None

    def test_ia_message_validation(self):
        from src.ia.interfaces import IAMessage
        msg = IAMessage(role="user", content="Test regresión")
        assert msg.role == "user"

    def test_ia_response_validation(self):
        from src.ia.interfaces import IAResponse
        resp = IAResponse(
            content="OK", model="test",
            tokens_used=5, latency_ms=10.0
        )
        assert resp.content == "OK"

    def test_ia_provider_is_abstract(self):
        from src.ia.interfaces import IAProvider
        with pytest.raises(TypeError):
            IAProvider()


# ============================================
# TEST 9: Verificaciones Críticas
# ============================================

class TestCriticalRules:
    """Verificar reglas fundamentales de YeyoOS."""

    def test_no_delete_method_on_flash_memory(self, flash_memory):
        """FlashMemory NO tiene método delete."""
        assert not hasattr(flash_memory, "delete")
        assert not hasattr(flash_memory, "remove")
        assert not hasattr(flash_memory, "destroy")

    def test_token_budget_is_4000(self):
        """El budget TOTAL debe ser 4000."""
        from src.chat.token_budget import TokenBudget
        assert TokenBudget.TOTAL == 4000

    def test_embedding_dimension_is_384(self, embedding_service):
        """Embeddings deben ser de 384 dimensiones."""
        assert embedding_service.get_dimension() == 384

    def test_embeddings_on_cpu(self):
        """Embeddings deben correr en CPU."""
        import os
        assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
