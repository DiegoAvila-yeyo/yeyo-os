"""
YeyoOS — Arena Battle System API
Phase 8 — YeyoHack vs Guardian battle endpoints
"""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.arena.battle import BattleEngine, BattleSession

logger = logging.getLogger("yeyoos.api.arena")

router = APIRouter(prefix="/api/v1/arena", tags=["arena"])

# ========== IA Provider & WS Manager (injected from main.py) ==========

_ia_provider = None
_ws_manager = None
_engine: Optional[BattleEngine] = None


def set_ia_provider(provider):
    global _ia_provider, _engine
    _ia_provider = provider
    _engine = BattleEngine(ia_provider=_ia_provider, ws_manager=_ws_manager)


def set_ws_manager(ws):
    global _ws_manager, _engine
    _ws_manager = ws
    _engine = BattleEngine(ia_provider=_ia_provider, ws_manager=_ws_manager)


def _get_engine() -> BattleEngine:
    global _engine
    if _engine is None:
        _engine = BattleEngine(ia_provider=_ia_provider, ws_manager=_ws_manager)
    return _engine


# ========== Request / Response Models ==========

class StartBattleRequest(BaseModel):
    max_rounds: int = Field(default=15, ge=1, le=100)


class SessionResponse(BaseModel):
    session_id: str
    status: str
    max_rounds: int
    current_round: int
    red_score: int
    blue_score: int


class RoundResponse(BaseModel):
    round_number: int
    attack_type: str
    attack_code: str
    defense_code: str
    attack_success: bool
    defense_success: bool
    severity: int
    red_score: int
    blue_score: int
    description: str


class SessionDetailResponse(BaseModel):
    session_id: str
    status: str
    max_rounds: int
    current_round: int
    red_score: int
    blue_score: int
    rounds: list[RoundResponse]
    learned_combos: list[str]


class ScriptEntry(BaseModel):
    round_number: int
    attack_type: str
    attack_code: str
    defense_code: str
    attack_success: bool


# ========== Endpoints ==========

@router.post("/start", response_model=SessionResponse)
async def start_battle(req: StartBattleRequest):
    """Start a new Arena battle."""
    engine = _get_engine()
    session_id = f"arena-{uuid.uuid4().hex[:8]}"
    engine.create_session(session_id, max_rounds=req.max_rounds)
    await engine.start(session_id)
    session = engine.sessions[session_id]
    logger.info(f"⚔️ Arena battle started: {session_id} ({req.max_rounds} rounds)")
    return SessionResponse(
        session_id=session.id,
        status=session.status,
        max_rounds=session.max_rounds,
        current_round=session.current_round,
        red_score=session.red_score,
        blue_score=session.blue_score,
    )


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions():
    """List all arena sessions."""
    engine = _get_engine()
    return [
        SessionResponse(
            session_id=s.id,
            status=s.status,
            max_rounds=s.max_rounds,
            current_round=s.current_round,
            red_score=s.red_score,
            blue_score=s.blue_score,
        )
        for s in engine.sessions.values()
    ]


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session(session_id: str):
    """Get battle session details with all rounds."""
    engine = _get_engine()
    session = engine.sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionDetailResponse(
        session_id=session.id,
        status=session.status,
        max_rounds=session.max_rounds,
        current_round=session.current_round,
        red_score=session.red_score,
        blue_score=session.blue_score,
        rounds=[
            RoundResponse(
                round_number=r.round_number,
                attack_type=r.attack_type,
                attack_code=r.attack_code,
                defense_code=r.defense_code,
                attack_success=r.attack_success,
                defense_success=r.defense_success,
                severity=r.severity,
                red_score=r.red_score,
                blue_score=r.blue_score,
                description=r.description,
            )
            for r in session.rounds
        ],
        learned_combos=session.learned_combos,
    )


@router.post("/sessions/{session_id}/pause", response_model=SessionResponse)
async def pause_battle(session_id: str):
    """Pause an active battle."""
    engine = _get_engine()
    session = engine.sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    engine.pause(session_id)
    return SessionResponse(
        session_id=session.id,
        status=session.status,
        max_rounds=session.max_rounds,
        current_round=session.current_round,
        red_score=session.red_score,
        blue_score=session.blue_score,
    )


@router.post("/sessions/{session_id}/resume", response_model=SessionResponse)
async def resume_battle(session_id: str):
    """Resume a paused battle."""
    engine = _get_engine()
    session = engine.sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != 'paused':
        raise HTTPException(status_code=400, detail="Session is not paused")
    await engine.resume(session_id)
    return SessionResponse(
        session_id=session.id,
        status=session.status,
        max_rounds=session.max_rounds,
        current_round=session.current_round,
        red_score=session.red_score,
        blue_score=session.blue_score,
    )


@router.post("/sessions/{session_id}/stop", response_model=SessionResponse)
async def stop_battle(session_id: str):
    """Stop a battle."""
    engine = _get_engine()
    session = engine.sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    engine.stop(session_id)
    return SessionResponse(
        session_id=session.id,
        status=session.status,
        max_rounds=session.max_rounds,
        current_round=session.current_round,
        red_score=session.red_score,
        blue_score=session.blue_score,
    )


@router.get("/sessions/{session_id}/scripts", response_model=list[ScriptEntry])
async def get_scripts(session_id: str):
    """Get all attack/defense scripts from a battle session."""
    engine = _get_engine()
    session = engine.sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return [
        ScriptEntry(
            round_number=r.round_number,
            attack_type=r.attack_type,
            attack_code=r.attack_code,
            defense_code=r.defense_code,
            attack_success=r.attack_success,
        )
        for r in session.rounds
    ]
