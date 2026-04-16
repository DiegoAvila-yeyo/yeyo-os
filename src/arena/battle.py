"""
YeyoOS — Arena Battle Manager
Orchestrates rounds between YeyoHack (Red) and Guardian (Blue).
"""
import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from src.arena.guardian import Guardian
from src.arena.sandbox import ArenaSandbox
from src.arena.yeyohack import YeyoHack

logger = logging.getLogger("yeyoos.arena.battle")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class BattleRound:
    """Record of a single attack/defense round."""

    round_number: int
    attack_type: str
    attack_success: bool
    defense_success: bool
    attack_duration_ms: float
    defense_duration_ms: float
    details: str
    attack_code: str = ""
    defense_code: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "round_number": self.round_number,
            "attack_type": self.attack_type,
            "attack_success": self.attack_success,
            "defense_success": self.defense_success,
            "attack_duration_ms": round(self.attack_duration_ms, 2),
            "defense_duration_ms": round(self.defense_duration_ms, 2),
            "details": self.details,
            "attack_code": self.attack_code,
            "defense_code": self.defense_code,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class BattleSession:
    """State of an entire battle session."""

    id: str
    status: str = "idle"  # idle | running | paused | completed
    rounds: list[BattleRound] = field(default_factory=list)
    red_score: int = 0
    blue_score: int = 0
    max_rounds: int = 100
    current_round: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status,
            "red_score": self.red_score,
            "blue_score": self.blue_score,
            "max_rounds": self.max_rounds,
            "current_round": self.current_round,
            "total_rounds_played": len(self.rounds),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


# ---------------------------------------------------------------------------
# Battle Manager
# ---------------------------------------------------------------------------

class BattleManager:
    """Orchestrates Red vs Blue rounds inside sandboxed environments."""

    def __init__(self) -> None:
        self.yeyohack = YeyoHack()
        self.guardian = Guardian()
        self.current_session: Optional[BattleSession] = None
        self.event_callback: Optional[Callable[..., Any]] = None
        self._task: Optional[asyncio.Task[None]] = None

    # -- callbacks ---------------------------------------------------------

    def set_event_callback(self, callback: Callable[..., Any]) -> None:
        """Register a callback invoked on every battle event (e.g. WS broadcast)."""
        self.event_callback = callback

    async def _emit(self, event: str, data: dict[str, Any]) -> None:
        if self.event_callback:
            try:
                await self.event_callback({"event": event, **data})
            except Exception as exc:
                logger.warning("Event callback error: %s", exc)

    # -- session lifecycle -------------------------------------------------

    async def start_session(self, max_rounds: int = 100) -> BattleSession:
        """Create and start a new battle session."""
        if self.current_session and self.current_session.status == "running":
            raise RuntimeError("A session is already running — stop it first.")

        self.yeyohack = YeyoHack()
        self.guardian = Guardian()
        self.current_session = BattleSession(
            id=uuid.uuid4().hex[:12],
            status="running",
            max_rounds=max_rounds,
            started_at=datetime.now(timezone.utc),
        )
        logger.info("Battle session %s started (max_rounds=%d)", self.current_session.id, max_rounds)
        await self._emit("session_started", self.current_session.to_dict())

        self._task = asyncio.create_task(self._battle_loop())
        return self.current_session

    async def stop_session(self) -> None:
        """Stop the running session."""
        if self.current_session:
            self.current_session.status = "completed"
            self.current_session.completed_at = datetime.now(timezone.utc)
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self._emit("session_stopped", self.get_status())
        logger.info("Battle session stopped.")

    async def pause_session(self) -> None:
        """Pause the battle (rounds stop until resumed)."""
        if self.current_session and self.current_session.status == "running":
            self.current_session.status = "paused"
            await self._emit("session_paused", self.get_status())
            logger.info("Battle session paused.")

    async def resume_session(self) -> None:
        """Resume a paused session."""
        if self.current_session and self.current_session.status == "paused":
            self.current_session.status = "running"
            await self._emit("session_resumed", self.get_status())
            logger.info("Battle session resumed.")

    # -- battle loop -------------------------------------------------------

    async def _battle_loop(self) -> None:
        """Core loop — one round per iteration."""
        session = self.current_session
        if session is None:
            return

        try:
            while (
                session.current_round < session.max_rounds
                and session.status in ("running", "paused")
            ):
                # Respect pause
                while session.status == "paused":
                    await asyncio.sleep(0.5)
                if session.status not in ("running",):
                    break

                session.current_round += 1
                round_num = session.current_round

                async with ArenaSandbox(timeout=30) as sandbox:
                    # ---- Red Team attacks ----
                    attack_result = await self.yeyohack.execute(sandbox, round_number=round_num)
                    attack_success = attack_result.get("success", False)
                    attack_duration = attack_result.get("duration_ms", 0.0)
                    attack_type = attack_result.get("attack_type", "unknown")
                    payload = attack_result.get("details", "")
                    attack_code = attack_result.get("code", "")

                    # ---- Blue Team detects & defends ----
                    import time as _time

                    defense_start = _time.perf_counter()
                    detected, detected_type = await self.guardian.detect(payload)

                    defense_success = False
                    defense_code = ""
                    if detected and detected_type:
                        defense_code = await self.guardian.generate_defense(detected_type, payload)
                        defense_success = await self.guardian.validate_defense(
                            defense_code, payload, sandbox,
                            attack_type=detected_type,
                            round_number=round_num,
                        )
                    defense_duration = (_time.perf_counter() - defense_start) * 1000

                # ---- Scoring ----
                if attack_success and not detected:
                    session.red_score += 1
                if detected or defense_success:
                    session.blue_score += 1

                details = (
                    f"attack={attack_type} "
                    f"hit={'yes' if attack_success else 'no'} "
                    f"detected={'yes' if detected else 'no'} "
                    f"defended={'yes' if defense_success else 'no'}"
                )
                battle_round = BattleRound(
                    round_number=round_num,
                    attack_type=attack_type,
                    attack_success=attack_success,
                    defense_success=defense_success,
                    attack_duration_ms=attack_duration,
                    defense_duration_ms=defense_duration,
                    details=details,
                    attack_code=attack_code,
                    defense_code=defense_code,
                )
                session.rounds.append(battle_round)

                await self._emit("round_completed", {
                    "round": battle_round.to_dict(),
                    "scores": {"red": session.red_score, "blue": session.blue_score},
                })

                # Auto-pause on critical attacks (severity >= 9 that succeeded)
                if attack_success and not defense_success:
                    from src.arena.attack_library import get_attack_by_severity
                    critical = [a for a in get_attack_by_severity(9) if a.attack_type.value == attack_type]
                    if critical:
                        logger.warning("CRITICAL attack succeeded — auto-pausing session.")
                        session.status = "paused"
                        await self._emit("auto_paused", {
                            "reason": f"Critical {attack_type} attack succeeded",
                            "round": round_num,
                        })

                # Evolve every 10 rounds
                if round_num % 10 == 0:
                    await self.yeyohack.evolve()

                # Brief delay between rounds
                await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            logger.info("Battle loop cancelled.")
        except Exception as exc:
            logger.error("Battle loop error: %s", exc, exc_info=True)
        finally:
            if session.status == "running":
                session.status = "completed"
                session.completed_at = datetime.now(timezone.utc)
            await self._emit("session_completed", self.get_status())
            logger.info(
                "Session %s finished — Red %d / Blue %d (%d rounds)",
                session.id,
                session.red_score,
                session.blue_score,
                len(session.rounds),
            )

    # -- queries -----------------------------------------------------------

    def get_status(self) -> dict[str, Any]:
        """Return current session status."""
        if not self.current_session:
            return {"status": "no_session"}
        return {
            "session": self.current_session.to_dict(),
            "red_stats": self.yeyohack.get_stats(),
            "blue_stats": self.guardian.get_stats(),
        }

    def get_metrics(self) -> dict[str, Any]:
        """Return aggregate battle metrics."""
        if not self.current_session:
            return {}
        s = self.current_session
        attack_types_seen = {r.attack_type for r in s.rounds}
        return {
            "session_id": s.id,
            "red_score": s.red_score,
            "blue_score": s.blue_score,
            "rounds_played": len(s.rounds),
            "attack_types_seen": sorted(attack_types_seen),
            "red_stats": self.yeyohack.get_stats(),
            "blue_stats": self.guardian.get_stats(),
        }

    def get_history(self) -> list[dict[str, Any]]:
        """Return all rounds as dicts."""
        if not self.current_session:
            return []
        return [r.to_dict() for r in self.current_session.rounds]
