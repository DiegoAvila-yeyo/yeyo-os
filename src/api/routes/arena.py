"""
YeyoOS — Arena API Routes
FastAPI router for the YeyoHack Arena battle system.
"""
import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from src.arena.service import ArenaService, get_arena_service

logger = logging.getLogger("yeyoos.api.arena")

router = APIRouter(prefix="/api/v1/arena", tags=["arena"])

_DB_PATH = Path(__file__).resolve().parent.parent.parent / "arena" / "attack_db.json"


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class StartBattleRequest(BaseModel):
    """Body for POST /start."""
    max_rounds: int = Field(default=100, ge=1, le=10_000, description="Maximum rounds to play.")


class BattleResponse(BaseModel):
    """Generic arena response wrapper."""
    ok: bool
    data: dict[str, Any] = {}
    message: str = ""


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------

@router.post("/start", response_model=BattleResponse)
async def start_battle(
    body: StartBattleRequest = StartBattleRequest(),
    service: ArenaService = Depends(get_arena_service),
) -> BattleResponse:
    """Start a new Red vs Blue battle session."""
    try:
        session_data = await service.start_battle(max_rounds=body.max_rounds)
        return BattleResponse(ok=True, data=session_data, message="Battle started.")
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to start battle: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal error starting battle.")


@router.post("/stop", response_model=BattleResponse)
async def stop_battle(
    service: ArenaService = Depends(get_arena_service),
) -> BattleResponse:
    """Stop the running battle session."""
    try:
        status = await service.stop_battle()
        return BattleResponse(ok=True, data=status, message="Battle stopped.")
    except Exception as exc:
        logger.error("Failed to stop battle: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal error stopping battle.")


@router.get("/status", response_model=BattleResponse)
async def get_status(
    service: ArenaService = Depends(get_arena_service),
) -> BattleResponse:
    """Return current battle session status."""
    return BattleResponse(ok=True, data=service.get_status())


@router.get("/metrics", response_model=BattleResponse)
async def get_metrics(
    service: ArenaService = Depends(get_arena_service),
) -> BattleResponse:
    """Return battle metrics (current session + aggregate)."""
    return BattleResponse(ok=True, data=service.get_metrics())


@router.get("/history")
async def get_history(
    service: ArenaService = Depends(get_arena_service),
) -> list[dict[str, Any]]:
    """Return round-by-round history of the current session."""
    return service.get_history()


@router.get("/scripts", response_model=BattleResponse)
async def get_scripts() -> BattleResponse:
    """Return all stored attack and defense scripts from the persistent DB."""
    try:
        with open(_DB_PATH, "r") as f:
            db = json.load(f)
        return BattleResponse(ok=True, data=db, message="Scripts loaded.")
    except FileNotFoundError:
        return BattleResponse(ok=True, data={"attacks": [], "defenses": []}, message="No scripts yet.")
    except json.JSONDecodeError:
        return BattleResponse(ok=False, data={}, message="Corrupt scripts database.")


# ---------------------------------------------------------------------------
# WebSocket — live battle stream
# ---------------------------------------------------------------------------

@router.websocket("/live")
async def arena_live(
    ws: WebSocket,
    service: ArenaService = Depends(get_arena_service),
) -> None:
    """WebSocket endpoint for real-time battle event streaming."""
    await ws.accept()
    service.add_ws(ws)
    logger.info("Arena live WebSocket connected.")
    try:
        # Keep the connection open; the client can send pings or control msgs
        while True:
            data = await ws.receive_text()
            # Echo back for health-check / keepalive
            if data == "ping":
                await ws.send_text("pong")
    except WebSocketDisconnect:
        logger.info("Arena live WebSocket disconnected.")
    except Exception as exc:
        logger.warning("WebSocket error: %s", exc)
    finally:
        service.remove_ws(ws)
