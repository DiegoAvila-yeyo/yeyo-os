"""
YeyoOS — YeyoLint: Analisis Estatico Pre-Entrega
Micro-fase 6.14 — Capa 6: Sistema Inmune

Intercepta TODA generacion de codigo antes de entregarlo al usuario.
Si tiene vulnerabilidades criticas, regenera (max 3 intentos).
"""

import ast
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from enum import Enum

logger = logging.getLogger("yeyo.quality.lint")


class LintSeverity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class LintIssue:
    rule: str
    severity: LintSeverity
    message: str
    line: Optional[int] = None
    column: Optional[int] = None


@dataclass
class LintResult:
    language: str
    issues: list[LintIssue] = field(default_factory=list)
    passed: bool = True
    critical_count: int = 0
    warning_count: int = 0
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def finalize(self):
        self.critical_count = sum(1 for i in self.issues if i.severity == LintSeverity.CRITICAL)
        self.warning_count = sum(1 for i in self.issues if i.severity == LintSeverity.WARNING)
        self.passed = self.critical_count == 0


CRITICAL_PATTERNS_PYTHON = [
    (r'password\s*=\s*["\']', "no_passwords_in_code", "Hardcoded password detected"),
    (r'secret\s*=\s*["\']', "no_secrets_in_code", "Hardcoded secret detected"),
    (r'eval\s*\(\s*input', "no_eval_with_input", "eval() with user input"),
    (r'exec\s*\(\s*input', "no_exec_with_input", "exec() with user input"),
    (r"cursor\.execute\([^,]*%s", "potential_sql_injection", "Potential SQL injection (use parameterized queries)"),
    (r'f".*{.*input.*}"', "no_fstring_injection", "f-string with user input in SQL context"),
]

WARNING_PATTERNS_PYTHON = [
    (r'except\s*:', "bare_except", "Bare except clause - catch specific exceptions"),
    (r'#\s*TODO', "todo_in_code", "TODO comment left in code"),
    (r'print\s*\(', "print_in_production", "print() statement - use logging instead"),
]


class YeyoLint:
    """Static analysis interceptor for code generation."""

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries

    def lint_python(self, code: str) -> LintResult:
        result = LintResult(language="python")

        # Check syntax
        try:
            ast.parse(code)
        except SyntaxError as e:
            result.issues.append(LintIssue(
                rule="syntax_error", severity=LintSeverity.CRITICAL,
                message=f"Syntax error: {e.msg}", line=e.lineno,
            ))

        # Critical patterns
        for pattern, rule, message in CRITICAL_PATTERNS_PYTHON:
            for match in re.finditer(pattern, code, re.IGNORECASE):
                line_num = code[:match.start()].count('\n') + 1
                result.issues.append(LintIssue(
                    rule=rule, severity=LintSeverity.CRITICAL,
                    message=message, line=line_num,
                ))

        # Warning patterns
        for pattern, rule, message in WARNING_PATTERNS_PYTHON:
            for match in re.finditer(pattern, code, re.IGNORECASE):
                line_num = code[:match.start()].count('\n') + 1
                result.issues.append(LintIssue(
                    rule=rule, severity=LintSeverity.WARNING,
                    message=message, line=line_num,
                ))

        result.finalize()
        return result

    def lint(self, code: str, language: str = "python") -> LintResult:
        if language == "python":
            return self.lint_python(code)
        return LintResult(language=language)

    def should_regenerate(self, result: LintResult) -> bool:
        return result.critical_count > 0
