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

import json
import os
import time
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

import asyncpg

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.core.config import get_config
from src.ia.ollama_provider import OllamaProvider
from src.ia.ollama_embeddings import OllamaEmbeddingService
from src.memory.flash_memory import FlashMemory
from src.memory.cache import MemoryCache
from src.memory.tier_manager import TierManager
from src.core.background import BackgroundTaskManager
from src.chat.conversation import ConversationManager
from src.chat.feedback import FeedbackService
from src.api.websocket import manager
from src.api.tts import router as tts_router
from src.api.routes.chat import router as chat_router
from src.api.routes.memory import router as memory_router
from src.api.routes.packages import router as packages_router, init_package_services
from src.api.routes.media import router as media_router
from src.api.routes.nodes import router as nodes_router
from src.api.routes.code import router as code_router, set_ia_provider as set_code_ia, set_code_ia_provider, set_memory_service as set_code_memory
from src.api.routes.video import router as video_router, get_ia_provider as video_get_ia, get_flash_memory as video_get_memory, set_video_memory_service
from src.api.routes.yeyonet import router as yeyonet_router, get_invite_manager as yeyonet_get_invite, get_satellite_manager as yeyonet_get_sat, get_node_identity as yeyonet_get_identity, get_job_orchestrator as yeyonet_get_orchestrator, get_sync_manager as yeyonet_get_sync
from src.api.routes.cloud_sync import router as cloud_sync_router, get_cloud_sync as cloud_sync_get

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
_memory_cache: MemoryCache | None = None
_tier_manager: TierManager | None = None
_background_manager: BackgroundTaskManager | None = None
_node_identity = None  # YeyoNet NodeIdentity
_invite_manager = None  # YeyoNet InviteManager
_satellite_manager = None  # YeyoNet SatelliteManager
_yeyonet_relay = None  # YeyoNet Relay Server
_job_orchestrator = None  # YeyoNet JobOrchestrator
_sync_manager = None  # YeyoNet SyncManager
_cloud_sync = None  # Cloud Memory Sync (Supabase)


def _get_fallback_node_id() -> str:
    """Generate a deterministic node_id from hostname when YeyoNet isn't available."""
    import hashlib
    import socket
    hostname = socket.gethostname()
    return hashlib.sha256(hostname.encode()).hexdigest()[:32]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: conectar todos los servicios. Shutdown: cerrar conexiones."""
    global _start_time, _ia_provider, _flash_memory, _conv_manager
    global _feedback_service, _chat_service, _embedding_service, _association_engine
    global _memory_cache, _tier_manager, _background_manager
    global _node_identity, _invite_manager, _satellite_manager
    global _yeyonet_relay
    global _job_orchestrator
    global _sync_manager
    global _cloud_sync

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

    # 4b. MemoryCache (Redis HOT tier)
    try:
        _memory_cache = MemoryCache()
        await _memory_cache.connect()
        cache_ok = await _memory_cache.health_check()
        logger.info(f"  Redis MemoryCache: {'✅' if cache_ok else '❌ (modo degradado)'}")
        # Conectar cache a FlashMemory — activa la capa HOT
        if cache_ok and _flash_memory:
            _flash_memory.set_cache(_memory_cache)
            logger.info("  FlashMemory → Redis HOT cache: ✅ conectado")
    except Exception as e:
        logger.warning(f"  Redis MemoryCache: ❌ ({e}) — sin cache HOT")
        _memory_cache = None

    # 4c. TierManager
    if _flash_memory and _memory_cache:
        _tier_manager = TierManager(_flash_memory, _memory_cache)
        logger.info("  TierManager: ✅")

    # 4d. BackgroundTaskManager
    _background_manager = BackgroundTaskManager(
        tier_manager=_tier_manager,
        cache=_memory_cache,
        flash_memory=_flash_memory,
        embeddings=_embedding_service,
    )
    await _background_manager.start()
    logger.info(f"  BackgroundTaskManager: ✅ ({_background_manager.task_count} tareas)")

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

    # 7. YeyoNet — Red distribuida
    try:
        from src.yeyonet.identity import NodeIdentity
        from src.yeyonet.invite_manager import InviteManager
        from src.yeyonet.satellite_manager import SatelliteManager

        if pool:
            _node_identity = NodeIdentity(pool)
            await _node_identity.initialize(name="Central")
            _invite_manager = InviteManager(pool)
            _satellite_manager = SatelliteManager(pool)

            # Iniciar Relay Server
            from src.yeyonet.relay import YeyoNetRelay
            _yeyonet_relay = YeyoNetRelay(_satellite_manager, _node_identity.node_id)
            await _yeyonet_relay.start()

            # Iniciar Job Orchestrator
            from src.yeyonet.job_orchestrator import JobOrchestrator
            _job_orchestrator = JobOrchestrator(pool, _yeyonet_relay)
            await _job_orchestrator.start()

            # Wire relay handlers for job messages
            from src.yeyonet.protocol import MessageType as MT
            _yeyonet_relay.on_message(MT.JOB_PROGRESS, _job_orchestrator.handle_job_progress)
            _yeyonet_relay.on_message(MT.JOB_RESULT, _job_orchestrator.handle_job_result)

            # Iniciar SyncManager
            from src.yeyonet.sync_manager import SyncManager
            _sync_manager = SyncManager(pool, _yeyonet_relay)
            await _sync_manager.start()
            _yeyonet_relay.on_message(MT.MEMORY_SYNC, _sync_manager.handle_memory_sync)

            logger.info(f"  🌐 YeyoNet: ✅ (node={_node_identity.node_id[:8]}..., relay+jobs+sync=on)")
    except Exception as e:
        logger.warning(f"  🌐 YeyoNet: ❌ ({e})")

    # 8. Cloud Memory Sync (Supabase) — optional
    import os
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_KEY", "")
    if supabase_url and supabase_key and pool:
        try:
            from src.memory.cloud_sync import CloudSyncService
            node_id = _node_identity.node_id if _node_identity else _get_fallback_node_id()
            _cloud_sync = CloudSyncService(pool, supabase_url, supabase_key, node_id)
            await _cloud_sync.start()
            # Hook: push cada memoria nueva al cloud automáticamente
            if _flash_memory:
                _flash_memory.on_store(_cloud_sync.push_single)
            logger.info("  ☁️  Cloud Sync (Supabase): ✅")
        except Exception as e:
            logger.warning(f"  ☁️  Cloud Sync: ❌ ({e})")
    else:
        logger.info("  ☁️  Cloud Sync: ⏭ (SUPABASE_URL/KEY not set)")

    # Inyectar dependencias en los routers
    _wire_dependencies()

    set_code_ia(_ia_provider)
    # Crear proveedor especializado para código (qwen2.5-coder:7b)
    try:
        _config = get_config()
        if _config.ollama_code_model and _config.ollama_code_model != _config.ollama_model:
            code_ia = OllamaProvider(model=_config.ollama_code_model)
            set_code_ia_provider(code_ia)
            logger.info(f"🔧 Modelo de código: {_config.ollama_code_model}")
    except Exception as e:
        logger.warning(f"No se pudo cargar modelo de código: {e}")
    logger.info("🟢 YeyoOS Backend listo")

    yield

    # Shutdown
    logger.info("🔴 YeyoOS Backend cerrando...")
    if _cloud_sync:
        await _cloud_sync.stop()
    if _yeyonet_relay:
        await _yeyonet_relay.stop()
    if _job_orchestrator:
        await _job_orchestrator.stop()
    if _sync_manager:
        await _sync_manager.stop()
    if _background_manager:
        await _background_manager.stop()
    if _memory_cache:
        await _memory_cache.disconnect()
    if _ia_provider:
        await _ia_provider.close()
    if pool:
        await pool.close()
    logger.info("👋 YeyoOS Backend cerrado")


def _wire_dependencies():
    """Inyecta los servicios reales en los routers via FastAPI dependency_overrides."""
    from src.api.routes.chat import get_chat_service, get_conversation_manager, get_feedback_service
    from src.api.routes.memory import get_flash_memory, get_embedding_service, get_association_engine, get_memory_cache
    from src.api.routes.nodes import get_node_memory_service

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

    async def _real_memory_cache():
        return _memory_cache

    app.dependency_overrides[get_memory_cache] = _real_memory_cache

    # Node memory service
    if _flash_memory and _embedding_service:
        from src.memory.node_memory import NodeMemoryService
        _node_memory = NodeMemoryService(_flash_memory, _embedding_service)

        async def _real_node_memory_service():
            return _node_memory

        app.dependency_overrides[get_node_memory_service] = _real_node_memory_service

        # Wire memory service to Code Dojo
        set_code_memory(_node_memory)

        # Wire memory service to Video Ingest
        set_video_memory_service(_node_memory)

    # Video dependencies
    async def _real_video_ia():
        return _ia_provider

    async def _real_video_memory():
        return _flash_memory

    app.dependency_overrides[video_get_ia] = _real_video_ia
    app.dependency_overrides[video_get_memory] = _real_video_memory

    # YeyoNet dependencies
    if _node_identity and _invite_manager and _satellite_manager:
        async def _real_invite_manager():
            return _invite_manager

        async def _real_satellite_manager():
            return _satellite_manager

        async def _real_node_identity():
            return _node_identity

        app.dependency_overrides[yeyonet_get_invite] = _real_invite_manager
        app.dependency_overrides[yeyonet_get_sat] = _real_satellite_manager
        app.dependency_overrides[yeyonet_get_identity] = _real_node_identity

    if _job_orchestrator:
        async def _real_job_orchestrator():
            return _job_orchestrator

        app.dependency_overrides[yeyonet_get_orchestrator] = _real_job_orchestrator

    if _sync_manager:
        async def _real_sync_manager():
            return _sync_manager

        app.dependency_overrides[yeyonet_get_sync] = _real_sync_manager

    # Cloud sync dependency (return None if not configured — routes handle gracefully)
    async def _real_cloud_sync():
        return _cloud_sync

    app.dependency_overrides[cloud_sync_get] = _real_cloud_sync


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
    expose_headers=["X-Conversation-Id"],
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
        await r.aclose()
    except Exception:
        services["redis"] = "down"

    down_count = sum(1 for v in services.values() if v == "down")

    # GPU
    try:
        import subprocess as _sp
        result = _sp.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5,
        )
        services["gpu"] = "up" if result.returncode == 0 else "down"
    except Exception:
        services["gpu"] = "unavailable"

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
app.include_router(media_router)
app.include_router(nodes_router)
app.include_router(code_router)
app.include_router(video_router)
app.include_router(yeyonet_router)
app.include_router(cloud_sync_router)


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


# ─── WebSocket Pipeline — tiempo real ─────────────────────────────────────────

_pipeline_ws_clients: list[WebSocket] = []


def _on_pipeline_event(event):
    """Callback del PipelineBuffer — encola broadcast a todos los clientes WS."""
    import asyncio
    data = json.dumps({"type": "pipeline:event", "event": event.to_dict()})
    disconnected = []
    for ws in _pipeline_ws_clients:
        try:
            asyncio.ensure_future(ws.send_text(data))
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        _pipeline_ws_clients.remove(ws)


# Register listener on startup
from src.memory.pipeline_events import pipeline_buffer as _pb
_pb.add_listener(_on_pipeline_event)


@app.websocket("/ws/pipeline")
async def ws_pipeline(websocket: WebSocket):
    """WebSocket para recibir eventos de pipeline en tiempo real."""
    await websocket.accept()
    _pipeline_ws_clients.append(websocket)
    try:
        # Send current state on connect
        from src.memory.pipeline_events import pipeline_buffer, PIPELINE_DEFS
        await websocket.send_text(json.dumps({
            "type": "pipeline:init",
            "pipelines": pipeline_buffer.get_pipelines(15),
            "step_stats": pipeline_buffer.get_step_stats(),
            "pipeline_defs": PIPELINE_DEFS,
        }))
        # Keep alive — wait for client pings or disconnect
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in _pipeline_ws_clients:
            _pipeline_ws_clients.remove(websocket)


@app.websocket("/ws/yeyonet")
async def ws_yeyonet(websocket: WebSocket):
    """WebSocket para la red YeyoNet — satélites se conectan aquí."""
    if _yeyonet_relay:
        await _yeyonet_relay.handle_connection(websocket)
    else:
        await websocket.accept()
        await websocket.close(code=1013, reason="YeyoNet relay not initialized")
