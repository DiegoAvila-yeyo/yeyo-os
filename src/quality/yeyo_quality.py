"""
YeyoOS — YeyoQuality: Criterios Objetivos de Feedback
Micro-fase 6.13 — Capa 6: Sistema Inmune

Evalua objetivamente si el codigo generado es bueno.
Solo score >= 0.8 genera feedback positivo al modelo.
"""

import logging
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from enum import Enum

logger = logging.getLogger("yeyo.quality")


class QualityLevel(str, Enum):
    EXCELLENT = "excellent"  # >= 0.9
    GOOD = "good"            # >= 0.8
    ACCEPTABLE = "acceptable"  # >= 0.6
    POOR = "poor"            # >= 0.4
    FAILING = "failing"      # < 0.4


@dataclass
class QualityCheck:
    name: str
    passed: bool
    score: float  # 0.0 to 1.0
    details: str = ""
    weight: float = 1.0


@dataclass
class QualityReport:
    code_id: str
    language: str
    checks: list[QualityCheck] = field(default_factory=list)
    overall_score: float = 0.0
    level: QualityLevel = QualityLevel.FAILING
    feedback_action: str = "none"  # "positive", "negative", "none"
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def calculate_score(self):
        if not self.checks:
            self.overall_score = 0.0
        else:
            total_weight = sum(c.weight for c in self.checks)
            if total_weight > 0:
                self.overall_score = sum(c.score * c.weight for c in self.checks) / total_weight
            else:
                self.overall_score = 0.0

        if self.overall_score >= 0.9:
            self.level = QualityLevel.EXCELLENT
        elif self.overall_score >= 0.8:
            self.level = QualityLevel.GOOD
        elif self.overall_score >= 0.6:
            self.level = QualityLevel.ACCEPTABLE
        elif self.overall_score >= 0.4:
            self.level = QualityLevel.POOR
        else:
            self.level = QualityLevel.FAILING

        if self.overall_score >= 0.8:
            self.feedback_action = "positive"
        elif self.overall_score < 0.4:
            self.feedback_action = "negative"
        else:
            self.feedback_action = "none"


class QualityEvaluator:
    """Evaluates code quality objectively."""

    def evaluate_syntax(self, code: str, language: str) -> QualityCheck:
        """Check if code has valid syntax."""
        if language == "python":
            try:
                compile(code, "<string>", "exec")
                return QualityCheck(name="syntax", passed=True, score=1.0, details="Valid Python syntax")
            except SyntaxError as e:
                return QualityCheck(name="syntax", passed=False, score=0.0, details=str(e))
        return QualityCheck(name="syntax", passed=True, score=0.5, details=f"No syntax check for {language}")

    def evaluate_no_dangerous_patterns(self, code: str) -> QualityCheck:
        """Check for dangerous patterns."""
        dangerous = ["eval(", "exec(", "__import__", "os.system(", "subprocess.call("]
        found = [p for p in dangerous if p in code]
        if found:
            return QualityCheck(
                name="security", passed=False, score=0.2,
                details=f"Dangerous patterns found: {found}", weight=2.0,
            )
        return QualityCheck(name="security", passed=True, score=1.0, weight=2.0)

    def evaluate_has_error_handling(self, code: str, language: str) -> QualityCheck:
        """Check if code has error handling."""
        if language == "python":
            has_try = "try:" in code
            has_except = "except" in code
            if has_try and has_except:
                return QualityCheck(name="error_handling", passed=True, score=1.0)
            elif has_try:
                return QualityCheck(name="error_handling", passed=False, score=0.5, details="try without except")
            return QualityCheck(name="error_handling", passed=False, score=0.3, details="No error handling")
        return QualityCheck(name="error_handling", passed=True, score=0.5)

    def evaluate(self, code: str, language: str = "python", code_id: str = "unknown") -> QualityReport:
        """Run all quality checks on code."""
        report = QualityReport(code_id=code_id, language=language)
        report.checks.append(self.evaluate_syntax(code, language))
        report.checks.append(self.evaluate_no_dangerous_patterns(code))
        report.checks.append(self.evaluate_has_error_handling(code, language))
        report.calculate_score()
        return report
