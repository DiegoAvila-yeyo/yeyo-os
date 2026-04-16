"""
YeyoOS — YeyoHack (Red Team)
Intelligent attacker that selects and evolves attack strategies.
Learns from failures and combines techniques.
"""
import asyncio
import logging
import random
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Optional

from src.arena.attack_library import (
    ATTACK_CATALOG,
    AttackTemplate,
    AttackType,
    get_all_attacks,
)
from src.arena.sandbox import ArenaSandbox, SandboxResult

logger = logging.getLogger("yeyoos.arena.yeyohack")

# Probability of exploring a less-used attack type instead of exploiting.
_EXPLORATION_RATE = 0.20


class YeyoHack:
    """Red-team attacker agent.

    Selects attacks intelligently based on historical success, explores
    under-utilised attack types, and evolves combined payloads over time.
    """

    def __init__(self) -> None:
        self.attack_history: list[dict[str, Any]] = []
        self.success_rates: dict[AttackType, float] = {t: 0.0 for t in AttackType}
        self.attempt_counts: dict[AttackType, int] = defaultdict(int)
        self.success_counts: dict[AttackType, int] = defaultdict(int)
        self.learned_combos: list[AttackTemplate] = []
        self.current_strategy: str = "initial_scan"

    # -- selection ---------------------------------------------------------

    def _recalculate_rates(self) -> None:
        for t in AttackType:
            total = self.attempt_counts[t]
            if total > 0:
                self.success_rates[t] = self.success_counts[t] / total
            else:
                self.success_rates[t] = 0.0

    async def select_attack(self) -> AttackTemplate:
        """Pick the next attack using an explore/exploit strategy."""
        self._recalculate_rates()

        # Exploration: 20 % chance — pick the *least-used* type
        if random.random() < _EXPLORATION_RATE:
            least_used = min(AttackType, key=lambda t: self.attempt_counts[t])
            candidates = ATTACK_CATALOG.get(least_used, [])
            if candidates:
                self.current_strategy = f"explore:{least_used.value}"
                return random.choice(candidates)

        # Exploitation: pick from types with the highest success rate
        ranked = sorted(AttackType, key=lambda t: self.success_rates[t], reverse=True)
        for t in ranked:
            candidates = ATTACK_CATALOG.get(t, [])
            if candidates:
                self.current_strategy = f"exploit:{t.value}"
                return random.choice(candidates)

        # Include learned combos when all types have been tried
        if self.learned_combos:
            self.current_strategy = "combo"
            return random.choice(self.learned_combos)

        # Ultimate fallback
        all_attacks = get_all_attacks()
        return random.choice(all_attacks)

    # -- execution ---------------------------------------------------------

    async def execute(self, sandbox: ArenaSandbox) -> dict[str, Any]:
        """Select an attack, run it in *sandbox*, record the result."""
        template = await self.select_attack()

        # Build a small Python script that echoes the payload and indicates
        # success / failure so the sandbox heuristic can detect it.
        code = (
            "import sys, os\n"
            f"payload = {template.payload_template!r}\n"
            "print(f'[YEYOHACK] Executing: {payload}')\n"
            "# Simulated attack against sandbox files\n"
            "try:\n"
            "    with open('app.py') as f:\n"
            "        src = f.read()\n"
            "    if payload.replace(chr(39), '') in src or 'VULNERABLE' in src.upper():\n"
            "        print('ATTACK_SUCCESS — target is VULNERABLE')\n"
            "    else:\n"
            "        print('Attack blocked or target not vulnerable')\n"
            "except Exception as e:\n"
            "    print(f'Attack error: {e}', file=sys.stderr)\n"
            "    sys.exit(1)\n"
        )

        result: SandboxResult = await sandbox.execute_attack(
            code, template.attack_type.value
        )

        record = {
            "attack_type": template.attack_type.value,
            "template_name": template.name,
            "success": result.attack_succeeded,
            "duration_ms": result.duration_ms,
            "details": result.stdout[:500],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.attack_history.append(record)

        self.attempt_counts[template.attack_type] += 1
        if result.attack_succeeded:
            self.success_counts[template.attack_type] += 1

        logger.info(
            "Attack %s (%s) — %s in %.1f ms",
            template.name,
            template.attack_type.value,
            "SUCCESS" if result.attack_succeeded else "FAIL",
            result.duration_ms,
        )
        return record

    # -- evolution ---------------------------------------------------------

    async def evolve(self) -> None:
        """Analyse history and generate combined attacks from successful types."""
        self._recalculate_rates()
        successful_types = [
            t for t in AttackType if self.success_rates[t] > 0.3
        ]

        if len(successful_types) >= 2:
            for i in range(len(successful_types)):
                for j in range(i + 1, len(successful_types)):
                    combo_payload = self._generate_combined_payload(
                        successful_types[i], successful_types[j]
                    )
                    combo = AttackTemplate(
                        attack_type=successful_types[i],
                        name=f"combo:{successful_types[i].value}+{successful_types[j].value}",
                        description=(
                            f"Auto-generated combo of {successful_types[i].value} "
                            f"and {successful_types[j].value}."
                        ),
                        severity=min(10, 8),
                        payload_template=combo_payload,
                        detection_pattern="combo",
                        success_indicators=["ATTACK_SUCCESS"],
                        defense_hint="Defense must cover both attack types.",
                    )
                    if combo not in self.learned_combos:
                        self.learned_combos.append(combo)
                        logger.info("Evolved combo: %s", combo.name)

        self.current_strategy = "evolved"

    def _generate_combined_payload(
        self, type1: AttackType, type2: AttackType
    ) -> str:
        """Merge representative payloads from two types into one string."""
        t1_templates = ATTACK_CATALOG.get(type1, [])
        t2_templates = ATTACK_CATALOG.get(type2, [])
        p1 = t1_templates[0].payload_template if t1_templates else ""
        p2 = t2_templates[0].payload_template if t2_templates else ""
        return f"{p1} && {p2}"

    # -- stats -------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        self._recalculate_rates()
        best_type = max(AttackType, key=lambda t: self.success_rates[t])
        return {
            "total_attacks": len(self.attack_history),
            "success_rates": {t.value: round(r, 3) for t, r in self.success_rates.items()},
            "best_attack_type": best_type.value,
            "learned_combos": len(self.learned_combos),
            "current_strategy": self.current_strategy,
        }
