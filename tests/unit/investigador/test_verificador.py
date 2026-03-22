"""
Tests unitarios para Verificador.
Micro-fase 5.28 — 8 tests (uno por nivel + combinaciones).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.investigador.verificador import Verificador
from src.investigador.modelos import (
    LintResult,
    StressResult,
    TestResult,
    VerificacionCompleta,
)


@pytest.fixture
def verificador():
    return Verificador(timeout_ejecucion=10.0, timeout_tests=10.0)


@pytest.mark.asyncio
async def test_nivel_1_codigo_valido(verificador):
    resultado = await verificador.ejecutar_codigo("x = 1 + 1\nprint(x)", "python")
    assert resultado is True


@pytest.mark.asyncio
async def test_nivel_1_codigo_invalido(verificador):
    resultado = await verificador.ejecutar_codigo("def (invalid syntax", "python")
    assert resultado is False


@pytest.mark.asyncio
async def test_nivel_2_tests_pasan(verificador):
    codigo = "def suma(a, b): return a + b"
    tests = "def test_suma():\n    assert suma(2, 3) == 5"
    resultado = await verificador.correr_tests(codigo, tests)
    assert isinstance(resultado, TestResult)
    assert resultado.passed is True


@pytest.mark.asyncio
async def test_nivel_3_lint_limpio(verificador):
    codigo = "x = 1\ny = 2\nprint(x + y)"
    resultado = await verificador.analisis_estatico(codigo, "python")
    assert isinstance(resultado, LintResult)
    assert resultado.passed is True
    assert resultado.errors == 0


@pytest.mark.asyncio
async def test_nivel_3_lint_detecta_eval(verificador):
    codigo = "resultado = eval(input())"
    resultado = await verificador.analisis_estatico(codigo, "python")
    assert resultado.errors > 0
    assert resultado.passed is False


@pytest.mark.asyncio
async def test_nivel_4_similitud(verificador):
    original = "def hello(): return 'world'"
    adaptado = "def hello(): return 'mundo'"
    score = await verificador.comparar_con_fuente(adaptado, original)
    assert 0.0 <= score <= 1.0


@pytest.mark.asyncio
async def test_nivel_5_stress_sin_docker(verificador):
    resultado = await verificador.stress_test_docker("x = 1", {"iteraciones": 10})
    assert isinstance(resultado, StressResult)


@pytest.mark.asyncio
async def test_calcular_confianza_todos_pasan(verificador):
    resultado = VerificacionCompleta(
        nivel_1_ejecucion=True,
        nivel_2_tests=TestResult(passed=True, total=5),
        nivel_3_lint=LintResult(passed=True),
        nivel_4_similitud=0.85,
        nivel_5_stress=StressResult(passed=True),
    )
    confianza = verificador.calcular_confianza(resultado)
    assert confianza > 0.8
