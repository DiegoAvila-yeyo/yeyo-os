"""
YeyoOS — API Base (FastAPI)
Micro-fase 1.6 — Capa 1: Esqueleto

Skeleton de la API REST.
Endpoints: /health, /api/v1/status
CORS configurado para frontend Next.js en localhost:3000.
"""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse


_start_time: float = 0.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle de la aplicación: startup y shutdown."""
    global _start_time
    _start_time = time.time()
    yield


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


@app.get("/health")
async def health():
    """Health check básico de la API. Retorna status y uptime."""
    uptime = time.time() - _start_time if _start_time else 0
    return JSONResponse(
        content={
            "status": "healthy",
            "version": "0.1.0",
            "uptime_seconds": round(uptime, 2),
        }
    )


@app.get("/api/v1/status")
async def status():
    """
    Status detallado del sistema.
    En Capa 2 se conectará con HealthChecker real.
    """
    uptime = time.time() - _start_time if _start_time else 0
    return JSONResponse(
        content={
            "status": "operational",
            "version": "0.1.0",
            "uptime_seconds": round(uptime, 2),
            "services": {
                "api": "up",
                "postgresql": "pending",
                "redis": "pending",
                "ollama": "pending",
                "gpu": "pending",
            },
        }
    )


from src.api.websocket import manager


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Endpoint WebSocket principal."""
    connected = await manager.connect(websocket)
    if not connected:
        return
    try:
        while True:
            data = await websocket.receive_text()
            # Echo por ahora, en Capa 2 se conectará con Orquestador
            await manager.send_json(
                {"type": "echo", "content": data, "timestamp": time.time()},
                websocket,
            )
    except WebSocketDisconnect:
        manager.disconnect(websocket)

