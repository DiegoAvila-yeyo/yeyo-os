#!/usr/bin/env python
"""Test Task 4: Evaluador edge cases"""

from src.investigador.modelos import ResultadoBusqueda
from src.investigador.evaluador import EvaluadorCandidatos, SCORE_MINIMO_ACEPTABLE

evaluador = EvaluadorCandidatos()

# Test 1: Empty code (score should be 0)
candidato1 = ResultadoBusqueda(
    fuente="github",
    url="https://example.com",
    codigo="",
    score=0.5,
    metadata={"estrellas": 100}
)

# Test 2: Valid code with good metadata
candidato2 = ResultadoBusqueda(
    fuente="github",
    url="https://example.com",
    codigo="def factorial(n): return n * factorial(n-1) if n > 1 else 1",
    score=0.8,
    metadata={"estrellas": 500, "lenguaje": "python", "actualizado": "2024"}
)

# Test 3: Code with no metadata
candidato3 = ResultadoBusqueda(
    fuente="stackoverflow",
    url="https://example.com",
    codigo="async def fetch(): return requests.get('http://api.com')",
    score=0.5,
    metadata={}
)

resultados = evaluador.evaluar([candidato1, candidato2, candidato3])

print(f"Test 1 (empty code): {resultados[2].score_final} (expect 0.0)")
print(f"Test 2 (good code): {resultados[0].score_final} (expect ~0.8-1.0)")
print(f"Test 3 (no metadata): {resultados[1].score_final} (expect ~0.4-0.6)")
print(f"Score mínimo: {SCORE_MINIMO_ACEPTABLE}")

# Validate
assert resultados[2].score_final == 0.0, f"Empty code should have score 0, got {resultados[2].score_final}"
assert resultados[0].score_final >= 0.7, f"Good code should have score >= 0.7, got {resultados[0].score_final}"
assert 0.3 <= resultados[1].score_final <= 0.7, f"Code with no metadata should have score 0.3-0.7, got {resultados[1].score_final}"

print("✅ All tests passed!")
