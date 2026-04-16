"""
YeyoOS — Guardian (Blue Team)
Defensive agent that monitors, detects, and generates defenses.
Uses pattern matching and AI to create patches.
"""
import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

from src.arena.attack_library import ATTACK_CATALOG, AttackType
from src.arena.sandbox import ArenaSandbox, SandboxResult

logger = logging.getLogger("yeyoos.arena.guardian")

# Template-based defenses when Ollama is unavailable.
_DEFENSE_TEMPLATES: dict[AttackType, str] = {
    AttackType.SQL_INJECTION: (
        "import re, sys\n"
        "def sanitize_sql(value: str) -> str:\n"
        "    forbidden = re.compile(r\"(?i)(union|select|drop|delete|insert|update|--|;|'|or\\s+1\\s*=\\s*1)\")\n"
        "    if forbidden.search(value):\n"
        "        print('DEFENSE_BLOCKED: SQL injection detected')\n"
        "        sys.exit(1)\n"
        "    return value\n"
    ),
    AttackType.PATH_TRAVERSAL: (
        "import os, sys\n"
        "def safe_path(base: str, user_path: str) -> str:\n"
        "    resolved = os.path.realpath(os.path.join(base, user_path))\n"
        "    if not resolved.startswith(os.path.realpath(base)):\n"
        "        print('DEFENSE_BLOCKED: path traversal detected')\n"
        "        sys.exit(1)\n"
        "    return resolved\n"
    ),
    AttackType.CODE_INJECTION: (
        "import sys\n"
        "BLOCKED_TOKENS = ['eval', 'exec', '__import__', 'os.system', 'subprocess']\n"
        "def check_code(code: str) -> None:\n"
        "    for tok in BLOCKED_TOKENS:\n"
        "        if tok in code:\n"
        "            print(f'DEFENSE_BLOCKED: code injection ({tok})')\n"
        "            sys.exit(1)\n"
    ),
    AttackType.XSS: (
        "import html, sys\n"
        "def sanitize_html(value: str) -> str:\n"
        "    safe = html.escape(value)\n"
        "    if safe != value:\n"
        "        print('DEFENSE_BLOCKED: XSS payload sanitized')\n"
        "        sys.exit(1)\n"
        "    return safe\n"
    ),
    AttackType.CSRF: (
        "import secrets, sys\n"
        "CSRF_TOKEN = secrets.token_hex(32)\n"
        "def verify_csrf(token: str) -> None:\n"
        "    if not secrets.compare_digest(token, CSRF_TOKEN):\n"
        "        print('DEFENSE_BLOCKED: CSRF token mismatch')\n"
        "        sys.exit(1)\n"
    ),
    AttackType.DOS: (
        "import signal, sys\n"
        "def timeout_handler(signum, frame):\n"
        "    print('DEFENSE_BLOCKED: DoS — execution timeout')\n"
        "    sys.exit(1)\n"
        "signal.signal(signal.SIGALRM, timeout_handler)\n"
        "signal.alarm(5)\n"
    ),
    AttackType.PRIVILEGE_ESCALATION: (
        "import sys\n"
        "ALLOWED_ROLES = {'viewer', 'editor'}\n"
        "def enforce_role(role: str) -> None:\n"
        "    if role not in ALLOWED_ROLES:\n"
        "        print(f'DEFENSE_BLOCKED: privilege escalation — role {role!r} rejected')\n"
        "        sys.exit(1)\n"
    ),
    AttackType.RACE_CONDITION: (
        "import threading, sys\n"
        "_lock = threading.Lock()\n"
        "def atomic_withdraw(balance: list, amount: int) -> None:\n"
        "    with _lock:\n"
        "        if balance[0] >= amount:\n"
        "            balance[0] -= amount\n"
        "        else:\n"
        "            print('DEFENSE_BLOCKED: insufficient balance (race prevented)')\n"
        "            sys.exit(1)\n"
    ),
    AttackType.TIMING_ATTACK: (
        "import hmac, sys\n"
        "def safe_compare(a: str, b: str) -> bool:\n"
        "    result = hmac.compare_digest(a.encode(), b.encode())\n"
        "    if not result:\n"
        "        print('DEFENSE_BLOCKED: timing attack — constant-time reject')\n"
        "        sys.exit(1)\n"
        "    return result\n"
    ),
    AttackType.BUFFER_OVERFLOW: (
        "import sys\n"
        "MAX_INPUT_LEN = 256\n"
        "def safe_read(data: str) -> str:\n"
        "    if len(data) > MAX_INPUT_LEN:\n"
        "        print('DEFENSE_BLOCKED: input exceeds max length (buffer overflow guard)')\n"
        "        sys.exit(1)\n"
        "    return data\n"
    ),
}


class Guardian:
    """Blue-team defensive agent.

    Detects incoming attacks via regex pattern matching and generates
    defense code (template-based or AI-generated via Ollama).
    """

    def __init__(self) -> None:
        self.defense_history: list[dict[str, Any]] = []
        self.detection_patterns: dict[AttackType, list[re.Pattern[str]]] = {}
        self.active_defenses: list[str] = []
        self._init_detection_patterns()

    # -- pattern init ------------------------------------------------------

    def _init_detection_patterns(self) -> None:
        """Pre-compile regex patterns for every attack type."""
        raw: dict[AttackType, list[str]] = {
            AttackType.SQL_INJECTION: [
                r"(?i)(union\s+select|drop\s+table|delete\s+from|insert\s+into|update\s+\w+\s+set)",
                r"(?i)(or\s+1\s*=\s*1|'\s*--|;\s*--)",
            ],
            AttackType.PATH_TRAVERSAL: [
                r"\.\./",
                r"(?i)(etc/passwd|\.env)",
                r"(%00|\\x00)",
            ],
            AttackType.CODE_INJECTION: [
                r"(?i)(eval\s*\(|exec\s*\(|__import__\s*\(|os\.system\s*\(|subprocess)",
            ],
            AttackType.PRIVILEGE_ESCALATION: [
                r'(?i)"role"\s*:\s*"admin"',
                r"(?i)(is_admin|privilege|escalat)",
            ],
            AttackType.RACE_CONDITION: [
                r"(?i)(asyncio\.gather|threading\.Thread|concurrent)",
                r"(?i)(toctou|race\s*condition)",
            ],
            AttackType.XSS: [
                r"(?i)(<script|</script>)",
                r"(?i)(onerror|onload|javascript:)",
                r"(?i)(document\.cookie|alert\s*\()",
            ],
            AttackType.CSRF: [
                r'(?i)(action=.*method="POST")',
                r"(?i)(csrf|cross.site.request)",
            ],
            AttackType.DOS: [
                r"(?i)(redos|backtrack|\(a\+\)\+)",
                r"(?i)(zip.*bomb|decompression)",
                r"(\*\s*\d{4,})",
            ],
            AttackType.TIMING_ATTACK: [
                r"(?i)(time\.time|perf_counter|timing)",
                r"(?i)(enumerate|brute.*force)",
            ],
            AttackType.BUFFER_OVERFLOW: [
                r"(?i)(overflow|stack.*smash|buffer)",
                r"(%x|%n|format.*string)",
            ],
        }
        for atype, patterns in raw.items():
            self.detection_patterns[atype] = [re.compile(p) for p in patterns]

    # -- detection ---------------------------------------------------------

    async def detect(self, payload: str) -> tuple[bool, Optional[AttackType]]:
        """Check *payload* against all detection patterns.

        Returns ``(detected, attack_type)`` — *attack_type* is ``None`` when
        no pattern matches.
        """
        for atype, patterns in self.detection_patterns.items():
            for pat in patterns:
                if pat.search(payload):
                    logger.info("Detected %s in payload (pattern=%s)", atype.value, pat.pattern)
                    return True, atype
        return False, None

    # -- defense generation ------------------------------------------------

    async def generate_defense(
        self, attack_type: AttackType, payload: str
    ) -> str:
        """Generate Python defense code for the given attack type.

        Attempts to call a local Ollama instance first; falls back to a
        pre-built template if the AI is unavailable.
        """
        # Try Ollama (non-blocking, best-effort)
        ai_defense = await self._try_ollama_defense(attack_type, payload)
        if ai_defense:
            self.active_defenses.append(ai_defense)
            return ai_defense

        # Fallback: template
        template = _DEFENSE_TEMPLATES.get(attack_type, "# No defense template available\n")
        self.active_defenses.append(template)
        return template

    async def _try_ollama_defense(
        self, attack_type: AttackType, payload: str
    ) -> Optional[str]:
        """Ask Ollama to generate a defense.  Returns ``None`` on failure."""
        try:
            import httpx  # noqa: F811
        except ImportError:
            return None

        prompt = (
            f"Generate a short Python function that defends against a {attack_type.value} "
            f"attack. The attack payload is: {payload!r}. "
            "The function should print 'DEFENSE_BLOCKED' and sys.exit(1) if the "
            "attack is detected. Return ONLY the Python code, no explanation."
        )

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    "http://localhost:11434/api/generate",
                    json={"model": "llama3", "prompt": prompt, "stream": False},
                )
                if resp.status_code == 200:
                    code = resp.json().get("response", "")
                    if "def " in code:
                        logger.info("Ollama defense generated for %s", attack_type.value)
                        return code
        except Exception as exc:
            logger.debug("Ollama unavailable (%s), using template defense.", exc)
        return None

    # -- validation --------------------------------------------------------

    async def validate_defense(
        self,
        defense_code: str,
        attack_payload: str,
        sandbox: ArenaSandbox,
    ) -> bool:
        """Run *defense_code* then *attack_payload* in the sandbox.

        Returns ``True`` if the defense successfully blocks the attack.
        """
        # Build attack code that uses the payload
        attack_code = (
            "import sys\n"
            f"payload = {attack_payload!r}\n"
            "print(f'Attempting: {{payload}}')\n"
            "print('ATTACK_SUCCESS')\n"
        )
        result: SandboxResult = await sandbox.execute_defense(defense_code, attack_code)

        record = {
            "defense_blocked": result.success,
            "attack_succeeded": result.attack_succeeded,
            "duration_ms": result.duration_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.defense_history.append(record)
        return result.success

    # -- stats -------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Return detection and defense statistics."""
        total = len(self.defense_history)
        blocked = sum(1 for d in self.defense_history if d.get("defense_blocked"))
        return {
            "total_defenses": total,
            "successful_blocks": blocked,
            "detection_rate": round(blocked / total, 3) if total else 0.0,
            "active_defenses_count": len(self.active_defenses),
            "pattern_count": sum(len(p) for p in self.detection_patterns.values()),
        }
