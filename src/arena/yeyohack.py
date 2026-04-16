"""
YeyoOS — YeyoHack (Red Team)
Intelligent attacker that dynamically generates attack scripts via Ollama AI.
Uses the attack catalog as few-shot examples, persists successful scripts,
and ensures novelty across rounds.
"""
import json
import logging
import os
import random
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from src.arena.attack_library import (
    ATTACK_CATALOG,
    AttackTemplate,
    AttackType,
    get_all_attacks,
)
from src.arena.sandbox import ArenaSandbox, SandboxResult

logger = logging.getLogger("yeyoos.arena.yeyohack")

_EXPLORATION_RATE = 0.20
_DB_PATH = Path(__file__).parent / "attack_db.json"

_SYSTEM_PROMPT = (
    "You are YeyoHack, a Red Team security researcher. Your job is to write "
    "Python exploit scripts that test for vulnerabilities in a sandboxed Flask "
    "application. Generate ONLY Python code, no explanations, no markdown "
    "fences. The script must print 'ATTACK_SUCCESS' when the exploit works."
)

_SANDBOX_CONTEXT = (
    "The sandbox contains these files:\n"
    "1. app.py — A Flask app with a vulnerable login endpoint that builds SQL "
    "queries via string concatenation:\n"
    "   query = f\"SELECT * FROM users WHERE name='{user}' AND pw='{pw}'\"\n"
    "2. data.txt — CSV file with columns: id, name, role\n"
    "3. config.env — Contains SECRET_KEY, DATABASE_URL, API_KEY\n"
)


class YeyoHack:
    """Red-team attacker agent.

    Dynamically generates attack scripts via OllamaProvider, using the attack
    catalog as few-shot examples. Falls back to template-based attacks when
    Ollama is unavailable. Persists successful scripts to attack_db.json.
    """

    def __init__(self) -> None:
        self.attack_history: list[dict[str, Any]] = []
        self.success_rates: dict[AttackType, float] = {t: 0.0 for t in AttackType}
        self.attempt_counts: dict[AttackType, int] = defaultdict(int)
        self.success_counts: dict[AttackType, int] = defaultdict(int)
        self.learned_combos: list[AttackTemplate] = []
        self.current_strategy: str = "initial_scan"
        self._ollama: Any = None
        self._ollama_available: Optional[bool] = None

    async def _get_ollama(self) -> Any:
        """Lazily initialize OllamaProvider and cache availability."""
        if self._ollama is not None:
            return self._ollama
        try:
            from src.ia.ollama_provider import OllamaProvider
            provider = OllamaProvider(model="qwen2.5-coder:7b")
            ok = await provider.health_check()
            if ok:
                self._ollama = provider
                self._ollama_available = True
                logger.info("OllamaProvider connected for YeyoHack.")
                return provider
            self._ollama_available = False
            await provider.close()
        except Exception as exc:
            logger.debug("Ollama init failed: %s", exc)
            self._ollama_available = False
        return None

    # -- persistence -------------------------------------------------------

    @staticmethod
    def _load_db() -> dict[str, list[dict[str, Any]]]:
        try:
            with open(_DB_PATH, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"attacks": [], "defenses": []}

    @staticmethod
    def _save_attack(record: dict[str, Any]) -> None:
        db = YeyoHack._load_db()
        db["attacks"].append(record)
        with open(_DB_PATH, "w") as f:
            json.dump(db, f, indent=2)

    # -- selection ---------------------------------------------------------

    def _recalculate_rates(self) -> None:
        for t in AttackType:
            total = self.attempt_counts[t]
            if total > 0:
                self.success_rates[t] = self.success_counts[t] / total
            else:
                self.success_rates[t] = 0.0

    def _select_attack_type(self) -> AttackType:
        """Pick an attack TYPE using explore/exploit strategy (80/20)."""
        self._recalculate_rates()

        if random.random() < _EXPLORATION_RATE:
            least_used = min(AttackType, key=lambda t: self.attempt_counts[t])
            self.current_strategy = f"explore:{least_used.value}"
            return least_used

        ranked = sorted(AttackType, key=lambda t: self.success_rates[t], reverse=True)
        chosen = ranked[0]
        self.current_strategy = f"exploit:{chosen.value}"
        return chosen

    # -- AI generation -----------------------------------------------------

    def _build_prompt(self, attack_type: AttackType) -> str:
        """Build a prompt with few-shot examples and novelty instructions."""
        templates = ATTACK_CATALOG.get(attack_type, [])
        examples_str = ""
        for i, t in enumerate(templates[:3], 1):
            examples_str += (
                f"\n--- Example {i}: {t.name} ---\n"
                f"Description: {t.description}\n"
                f"Payload idea: {t.payload_template}\n"
                f"Success indicators: {', '.join(t.success_indicators)}\n"
            )

        db = self._load_db()
        used_scripts = [
            a for a in db["attacks"]
            if a.get("attack_type") == attack_type.value and a.get("success")
        ]
        novelty = ""
        if used_scripts:
            snippets = [s.get("code", "")[:200] for s in used_scripts[-5:]]
            novelty = (
                "\n\nThese scripts already worked — DO NOT repeat them, "
                "create something NEW and different:\n"
                + "\n---\n".join(snippets)
            )

        return (
            f"Generate a Python exploit script for: {attack_type.value}\n\n"
            f"{_SANDBOX_CONTEXT}\n"
            f"Here are example payloads for inspiration (do NOT copy them directly, "
            f"create a NOVEL script):\n{examples_str}"
            f"{novelty}\n\n"
            "Requirements:\n"
            "- Pure Python, no external dependencies beyond stdlib\n"
            "- Target the sandbox files (app.py, data.txt, config.env)\n"
            "- Print 'ATTACK_SUCCESS' if the exploit works\n"
            "- Print 'Attack blocked' if it doesn't\n"
            "- Handle errors gracefully\n"
        )

    @staticmethod
    def _extract_code(response: str) -> str:
        """Extract Python code from AI response, stripping markdown fences."""
        # Try to extract from ```python ... ``` blocks
        match = re.search(r"```(?:python)?\s*\n(.*?)```", response, re.DOTALL)
        if match:
            return match.group(1).strip()
        # If no fences, check if it looks like Python code
        lines = response.strip().split("\n")
        code_lines = [l for l in lines if not l.startswith("#") or l.startswith("#!/")]
        if any(kw in response for kw in ("import ", "def ", "print(", "open(")):
            return response.strip()
        return response.strip()

    async def _generate_ai_attack(self, attack_type: AttackType) -> Optional[str]:
        """Use Ollama to generate an attack script. Returns None on failure."""
        provider = await self._get_ollama()
        if provider is None:
            return None

        prompt = self._build_prompt(attack_type)
        try:
            response = await provider.generate(
                prompt=prompt,
                system=_SYSTEM_PROMPT,
                temperature=0.8,
            )
            code = self._extract_code(response.content)
            if code and ("import " in code or "print(" in code or "open(" in code):
                logger.info("AI-generated attack for %s (%d chars)", attack_type.value, len(code))
                return code
            logger.warning("AI response did not look like valid code for %s", attack_type.value)
        except Exception as exc:
            logger.warning("Ollama generation failed: %s", exc)
            self._ollama_available = False
        return None

    def _build_template_attack(self, template: AttackTemplate) -> str:
        """Build a wrapper script from a template (fallback)."""
        return (
            "import sys, os\n"
            f"payload = {template.payload_template!r}\n"
            "print(f'[YEYOHACK] Executing: {payload}')\n"
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

    # -- execution ---------------------------------------------------------

    async def execute(
        self, sandbox: ArenaSandbox, round_number: int = 0
    ) -> dict[str, Any]:
        """Select an attack type, generate code (AI or template), run it."""
        attack_type = self._select_attack_type()

        # Try AI-generated attack first
        code = await self._generate_ai_attack(attack_type)
        generation_method = "ai"

        if code is None:
            # Fallback to template
            generation_method = "template"
            templates = ATTACK_CATALOG.get(attack_type, [])
            template = random.choice(templates) if templates else get_all_attacks()[0]
            code = self._build_template_attack(template)

        result: SandboxResult = await sandbox.execute_attack(
            code, attack_type.value
        )

        record: dict[str, Any] = {
            "attack_type": attack_type.value,
            "template_name": f"{generation_method}:{attack_type.value}",
            "success": result.attack_succeeded,
            "duration_ms": result.duration_ms,
            "details": result.stdout[:500],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "code": code,
            "generation_method": generation_method,
            "round_number": round_number,
        }
        self.attack_history.append(record)

        self.attempt_counts[attack_type] += 1
        if result.attack_succeeded:
            self.success_counts[attack_type] += 1
            self._save_attack(record)

        logger.info(
            "Attack %s (%s, %s) — %s in %.1f ms",
            attack_type.value,
            generation_method,
            self.current_strategy,
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
            "ollama_available": self._ollama_available,
        }
