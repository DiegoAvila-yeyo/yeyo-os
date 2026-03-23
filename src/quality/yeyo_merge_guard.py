"""
YeyoOS — YeyoMergeGuard: Validacion Pre-Merge de Aprendizajes YeyoNet
Micro-fase 6.16 — Capa 6: Sistema Inmune

Valida aprendizajes de nodos satelite antes de aplicarlos al cerebro central.
Sandbox + mini-benchmark para detectar degradacion.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from enum import Enum

logger = logging.getLogger("yeyo.quality.merge_guard")


class MergeDecision(str, Enum):
    ACCEPT = "accept"          # No degradation
    QUARANTINE = "quarantine"  # Degradation <= 2%
    REJECT = "reject"          # Degradation > 2%


@dataclass
class LearningPayload:
    nodo_id: str
    content: dict
    tags: list[str] = field(default_factory=list)
    importance: float = 0.5
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class MergeResult:
    nodo_id: str
    decision: MergeDecision
    baseline_score: float = 0.0
    after_score: float = 0.0
    degradation_percent: float = 0.0
    details: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class NodeTrustRecord:
    nodo_id: str
    total_submissions: int = 0
    accepted: int = 0
    quarantined: int = 0
    rejected: int = 0
    consecutive_rejections: int = 0
    suspended: bool = False


class YeyoMergeGuard:
    """Validates external learnings before applying to central model."""

    DEGRADATION_QUARANTINE = 2.0  # %
    MAX_CONSECUTIVE_REJECTIONS = 3

    def __init__(self):
        self._trust_records: dict[str, NodeTrustRecord] = {}
        self._merge_history: list[MergeResult] = []

    def _get_trust(self, nodo_id: str) -> NodeTrustRecord:
        if nodo_id not in self._trust_records:
            self._trust_records[nodo_id] = NodeTrustRecord(nodo_id=nodo_id)
        return self._trust_records[nodo_id]

    def evaluate(self, payload: LearningPayload, baseline_score: float, after_score: float) -> MergeResult:
        """Evaluate a learning payload against benchmark scores."""
        trust = self._get_trust(payload.nodo_id)
        trust.total_submissions += 1

        if baseline_score == 0:
            degradation = 0.0
        else:
            degradation = max(0.0, (baseline_score - after_score) / baseline_score * 100)

        if degradation == 0.0:
            decision = MergeDecision.ACCEPT
            trust.accepted += 1
            trust.consecutive_rejections = 0
        elif degradation <= self.DEGRADATION_QUARANTINE:
            decision = MergeDecision.QUARANTINE
            trust.quarantined += 1
            trust.consecutive_rejections = 0
        else:
            decision = MergeDecision.REJECT
            trust.rejected += 1
            trust.consecutive_rejections += 1

        if trust.consecutive_rejections >= self.MAX_CONSECUTIVE_REJECTIONS:
            trust.suspended = True
            logger.warning(f"Node {payload.nodo_id} suspended after {self.MAX_CONSECUTIVE_REJECTIONS} consecutive rejections")

        result = MergeResult(
            nodo_id=payload.nodo_id,
            decision=decision,
            baseline_score=baseline_score,
            after_score=after_score,
            degradation_percent=degradation,
            details=f"Degradation: {degradation:.2f}%, Decision: {decision.value}",
        )
        self._merge_history.append(result)
        return result

    def is_node_suspended(self, nodo_id: str) -> bool:
        trust = self._trust_records.get(nodo_id)
        return trust.suspended if trust else False

    def get_trust_record(self, nodo_id: str) -> Optional[NodeTrustRecord]:
        return self._trust_records.get(nodo_id)

    def get_history(self) -> list[MergeResult]:
        return self._merge_history.copy()
