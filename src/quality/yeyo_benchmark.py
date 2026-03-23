"""
YeyoOS — YeyoBenchmark: Examen Semanal de Calidad
Micro-fase 6.15 — Capa 6: Sistema Inmune

50 problemas estandar con comparacion temporal.
Corre cada domingo a las 4 AM.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from enum import Enum

logger = logging.getLogger("yeyo.quality.benchmark")


class ProblemCategory(str, Enum):
    PYTHON = "python"
    TYPESCRIPT = "typescript"
    SQL = "sql"
    SECURITY = "security"
    ARCHITECTURE = "architecture"


@dataclass
class BenchmarkProblem:
    id: str
    category: ProblemCategory
    difficulty: str  # "easy", "medium", "hard"
    prompt: str
    expected_keywords: list[str] = field(default_factory=list)
    max_score: float = 1.0


@dataclass
class ProblemResult:
    problem_id: str
    score: float = 0.0
    passed: bool = False
    response: str = ""
    error: Optional[str] = None


@dataclass
class BenchmarkRun:
    run_id: str
    started_at: str = ""
    completed_at: str = ""
    total_problems: int = 0
    problems_passed: int = 0
    overall_score: float = 0.0
    results: list[ProblemResult] = field(default_factory=list)
    category_scores: dict[str, float] = field(default_factory=dict)
    degradation_percent: float = 0.0

    def __post_init__(self):
        if not self.started_at:
            self.started_at = datetime.now(timezone.utc).isoformat()

    def calculate_scores(self):
        if not self.results:
            return
        self.total_problems = len(self.results)
        self.problems_passed = sum(1 for r in self.results if r.passed)
        self.overall_score = sum(r.score for r in self.results) / self.total_problems if self.total_problems > 0 else 0.0


# Sample benchmark problems (10 of 50)
BENCHMARK_PROBLEMS = [
    BenchmarkProblem(id="py-001", category=ProblemCategory.PYTHON, difficulty="easy", prompt="Write a function that reverses a string", expected_keywords=["def", "return", "[::-1]"]),
    BenchmarkProblem(id="py-002", category=ProblemCategory.PYTHON, difficulty="medium", prompt="Implement a binary search function", expected_keywords=["def", "while", "mid", "return"]),
    BenchmarkProblem(id="py-003", category=ProblemCategory.PYTHON, difficulty="hard", prompt="Implement an async rate limiter with sliding window", expected_keywords=["async", "await", "time", "window"]),
    BenchmarkProblem(id="ts-001", category=ProblemCategory.TYPESCRIPT, difficulty="easy", prompt="Write a TypeScript function that filters an array by type", expected_keywords=["function", "filter", "return"]),
    BenchmarkProblem(id="ts-002", category=ProblemCategory.TYPESCRIPT, difficulty="medium", prompt="Create a generic Stack class in TypeScript", expected_keywords=["class", "Stack", "push", "pop"]),
    BenchmarkProblem(id="sql-001", category=ProblemCategory.SQL, difficulty="easy", prompt="Write a SQL query to find duplicate emails", expected_keywords=["SELECT", "GROUP BY", "HAVING", "COUNT"]),
    BenchmarkProblem(id="sql-002", category=ProblemCategory.SQL, difficulty="medium", prompt="Write a window function query for running totals", expected_keywords=["OVER", "ORDER BY", "SUM"]),
    BenchmarkProblem(id="sec-001", category=ProblemCategory.SECURITY, difficulty="medium", prompt="Write a function to sanitize SQL input", expected_keywords=["parameterized", "escape"]),
    BenchmarkProblem(id="arch-001", category=ProblemCategory.ARCHITECTURE, difficulty="medium", prompt="Design a circuit breaker pattern", expected_keywords=["class", "state", "open", "closed", "half"]),
    BenchmarkProblem(id="arch-002", category=ProblemCategory.ARCHITECTURE, difficulty="hard", prompt="Design an event sourcing system", expected_keywords=["event", "store", "replay", "aggregate"]),
]


class YeyoBenchmark:
    """Weekly benchmark suite."""

    def __init__(self, problems: Optional[list[BenchmarkProblem]] = None):
        self.problems = problems or BENCHMARK_PROBLEMS
        self._history: list[BenchmarkRun] = []

    def get_problems(self) -> list[BenchmarkProblem]:
        return self.problems

    def evaluate_response(self, problem: BenchmarkProblem, response: str) -> ProblemResult:
        """Evaluate a response against expected keywords."""
        if not response:
            return ProblemResult(problem_id=problem.id, score=0.0, passed=False, error="Empty response")

        matched = sum(1 for kw in problem.expected_keywords if kw.lower() in response.lower())
        total = len(problem.expected_keywords) if problem.expected_keywords else 1
        score = matched / total

        return ProblemResult(
            problem_id=problem.id,
            score=score,
            passed=score >= 0.6,
            response=response[:500],
        )

    def compare_with_previous(self, current: BenchmarkRun) -> float:
        """Compare current run with most recent previous. Returns degradation %."""
        if not self._history:
            return 0.0
        previous = self._history[-1]
        if previous.overall_score == 0:
            return 0.0
        degradation = (previous.overall_score - current.overall_score) / previous.overall_score * 100
        return max(0.0, degradation)

    def add_to_history(self, run: BenchmarkRun):
        self._history.append(run)

    def get_history(self) -> list[BenchmarkRun]:
        return self._history.copy()
