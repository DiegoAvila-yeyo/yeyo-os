"""
YeyoOS — Arena Metrics
Scoreboard and historical battle data.
"""
import logging
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("yeyoos.arena.metrics")


@dataclass
class ArenaMetrics:
    """Aggregate statistics across multiple battle sessions."""

    total_sessions: int = 0
    total_rounds: int = 0
    red_wins: int = 0
    blue_wins: int = 0
    most_common_attack: str = ""
    defense_rate: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_sessions": self.total_sessions,
            "total_rounds": self.total_rounds,
            "red_wins": self.red_wins,
            "blue_wins": self.blue_wins,
            "most_common_attack": self.most_common_attack,
            "defense_rate": round(self.defense_rate, 3),
        }


class ArenaMetricsCollector:
    """Stores session history and computes aggregate statistics."""

    def __init__(self) -> None:
        self._session_results: list[dict[str, Any]] = []

    def record_session(self, session_data: dict[str, Any]) -> None:
        """Record a completed session's data for historical tracking."""
        self._session_results.append(session_data)
        logger.info("Session recorded — total sessions: %d", len(self._session_results))

    def get_aggregate_metrics(self) -> ArenaMetrics:
        """Compute aggregate metrics across all recorded sessions."""
        if not self._session_results:
            return ArenaMetrics()

        total_sessions = len(self._session_results)
        total_rounds = 0
        red_wins = 0
        blue_wins = 0
        attack_counter: Counter[str] = Counter()
        total_defenses = 0
        successful_defenses = 0

        for sess in self._session_results:
            session_info = sess.get("session", sess)
            red = session_info.get("red_score", 0)
            blue = session_info.get("blue_score", 0)
            rounds_played = session_info.get("total_rounds_played", 0)

            total_rounds += rounds_played
            if red > blue:
                red_wins += 1
            elif blue > red:
                blue_wins += 1

            # Count attacks from blue stats if available
            blue_stats = sess.get("blue_stats", {})
            total_defenses += blue_stats.get("total_defenses", 0)
            successful_defenses += blue_stats.get("successful_blocks", 0)

            # Count attack types from rounds history
            for rd in sess.get("rounds", []):
                attack_counter[rd.get("attack_type", "unknown")] += 1

        most_common = attack_counter.most_common(1)
        most_common_attack = most_common[0][0] if most_common else ""
        defense_rate = successful_defenses / total_defenses if total_defenses else 0.0

        return ArenaMetrics(
            total_sessions=total_sessions,
            total_rounds=total_rounds,
            red_wins=red_wins,
            blue_wins=blue_wins,
            most_common_attack=most_common_attack,
            defense_rate=defense_rate,
        )

    def get_session_history(self) -> list[dict[str, Any]]:
        """Return all recorded session data."""
        return list(self._session_results)

    def clear(self) -> None:
        """Reset all stored data."""
        self._session_results.clear()
