"""Tests para DevOps Tools — Micro-fases 6.12-6.16"""

import pytest
from src.security.hack.red_team import RedTeamAgent, AttackVector, AttackPlan
from src.security.hack.arena import DockerArena, ArenaConfig
from src.quality.yeyo_quality import QualityEvaluator, QualityLevel, QualityReport
from src.quality.yeyo_lint import YeyoLint, LintSeverity
from src.quality.yeyo_benchmark import YeyoBenchmark, BenchmarkProblem, BenchmarkRun, ProblemCategory, ProblemResult, BENCHMARK_PROBLEMS
from src.quality.yeyo_merge_guard import YeyoMergeGuard, LearningPayload, MergeDecision


# ═══════════════════════════════════
# YEYO-HACK (6.12)
# ═══════════════════════════════════

class TestRedTeam:
    def test_all_attack_vectors(self):
        agent = RedTeamAgent()
        vectors = agent.get_all_vectors()
        assert len(vectors) == 10

    def test_generate_attack_plan(self):
        agent = RedTeamAgent()
        plan = agent.generate_attack_plan(AttackVector.SQL_INJECTION, "/api/users")
        assert plan.vector == AttackVector.SQL_INJECTION
        assert plan.target_endpoint == "/api/users"
        assert len(plan.payload) > 0

    def test_attack_plan_has_payload(self):
        agent = RedTeamAgent()
        for vector in AttackVector:
            plan = agent.generate_attack_plan(vector)
            assert plan.payload, f"No payload for {vector}"


class TestDockerArena:
    def test_create_and_destroy(self):
        arena = DockerArena()
        assert not arena.is_running()
        arena.create()
        assert arena.is_running()
        arena.destroy()
        assert not arena.is_running()

    def test_status(self):
        arena = DockerArena()
        status = arena.get_status()
        assert "container" in status
        assert "running" in status


# ═══════════════════════════════════
# YeyoQuality (6.13)
# ═══════════════════════════════════

class TestQualityEvaluator:
    def test_valid_python(self):
        evaluator = QualityEvaluator()
        code = '''
def hello():
    try:
        return "world"
    except Exception as e:
        return str(e)
'''
        report = evaluator.evaluate(code, "python")
        assert report.overall_score >= 0.8
        assert report.feedback_action == "positive"

    def test_dangerous_code(self):
        evaluator = QualityEvaluator()
        code = 'result = eval(user_input)'
        report = evaluator.evaluate(code, "python")
        assert report.overall_score < 0.8
        assert any(c.name == "security" and not c.passed for c in report.checks)

    def test_syntax_error(self):
        evaluator = QualityEvaluator()
        code = 'def foo(:'
        report = evaluator.evaluate(code, "python")
        assert any(c.name == "syntax" and not c.passed for c in report.checks)

    def test_quality_levels(self):
        assert QualityLevel.EXCELLENT.value == "excellent"
        assert QualityLevel.FAILING.value == "failing"

    def test_feedback_thresholds(self):
        report = QualityReport(code_id="test", language="python")
        from src.quality.yeyo_quality import QualityCheck
        report.checks = [QualityCheck(name="t1", passed=True, score=0.9)]
        report.calculate_score()
        assert report.feedback_action == "positive"

        report2 = QualityReport(code_id="test2", language="python")
        report2.checks = [QualityCheck(name="t1", passed=False, score=0.3)]
        report2.calculate_score()
        assert report2.feedback_action == "negative"


# ═══════════════════════════════════
# YeyoLint (6.14)
# ═══════════════════════════════════

class TestYeyoLint:
    def test_clean_code_passes(self):
        linter = YeyoLint()
        result = linter.lint("def hello():\n    return 'world'\n")
        assert result.passed
        assert result.critical_count == 0

    def test_hardcoded_password_detected(self):
        linter = YeyoLint()
        result = linter.lint('password = "secret123"')
        assert not result.passed
        assert result.critical_count > 0
        assert any(i.rule == "no_passwords_in_code" for i in result.issues)

    def test_hardcoded_secret_detected(self):
        linter = YeyoLint()
        result = linter.lint('secret = "my_api_key"')
        assert not result.passed

    def test_syntax_error_detected(self):
        linter = YeyoLint()
        result = linter.lint("def foo(:")
        assert not result.passed

    def test_warning_bare_except(self):
        linter = YeyoLint()
        result = linter.lint("try:\n    pass\nexcept:\n    pass\n")
        assert result.passed  # warnings don't fail
        assert result.warning_count > 0

    def test_should_regenerate(self):
        linter = YeyoLint()
        result = linter.lint('password = "secret"')
        assert linter.should_regenerate(result)
        result2 = linter.lint("x = 1")
        assert not linter.should_regenerate(result2)


# ═══════════════════════════════════
# YeyoBenchmark (6.15)
# ═══════════════════════════════════

class TestYeyoBenchmark:
    def test_problems_loaded(self):
        bench = YeyoBenchmark()
        assert len(bench.get_problems()) >= 10

    def test_evaluate_good_response(self):
        bench = YeyoBenchmark()
        problem = BenchmarkProblem(
            id="test-1", category=ProblemCategory.PYTHON, difficulty="easy",
            prompt="Reverse string", expected_keywords=["def", "return", "[::-1]"],
        )
        result = bench.evaluate_response(problem, "def reverse(s):\n    return s[::-1]")
        assert result.passed
        assert result.score >= 0.6

    def test_evaluate_empty_response(self):
        bench = YeyoBenchmark()
        problem = BENCHMARK_PROBLEMS[0]
        result = bench.evaluate_response(problem, "")
        assert not result.passed
        assert result.score == 0.0

    def test_degradation_detection(self):
        bench = YeyoBenchmark()
        prev_run = BenchmarkRun(run_id="prev", overall_score=0.85)
        bench.add_to_history(prev_run)
        current = BenchmarkRun(run_id="current", overall_score=0.70)
        degradation = bench.compare_with_previous(current)
        assert degradation > 5.0  # Should detect significant degradation

    def test_no_degradation_first_run(self):
        bench = YeyoBenchmark()
        current = BenchmarkRun(run_id="first", overall_score=0.80)
        assert bench.compare_with_previous(current) == 0.0


# ═══════════════════════════════════
# YeyoMergeGuard (6.16)
# ═══════════════════════════════════

class TestMergeGuard:
    def test_accept_no_degradation(self):
        guard = YeyoMergeGuard()
        payload = LearningPayload(nodo_id="friend-1", content={"skill": "python"})
        result = guard.evaluate(payload, baseline_score=0.85, after_score=0.85)
        assert result.decision == MergeDecision.ACCEPT

    def test_quarantine_small_degradation(self):
        guard = YeyoMergeGuard()
        payload = LearningPayload(nodo_id="friend-2", content={"skill": "sql"})
        result = guard.evaluate(payload, baseline_score=0.85, after_score=0.84)
        assert result.decision == MergeDecision.QUARANTINE

    def test_reject_large_degradation(self):
        guard = YeyoMergeGuard()
        payload = LearningPayload(nodo_id="friend-3", content={"skill": "bad"})
        result = guard.evaluate(payload, baseline_score=0.85, after_score=0.75)
        assert result.decision == MergeDecision.REJECT

    def test_suspend_after_consecutive_rejections(self):
        guard = YeyoMergeGuard()
        for i in range(4):
            payload = LearningPayload(nodo_id="bad-node", content={"attempt": i})
            guard.evaluate(payload, baseline_score=0.85, after_score=0.5)
        assert guard.is_node_suspended("bad-node")

    def test_not_suspended_initially(self):
        guard = YeyoMergeGuard()
        assert not guard.is_node_suspended("new-node")

    def test_trust_record_tracking(self):
        guard = YeyoMergeGuard()
        payload = LearningPayload(nodo_id="node-1", content={})
        guard.evaluate(payload, 0.85, 0.85)
        guard.evaluate(payload, 0.85, 0.84)
        trust = guard.get_trust_record("node-1")
        assert trust is not None
        assert trust.total_submissions == 2
        assert trust.accepted == 1
        assert trust.quarantined == 1
