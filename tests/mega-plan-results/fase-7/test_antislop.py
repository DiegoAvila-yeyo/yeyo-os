"""
Phase 7 — Anti-IA Slop Testing
Tests the 16-gate Workshop pipeline with 10 cases.
Verifies gate LOGIC, not AI quality (works without Ollama).
"""
import pytest
import ast
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from dataclasses import asdict

# Import pipeline components
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.workshop.pipeline import (
    WorkshopPipeline, MissionSpec, GateResult, GATE_DEFINITIONS
)


# ── Helpers ──────────────────────────────────────────────────────────

def _pipeline() -> WorkshopPipeline:
    """Create a pipeline with no external dependencies."""
    return WorkshopPipeline(ia_provider=None, pool=None, ws_manager=None)


def _valid_spec(**overrides) -> MissionSpec:
    """Return a minimal valid MissionSpec."""
    defaults = dict(
        inputs=[{"name": "arr", "type": "list[int]"}],
        outputs=[{"name": "sorted_arr", "type": "list[int]"}],
        edge_cases=["empty list", "single element", "duplicates"],
        error_handling=["invalid type raises TypeError"],
        constraints=["O(n log n) average case"],
        acceptance_criteria=["Returns sorted list", "Handles edge cases"],
    )
    defaults.update(overrides)
    return MissionSpec(**defaults)


# ── Case 1: Simple sort function ────────────────────────────────────

@pytest.mark.asyncio
async def test_case1_simple_sort():
    """Sort function: valid spec + clean code should pass structural gates."""
    spec = _valid_spec()
    pipeline = _pipeline()

    # Gate 0: Spec-First should pass
    result = await pipeline._gate_spec_first(spec)
    assert result.status == "passed", f"Spec-First should pass: {result.output}"

    # Gate 3: AST Parse with valid code
    code = (
        "def sort_list(arr: list[int]) -> list[int]:\n"
        "    if not arr:\n"
        "        return []\n"
        "    return sorted(arr)\n"
    )
    result = await pipeline._gate_ast_parse(code)
    assert result.status == "passed", f"AST should pass: {result.output}"
    assert "1 functions" in result.output


# ── Case 2: Function with side effects ──────────────────────────────

@pytest.mark.asyncio
async def test_case2_side_effects():
    """File I/O function needs error handling in spec."""
    spec = MissionSpec(
        inputs=[{"name": "filepath", "type": "str"}],
        outputs=[{"name": "content", "type": "str"}],
        edge_cases=["file not found", "permission denied"],
        error_handling=["FileNotFoundError", "PermissionError"],
        constraints=[],
        acceptance_criteria=["Read file content safely"],
    )
    pipeline = _pipeline()
    result = await pipeline._gate_spec_first(spec)
    assert result.status == "passed"
    assert "1 inputs" in result.output
    assert "1 criteria" in result.output


# ── Case 3: Syntax error in binary search ────────────────────────────

@pytest.mark.asyncio
async def test_case3_syntax_error():
    """Intentionally bad code should fail AST parse."""
    bad_code = (
        "def binary_search(arr, target)  # Missing colon\n"
        "    left, right = 0, len(arr) - 1\n"
        "    while left <= right\n"
        "        mid = (left + right) // 2\n"
    )
    pipeline = _pipeline()
    result = await pipeline._gate_ast_parse(bad_code)
    assert result.status == "failed", "Syntax error should fail AST gate"
    assert "SyntaxError" in result.output


# ── Case 4: Empty spec must block ────────────────────────────────────

@pytest.mark.asyncio
async def test_case4_no_spec_blocks():
    """Empty spec should be rejected by Spec-First gate."""
    empty_spec = MissionSpec()
    pipeline = _pipeline()
    result = await pipeline._gate_spec_first(empty_spec)
    assert result.status == "failed", "Empty spec must be rejected"
    assert "inputs" in result.output
    assert "outputs" in result.output
    assert "acceptance_criteria" in result.output


# ── Case 5: Trivial tests detected ──────────────────────────────────

@pytest.mark.asyncio
async def test_case5_trivial_tests():
    """Tests with only 'assert True' are syntactically valid but trivial."""
    trivial_test = (
        "def test_it_works():\n"
        "    assert True\n"
        "\n"
        "def test_it_really_works():\n"
        "    assert True\n"
    )
    pipeline = _pipeline()
    # AST parse accepts valid syntax even if tests are trivial
    result = await pipeline._gate_ast_parse(trivial_test)
    assert result.status == "passed", "Syntactically valid but trivial tests pass AST"
    assert "2 functions" in result.output


# ── Case 6: Security — dangerous patterns ────────────────────────────

@pytest.mark.asyncio
async def test_case6_security_patterns():
    """Code using eval() should be flagged by static security patterns."""
    vulnerable_code = (
        "def run_user_command(cmd):\n"
        "    return eval(cmd)\n"
    )
    pipeline = _pipeline()

    # AST parses fine (it's valid Python)
    result = await pipeline._gate_ast_parse(vulnerable_code)
    assert result.status == "passed", "Valid Python despite being insecure"

    # Security gate static regex should catch eval()
    result = await pipeline._gate_security(vulnerable_code)
    assert result.status == "failed", "eval() should trigger security failure"
    assert "eval()" in result.output or "code injection" in result.output.lower()


# ── Case 7: O(n²) nested loops ──────────────────────────────────────

@pytest.mark.asyncio
async def test_case7_slow_code():
    """O(n²) bubble sort should be parseable."""
    slow_code = (
        "def bubble_sort(arr):\n"
        "    n = len(arr)\n"
        "    for i in range(n):\n"
        "        for j in range(0, n-i-1):\n"
        "            if arr[j] > arr[j+1]:\n"
        "                arr[j], arr[j+1] = arr[j+1], arr[j]\n"
        "    return arr\n"
    )
    pipeline = _pipeline()
    result = await pipeline._gate_ast_parse(slow_code)
    assert result.status == "passed", "Valid syntax"
    assert "1 functions" in result.output

    # Performance gate detects nested loops via AST
    result = await pipeline._gate_performance(slow_code)
    assert "Nested loop" in result.output or "O(n²)" in result.output


# ── Case 8: Compiles but logically wrong ─────────────────────────────

@pytest.mark.asyncio
async def test_case8_compiles_but_wrong():
    """Code that parses but has logical errors passes AST gate."""
    wrong_code = (
        "def add(a, b):\n"
        "    return a - b  # Wrong: subtracts instead of adds\n"
    )
    pipeline = _pipeline()
    result = await pipeline._gate_ast_parse(wrong_code)
    assert result.status == "passed", "Syntactically valid"
    assert "1 functions" in result.output


# ── Case 9: Code without type annotations ────────────────────────────

@pytest.mark.asyncio
async def test_case9_no_types():
    """Code without type annotations still passes AST parse."""
    untyped_code = (
        "def process(data):\n"
        "    result = []\n"
        "    for item in data:\n"
        "        result.append(item * 2)\n"
        "    return result\n"
    )
    pipeline = _pipeline()
    result = await pipeline._gate_ast_parse(untyped_code)
    assert result.status == "passed"
    assert "1 functions" in result.output


# ── Case 10: Full pipeline structure ─────────────────────────────────

@pytest.mark.asyncio
async def test_case10_pipeline_structure():
    """Verify all 17 gates are defined and pipeline structure is correct."""
    # 17 gates numbered 0-16
    assert len(GATE_DEFINITIONS) == 17
    gate_numbers = [g[0] for g in GATE_DEFINITIONS]
    assert gate_numbers == list(range(17))

    # Verify key gate names exist
    gate_names = [g[1] for g in GATE_DEFINITIONS]
    assert "Spec-First" in gate_names
    assert "AST Parse" in gate_names
    assert "Human Checkpoint" in gate_names
    assert "Contract Testing" in gate_names
    assert "Security Scan" in gate_names
    assert "Mutation Testing" in gate_names

    # Verify pipeline has all expected gate methods
    pipeline = _pipeline()
    assert hasattr(pipeline, "_gate_spec_first")
    assert hasattr(pipeline, "_gate_ast_parse")
    assert hasattr(pipeline, "_gate_security")
    assert hasattr(pipeline, "_gate_contract")
    assert hasattr(pipeline, "_gate_performance")
    assert hasattr(pipeline, "execute")

    # GateResult dataclass fields
    gr = GateResult(gate_number=0, gate_name="test", status="passed", output="ok")
    d = asdict(gr)
    assert set(d.keys()) == {"gate_number", "gate_name", "status", "output", "duration_ms", "attempts"}

    # MissionSpec defaults to empty lists
    ms = MissionSpec()
    assert ms.inputs == []
    assert ms.outputs == []
    assert ms.acceptance_criteria == []
