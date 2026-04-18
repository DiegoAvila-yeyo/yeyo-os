"""
YeyoNet — Scheduler circular para pipelines multi-step.
"""
from __future__ import annotations

from dataclasses import dataclass


class NoEligibleRingNodeError(RuntimeError):
    """Raised when no node in the ring can execute a step."""


@dataclass(frozen=True)
class RingAssignment:
    node_id: str
    ring_index: int


class RingScheduler:
    """Asigna pasos siguiendo el orden del anillo y saltando nodos no elegibles."""

    def assign_steps(
        self,
        ring_node_ids: list[str],
        step_specs: list[dict],
        capabilities_by_node: dict[str, dict] | None = None,
    ) -> list[RingAssignment]:
        if not ring_node_ids:
            raise ValueError("ring_node_ids cannot be empty")

        capabilities = capabilities_by_node or {}
        assignments: list[RingAssignment] = []
        next_index = 0

        for step_spec in step_specs:
            requirements = dict(step_spec.get("requirements") or {})
            assignment = self._next_eligible_node(
                ring_node_ids=ring_node_ids,
                start_index=next_index,
                requirements=requirements,
                capabilities_by_node=capabilities,
            )
            assignments.append(assignment)
            next_index = (assignment.ring_index + 1) % len(ring_node_ids)

        return assignments

    def _next_eligible_node(
        self,
        ring_node_ids: list[str],
        start_index: int,
        requirements: dict,
        capabilities_by_node: dict[str, dict],
    ) -> RingAssignment:
        for offset in range(len(ring_node_ids)):
            ring_index = (start_index + offset) % len(ring_node_ids)
            node_id = ring_node_ids[ring_index]
            resources = capabilities_by_node.get(node_id, {})
            if self._meets_requirements(resources, requirements):
                return RingAssignment(node_id=node_id, ring_index=ring_index)

        raise NoEligibleRingNodeError("No eligible node found for pipeline step")

    @staticmethod
    def _meets_requirements(resources: dict, requirements: dict) -> bool:
        if requirements.get("needs_gpu") and not resources.get("gpu_name"):
            return False
        if requirements.get("needs_ollama") and not resources.get("ollama_models"):
            return False

        min_ram_gb = float(requirements.get("min_ram_gb", 0) or 0)
        if min_ram_gb and float(resources.get("ram_free_gb", min_ram_gb)) < min_ram_gb:
            return False

        return True
