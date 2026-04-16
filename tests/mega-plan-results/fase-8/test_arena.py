"""Phase 8 — Arena Battle System Tests"""
import pytest
from src.arena.battle import (
    BattleEngine, BattleSession, YeyoHack, Guardian, RoundResult,
    ATTACK_TEMPLATES, DETECTION_PATTERNS, DEFENSE_TEMPLATES,
)


class TestBattleStructure:
    def test_attack_templates_exist(self):
        assert len(ATTACK_TEMPLATES) >= 5
        for t in ATTACK_TEMPLATES:
            assert 'type' in t
            assert 'code' in t
            assert t['type'] in ('explore', 'exploit')

    def test_detection_patterns_exist(self):
        assert len(DETECTION_PATTERNS) >= 5
        import re
        for name, pattern in DETECTION_PATTERNS.items():
            re.compile(pattern)  # Verify valid regex

    def test_defense_templates_exist(self):
        assert len(DEFENSE_TEMPLATES) >= 3


class TestYeyoHack:
    @pytest.mark.asyncio
    async def test_generate_attack_without_ollama(self):
        hack = YeyoHack(ia_provider=None)
        code, attack_type, severity = await hack.generate_attack(1)
        assert isinstance(code, str)
        assert len(code) > 0
        assert attack_type in ('explore', 'exploit')
        assert 1 <= severity <= 10

    def test_evolve(self):
        hack = YeyoHack()
        hack.successful_attacks = [{"type": "explore"}, {"type": "exploit"}]
        hack.evolve()
        assert len(hack.learned_combos) == 1

    def test_evolve_no_attacks(self):
        hack = YeyoHack()
        hack.evolve()
        assert len(hack.learned_combos) == 0

    def test_extract_code_python_block(self):
        hack = YeyoHack()
        text = "Here is code:\n```python\nprint('hello')\n```\nDone"
        assert hack._extract_code(text) == "print('hello')"

    def test_extract_code_generic_block(self):
        hack = YeyoHack()
        text = "Code:\n```\nx = 1\n```"
        assert hack._extract_code(text) == "x = 1"

    def test_extract_code_plain(self):
        hack = YeyoHack()
        text = "print('hi')"
        assert hack._extract_code(text) == "print('hi')"


class TestGuardian:
    @pytest.mark.asyncio
    async def test_detect_port_scan(self):
        guardian = Guardian(ia_provider=None)
        code = "import socket\ns = socket.socket()\ns.connect(('127.0.0.1', 80))"
        detected, defense = await guardian.detect_and_defend(code)
        assert detected is True
        assert len(defense) > 0

    @pytest.mark.asyncio
    async def test_detect_env_read(self):
        guardian = Guardian(ia_provider=None)
        code = "import os\nprint(os.environ.get('SECRET'))"
        detected, defense = await guardian.detect_and_defend(code)
        assert detected is True

    @pytest.mark.asyncio
    async def test_detect_subprocess(self):
        guardian = Guardian(ia_provider=None)
        code = "import subprocess\nsubprocess.run(['ls'])"
        detected, defense = await guardian.detect_and_defend(code)
        assert detected is True

    @pytest.mark.asyncio
    async def test_detect_eval(self):
        guardian = Guardian(ia_provider=None)
        code = "eval('1+1')"
        detected, defense = await guardian.detect_and_defend(code)
        assert detected is True

    @pytest.mark.asyncio
    async def test_clean_code_not_detected(self):
        guardian = Guardian(ia_provider=None)
        code = "x = 1 + 2\nprint(x)"
        detected, defense = await guardian.detect_and_defend(code)
        assert detected is False
        assert "No threat detected" in defense


class TestBattleEngine:
    def test_create_session(self):
        engine = BattleEngine()
        session = engine.create_session("test-1", max_rounds=5)
        assert session.id == "test-1"
        assert session.max_rounds == 5
        assert session.status == 'idle'

    def test_pause_resume(self):
        engine = BattleEngine()
        session = engine.create_session("test-2")
        session.status = 'running'
        engine.pause("test-2")
        assert session.status == 'paused'

    def test_stop(self):
        engine = BattleEngine()
        session = engine.create_session("test-3")
        session.status = 'running'
        engine.stop("test-3")
        assert session.status == 'completed'

    def test_stop_nonexistent(self):
        engine = BattleEngine()
        engine.stop("nonexistent")  # Should not raise

    @pytest.mark.asyncio
    async def test_full_battle_without_ollama(self):
        """Run a short battle (5 rounds) with template fallbacks."""
        engine = BattleEngine(ia_provider=None, ws_manager=None)
        session = engine.create_session("battle-e2e", max_rounds=5)
        await engine.start("battle-e2e")

        # Wait for battle to complete
        import asyncio
        for _ in range(50):
            if session.status in ('completed', 'paused'):
                break
            await asyncio.sleep(0.05)

        assert session.current_round >= 1
        assert len(session.rounds) >= 1
        assert session.red_score + session.blue_score == len(session.rounds)
        for r in session.rounds:
            assert r.attack_type in ('explore', 'exploit')
            assert isinstance(r.attack_code, str)
            assert isinstance(r.defense_code, str)


class TestBattleSession:
    def test_initial_state(self):
        session = BattleSession(id="s1", max_rounds=10)
        assert session.red_score == 0
        assert session.blue_score == 0
        assert len(session.rounds) == 0
        assert session.status == 'idle'

    def test_round_result_dataclass(self):
        r = RoundResult(
            round_number=1, attack_type="explore",
            attack_code="print('hi')", defense_code="print('blocked')",
            attack_success=False, defense_success=True,
            severity=3, red_score=0, blue_score=1,
            description="🔵 Defense held!",
        )
        assert r.round_number == 1
        assert r.defense_success is True
