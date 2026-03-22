"""
YeyoOS — API Principal (FastAPI)
Backend conectado: PostgreSQL + Redis + Ollama (qwen2.5-coder:7b)

Servicios activos:
- Chat con contexto de memoria (ContextualChatService)
- Flash Memory persistente (PostgreSQL)
- Conversaciones y feedback (PostgreSQL)
- Paquetes .ypkg (PackageInstaller)
- Health check real de todos los subsistemas
- WebSocket para comunicación en tiempo real
- TTS local
"""

import time
import logging
from contextlib import asynccontextmanager

import asyncpg

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.core.config import get_config
from src.ia.ollama_provider import OllamaProvider
from src.ia.ollama_embeddings import OllamaEmbeddingService
from src.memory.flash_memory import FlashMemory
from src.chat.conversation import ConversationManager
from src.chat.feedback import FeedbackService
from src.api.websocket import manager
from src.api.tts import router as tts_router
from src.api.routes.chat import router as chat_router
from src.api.routes.memory import router as memory_router
from src.api.routes.packages import router as packages_router, init_package_services

logger = logging.getLogger("yeyoos.api")

_start_time: float = 0.0

# Servicios globales (inicializados en lifespan)
_ia_provider: OllamaProvider | None = None
_flash_memory: FlashMemory | None = None
_conv_manager: ConversationManager | None = None
_feedback_service: FeedbackService | None = None
_chat_service = None  # ChatService o ContextualChatService
_embedding_service: OllamaEmbeddingService | None = None
_association_engine = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: conectar todos los servicios. Shutdown: cerrar conexiones."""
    global _start_time, _ia_provider, _flash_memory, _conv_manager
    global _feedback_service, _chat_service, _embedding_service, _association_engine

    _start_time = time.time()
    config = get_config()

    logger.info("🚀 YeyoOS Backend iniciando...")

    # 1. OllamaProvider (IA)
    _ia_provider = OllamaProvider(
        host=config.ollama_host,
        model=config.ollama_model,
        embedding_model=config.ollama_embedding_model,
        timeout=config.ollama_timeout,
    )
    ollama_ok = await _ia_provider.health_check()
    logger.info(f"  Ollama ({config.ollama_model}): {'✅' if ollama_ok else '❌'}")

    # 2. PostgreSQL (Flash Memory + Conversations + Feedback)
    try:
        pool = await asyncpg.create_pool(
            config.database_url,
            min_size=2,
            max_size=10,
        )
        _flash_memory = FlashMemory(pool)
        _conv_manager = ConversationManager(pool)
        _feedback_service = FeedbackService(pool, _flash_memory)
        pg_ok = await _flash_memory.health_check()
        logger.info(f"  PostgreSQL: {'✅' if pg_ok else '❌'}")
    except Exception as e:
        logger.error(f"  PostgreSQL: ❌ ({e})")
        pool = None

    # 3. Embeddings via Ollama
    _embedding_service = OllamaEmbeddingService(
        host=config.ollama_host,
        model=config.ollama_embedding_model,
        timeout=30.0,
    )

    # 4. AssociationEngine (import lazy por dependencias pesadas)
    try:
        from src.memory.associations import AssociationEngine
        if _flash_memory and _embedding_service:
            _association_engine = AssociationEngine(_flash_memory, _embedding_service)
    except ImportError:
        logger.warning("  AssociationEngine no disponible (falta sentence-transformers)")

    # 5. Chat contextual (con memoria)
    try:
        from src.chat.contextual_service import ContextualChatService
        if _flash_memory and _embedding_service:
            _chat_service = ContextualChatService(
                ia=_ia_provider,
                memory=_flash_memory,
                embeddings=_embedding_service,
            )
        else:
            from src.chat.service import ChatService
            _chat_service = ChatService(_ia_provider)
    except ImportError:
        from src.chat.service import ChatService
        _chat_service = ChatService(_ia_provider)

    # 6. Paquetes
    init_package_services()

    # Inyectar dependencias en los routers
    _wire_dependencies()

    logger.info("🟢 YeyoOS Backend listo")

    yield

    # Shutdown
    logger.info("🔴 YeyoOS Backend cerrando...")
    if _ia_provider:
        await _ia_provider.close()
    if pool:
        await pool.close()
    logger.info("👋 YeyoOS Backend cerrado")


def _wire_dependencies():
    """Inyecta los servicios reales en los routers via FastAPI dependency_overrides."""
    from src.api.routes.chat import get_chat_service, get_conversation_manager, get_feedback_service
    from src.api.routes.memory import get_flash_memory, get_embedding_service, get_association_engine

    # Chat dependencies
    async def _real_chat_service():
        return _chat_service

    async def _real_conversation_manager():
        return _conv_manager

    async def _real_feedback_service():
        return _feedback_service

    app.dependency_overrides[get_chat_service] = _real_chat_service
    app.dependency_overrides[get_conversation_manager] = _real_conversation_manager
    app.dependency_overrides[get_feedback_service] = _real_feedback_service

    # Memory dependencies
    async def _real_flash_memory():
        return _flash_memory

    async def _real_embedding_service():
        return _embedding_service

    async def _real_association_engine():
        return _association_engine

    app.dependency_overrides[get_flash_memory] = _real_flash_memory
    app.dependency_overrides[get_embedding_service] = _real_embedding_service
    app.dependency_overrides[get_association_engine] = _real_association_engine


app = FastAPI(
    title="YeyoOS API",
    description="API REST para YeyoOS — OS AI-nativo",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — solo frontend local en desarrollo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


# ========== Health & Status ==========

@app.get("/health")
async def health():
    """Health check básico."""
    uptime = time.time() - _start_time if _start_time else 0
    return JSONResponse(content={
        "status": "healthy",
        "version": "0.1.0",
        "uptime_seconds": round(uptime, 2),
    })


@app.get("/api/v1/status")
async def status():
    """Status detallado con verificación real de servicios."""
    uptime = time.time() - _start_time if _start_time else 0

    services = {"api": "up"}

    # PostgreSQL
    if _flash_memory:
        try:
            pg_ok = await _flash_memory.health_check()
            services["postgresql"] = "up" if pg_ok else "down"
        except Exception:
            services["postgresql"] = "down"
    else:
        services["postgresql"] = "not_configured"

    # Ollama
    if _ia_provider:
        try:
            ollama_ok = await _ia_provider.health_check()
            services["ollama"] = "up" if ollama_ok else "down"
            if ollama_ok:
                services["ollama_model"] = _ia_provider.get_model_name()
        except Exception:
            services["ollama"] = "down"
    else:
        services["ollama"] = "not_configured"

    # Redis
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url("redis://localhost:6379")
        pong = await r.ping()
        services["redis"] = "up" if pong else "down"
        await r.close()
    except Exception:
        services["redis"] = "down"

    down_count = sum(1 for v in services.values() if v == "down")
    overall = "healthy" if down_count == 0 else ("degraded" if down_count == 1 else "unhealthy")

    return JSONResponse(content={
        "status": overall,
        "version": "0.1.0",
        "uptime_seconds": round(uptime, 2),
        "services": services,
    })


# ========== Registrar routers ==========

app.include_router(tts_router)
app.include_router(chat_router)
app.include_router(memory_router)
app.include_router(packages_router)


# ========== WebSocket ==========

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Endpoint WebSocket principal — conectado con chat service."""
    connected = await manager.connect(websocket)
    if not connected:
        return
    try:
        while True:
            data = await websocket.receive_text()
            if _chat_service:
                try:
                    response = await _chat_service.send_message(user_input=data)
                    await manager.send_json(
                        {"type": "chat", "content": response, "timestamp": time.time()},
                        websocket,
                    )
                except Exception as e:
                    await manager.send_json(
                        {"type": "error", "content": str(e), "timestamp": time.time()},
                        websocket,
                    )
            else:
                await manager.send_json(
                    {"type": "echo", "content": data, "timestamp": time.time()},
                    websocket,
                )
    except WebSocketDisconnect:
        manager.disconnect(websocket)

