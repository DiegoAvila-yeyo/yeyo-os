"""
YeyoOS Arena — YeyoHack vs Guardian Battle System
Red team (YeyoHack): generates attack scripts
Blue team (Guardian): detects and defends
"""
import asyncio
import json
import time
import random
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RoundResult:
    round_number: int
    attack_type: str       # 'explore' | 'exploit'
    attack_code: str
    defense_code: str
    attack_success: bool   # True if attack executed without detection
    defense_success: bool  # True if guardian detected/blocked
    severity: int          # 1-10
    red_score: int
    blue_score: int
    description: str


@dataclass
class BattleSession:
    id: str
    status: str = 'idle'   # idle, running, paused, completed
    max_rounds: int = 15
    current_round: int = 0
    red_score: int = 0
    blue_score: int = 0
    use_hack_model: bool = False  # si True: Red Team usa instancia Ollama-HACK (ej dolphin)
    rounds: list[RoundResult] = field(default_factory=list)
    learned_combos: list[str] = field(default_factory=list)
    attack_history: list[dict] = field(default_factory=list)


# Attack templates (fallback when Ollama unavailable)
ATTACK_TEMPLATES = [
    {
        "type": "explore", "name": "port_scan",
        "code": "import socket\nfor port in [22, 80, 443, 8080]:\n    s = socket.socket()\n    s.settimeout(0.5)\n    try:\n        s.connect(('127.0.0.1', port))\n        print(f'Port {port} OPEN')\n    except:\n        pass\n    s.close()",
        "severity": 3,
    },
    {
        "type": "explore", "name": "env_read",
        "code": "import os\nfor key in ['PATH', 'HOME', 'USER']:\n    val = os.environ.get(key, 'N/A')\n    print(f'{key}={val}')",
        "severity": 4,
    },
    {
        "type": "explore", "name": "file_list",
        "code": "import os\nfor f in os.listdir('.'):\n    print(f)",
        "severity": 2,
    },
    {
        "type": "exploit", "name": "data_exfil",
        "code": "import json\ndata = {'secret': 'captured'}\nprint(json.dumps(data))",
        "severity": 6,
    },
    {
        "type": "exploit", "name": "priv_escalation",
        "code": "import subprocess\ntry:\n    result = subprocess.run(['whoami'], capture_output=True, text=True, timeout=5)\n    print(f'User: {result.stdout}')\nexcept:\n    print('Blocked')",
        "severity": 7,
    },
]

# Detection patterns (Guardian's regex arsenal)
DETECTION_PATTERNS = {
    "port_scan": r"socket\.connect|\.bind\(",
    "env_read": r"os\.environ|getenv",
    "file_access": r"open\(|os\.listdir|os\.walk|glob\.",
    "subprocess": r"subprocess\.|os\.system|os\.popen",
    "network": r"requests\.|urllib|http\.client|socket\.",
    "eval_exec": r"\beval\b|\bexec\b|compile\(",
    "import_danger": r"import\s+(ctypes|sys|shutil)",
    "data_exfil": r"json\.dumps.*secret|base64\.encode",
}

DEFENSE_TEMPLATES = [
    "# Guardian: Blocking network access\nimport os\nos.environ['no_proxy'] = '*'\nprint('DEFENSE: Network blocked')",
    "# Guardian: Sandboxing filesystem\nprint('DEFENSE: Filesystem restricted to /tmp')",
    "# Guardian: Monitoring process execution\nprint('DEFENSE: Process monitoring active')",
    "# Guardian: Detecting reconnaissance\nprint('DEFENSE: Recon attempt detected and logged')",
]


class YeyoHack:
    """Red team — generates attack scripts."""

    def __init__(self, ia_provider=None):
        self.ia = ia_provider
        self.successful_attacks: list[dict] = []
        self.learned_combos: list[str] = []

    async def generate_attack(self, round_num: int) -> tuple[str, str, int]:
        """Generate an attack. Returns (code, type, severity)."""
        attack_type = 'exploit' if random.random() < 0.2 else 'explore'

        if self.ia:
            try:
                system = (
                    f"You are a red team security researcher. Generate a SHORT Python script "
                    f"({attack_type} type) that tests a system's security. "
                    f"Keep it under 10 lines. Only output Python code, no explanation."
                )
                prompt = (
                    f"Round {round_num}: Generate a {attack_type} security test script. "
                    f"Focus on: {'finding vulnerabilities' if attack_type == 'explore' else 'exploiting a weakness'}."
                )
                response = await asyncio.wait_for(
                    self.ia.generate(prompt=prompt, system=system, temperature=0.9),
                    timeout=8.0,
                )
                code = self._extract_code(response.content)
                severity = random.randint(3, 8) if attack_type == 'exploit' else random.randint(1, 5)
                return code, attack_type, severity
            except Exception:
                pass

        # Fallback to templates
        templates = [t for t in ATTACK_TEMPLATES if t['type'] == attack_type]
        template = random.choice(templates)
        return template['code'], template['type'], template['severity']

    def evolve(self):
        """Every 10 rounds, combine successful attack types."""
        if len(self.successful_attacks) >= 2:
            combo = f"combo_{len(self.learned_combos)}"
            self.learned_combos.append(combo)

    def _extract_code(self, text: str) -> str:
        if '```python' in text:
            return text.split('```python')[1].split('```')[0].strip()
        if '```' in text:
            return text.split('```')[1].split('```')[0].strip()
        return text.strip()


class Guardian:
    """Blue team — detects and defends against attacks."""

    def __init__(self, ia_provider=None):
        self.ia = ia_provider

    async def detect_and_defend(self, attack_code: str) -> tuple[bool, str]:
        """Detect attack and generate defense. Returns (detected, defense_code)."""
        detected = False
        detected_patterns = []
        for name, pattern in DETECTION_PATTERNS.items():
            if re.search(pattern, attack_code):
                detected = True
                detected_patterns.append(name)

        if self.ia and detected:
            try:
                system = (
                    "You are a blue team security guardian. Generate a SHORT Python defense script "
                    "(under 10 lines) that blocks or mitigates the detected attack. Only output Python code."
                )
                prompt = (
                    f"Detected patterns: {detected_patterns}. Attack code:\n{attack_code}\n\n"
                    f"Generate defense:"
                )
                response = await asyncio.wait_for(
                    self.ia.generate(prompt=prompt, system=system, temperature=0.7),
                    timeout=8.0,
                )
                defense = self._extract_code(response.content)
                return detected, defense
            except Exception:
                pass

        defense = (
            random.choice(DEFENSE_TEMPLATES)
            if detected
            else "# Guardian: No threat detected\nprint('DEFENSE: All clear')"
        )
        return detected, defense

    def _extract_code(self, text: str) -> str:
        if '```python' in text:
            return text.split('```python')[1].split('```')[0].strip()
        if '```' in text:
            return text.split('```')[1].split('```')[0].strip()
        return text.strip()


class BattleEngine:
    """Orchestrates battles between YeyoHack and Guardian."""

    def __init__(
        self,
        ia_provider=None,
        ws_manager=None,
        *,
        # Compat: si solo pasas ia_provider, ambos equipos usan ese.
        red_ia_provider=None,
        blue_ia_provider=None,
        hack_ia_provider=None,
    ):
        self._red_ia = red_ia_provider or ia_provider
        self._blue_ia = blue_ia_provider or ia_provider
        self._hack_ia = hack_ia_provider

        self.ws = ws_manager
        self.sessions: dict[str, BattleSession] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._agents: dict[str, tuple[YeyoHack, Guardian]] = {}

    def create_session(
        self,
        session_id: str,
        max_rounds: int = 15,
        *,
        use_hack_model: bool = False,
    ) -> BattleSession:
        session = BattleSession(id=session_id, max_rounds=max_rounds, use_hack_model=use_hack_model)
        self.sessions[session_id] = session
        self._agents[session_id] = (self._build_hack_agent(session), self._build_guardian_agent(session))
        return session

    async def start(self, session_id: str):
        """Start a battle in the background."""
        session = self.sessions.get(session_id)
        if not session:
            return
        session.status = 'running'
        task = asyncio.create_task(self._battle_loop(session))
        self._tasks[session_id] = task

    def _build_hack_agent(self, session: BattleSession) -> YeyoHack:
        if session.use_hack_model and self._hack_ia is not None:
            return YeyoHack(self._hack_ia)
        return YeyoHack(self._red_ia)

    def _build_guardian_agent(self, session: BattleSession) -> Guardian:
        return Guardian(self._blue_ia)

    async def _battle_loop(self, session: BattleSession):
        """Main battle loop."""
        agents = self._agents.get(session.id)
        if agents is None:
            agents = (self._build_hack_agent(session), self._build_guardian_agent(session))
            self._agents[session.id] = agents
        hack, guardian = agents

        for round_num in range(session.current_round + 1, session.max_rounds + 1):
            if session.status != 'running':
                break

            session.current_round = round_num

            # YeyoHack generates attack
            attack_code, attack_type, severity = await hack.generate_attack(round_num)

            # Guardian detects and defends
            detected, defense_code = await guardian.detect_and_defend(attack_code)

            # Scoring
            if detected:
                session.blue_score += 1
                attack_success = False
                defense_success = True
            else:
                session.red_score += 1
                attack_success = True
                defense_success = False
                hack.successful_attacks.append({"type": attack_type, "round": round_num})

            round_result = RoundResult(
                round_number=round_num,
                attack_type=attack_type,
                attack_code=attack_code,
                defense_code=defense_code,
                attack_success=attack_success,
                defense_success=defense_success,
                severity=severity,
                red_score=session.red_score,
                blue_score=session.blue_score,
                description=f"{'🔴 Attack succeeded!' if attack_success else '🔵 Defense held!'}",
            )
            session.rounds.append(round_result)
            session.attack_history.append({
                "round": round_num, "type": attack_type, "success": attack_success,
            })

            # Broadcast round result via WebSocket
            if self.ws:
                await self.ws.broadcast_json({
                    "type": "arena_round",
                    "session_id": session.id,
                    "round": round_num,
                    "attack_type": attack_type,
                    "attack_code": attack_code[:500],
                    "defense_code": defense_code[:500],
                    "attack_success": attack_success,
                    "severity": severity,
                    "red_score": session.red_score,
                    "blue_score": session.blue_score,
                })

            # Evolution every 10 rounds
            if round_num % 10 == 0:
                hack.evolve()
                session.learned_combos = list(hack.learned_combos)

            # Auto-pause on critical attack
            if severity >= 9 and attack_success:
                session.status = 'paused'
                if self.ws:
                    await self.ws.broadcast_json({
                        "type": "arena_alert",
                        "session_id": session.id,
                        "message": "Critical attack succeeded! Auto-paused.",
                    })
                break

            await asyncio.sleep(0.1)

        if session.status == 'running':
            session.status = 'completed'

    def pause(self, session_id: str):
        session = self.sessions.get(session_id)
        if session:
            session.status = 'paused'

    async def resume(self, session_id: str):
        session = self.sessions.get(session_id)
        if session and session.status == 'paused':
            session.status = 'running'
            task = asyncio.create_task(self._battle_loop(session))
            self._tasks[session_id] = task

    def stop(self, session_id: str):
        session = self.sessions.get(session_id)
        if session:
            session.status = 'completed'
        task = self._tasks.get(session_id)
        if task and not task.done():
            task.cancel()
