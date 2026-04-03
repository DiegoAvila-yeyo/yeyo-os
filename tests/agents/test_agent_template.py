"""
Test Template para Agentes Phase 3+
Archivo: tests/agents/test_{agent_name}.py

Copia y adapta para cada nuevo agente
"""

import pytest
from src.agents.{agent_name} import {AgentName}Agent
from src.agents.base import AgentInput


@pytest.fixture
def agent():
    """Fixture que proporciona instancia del agente."""
    return {AgentName}Agent()


@pytest.fixture
def valid_input():
    """Input válido para este dominio."""
    return AgentInput(
        content="Contenido válido con keywords específicas del dominio",
        context={"domain_param": "value"}
    )


@pytest.fixture
def invalid_inputs():
    """Ejemplos de inputs inválidos."""
    return [
        (AgentInput(content="corta"), "muy corta"),
        (AgentInput(content="contenido sin keywords"), "falta contexto"),
        (AgentInput(content=""), "vacía"),
    ]


# ============================================================
# TESTS: validate_input()
# ============================================================

class TestValidateInput:
    """Suite de tests para validación de entrada."""
    
    def test_valid_input_accepted(self, agent, valid_input):
        """Debe aceptar entrada válida."""
        result, msg = agent.validate_input(valid_input)
        assert result is True, f"Valid input rejected with: {msg}"
        assert msg == "", "Error message should be empty for valid input"
    
    def test_empty_input_rejected(self, agent):
        """Debe rechazar entrada vacía."""
        result, msg = agent.validate_input(AgentInput(content=""))
        assert result is False, "Empty input should be rejected"
        assert len(msg) > 0, "Should provide error message"
    
    def test_too_short_rejected(self, agent):
        """Debe rechazar entrada muy corta."""
        result, msg = agent.validate_input(AgentInput(content="muy corta"))
        assert result is False, "Short input should be rejected"
        assert "corta" in msg.lower(), "Error message should mention length"
    
    def test_missing_domain_keywords_rejected(self, agent):
        """Debe rechazar entrada sin palabras clave del dominio."""
        result, msg = agent.validate_input(AgentInput(content="texto genérico sin contexto"))
        assert result is False, "Input missing domain keywords should be rejected"
        assert "contexto" in msg.lower() or "keyword" in msg.lower()
    
    def test_returns_tuple_bool_str(self, agent, valid_input):
        """Siempre retorna tuple[bool, str]."""
        result = agent.validate_input(valid_input)
        assert isinstance(result, tuple), "Should return tuple"
        assert len(result) == 2, "Tuple should have 2 elements"
        assert isinstance(result[0], bool), "First element should be bool"
        assert isinstance(result[1], str), "Second element should be str"


# ============================================================
# TESTS: validate_output()
# ============================================================

class TestValidateOutput:
    """Suite de tests para validación de salida."""
    
    def test_valid_output_accepted(self, agent):
        """Debe aceptar salida válida."""
        valid_response = (
            "SECCIÓN1: Contenido detallado\n"
            "SECCIÓN2: Análisis y evaluación\n"
            "Puntuación: 8/10 - Excelente"
        )
        result, msg = agent.validate_output(valid_response)
        assert result is True, f"Valid output rejected with: {msg}"
        assert msg == "", "Error message should be empty"
    
    def test_too_short_rejected(self, agent):
        """Debe rechazar respuesta muy corta."""
        result, msg = agent.validate_output("muy corta")
        assert result is False, "Short output should be rejected"
        assert "corta" in msg.lower() or "mínimo" in msg.lower()
    
    def test_empty_rejected(self, agent):
        """Debe rechazar respuesta vacía."""
        result, msg = agent.validate_output("")
        assert result is False, "Empty response should be rejected"
    
    def test_returns_tuple_bool_str(self, agent):
        """Siempre retorna tuple[bool, str]."""
        result = agent.validate_output("respuesta")
        assert isinstance(result, tuple), "Should return tuple"
        assert len(result) == 2, "Tuple should have 2 elements"
        assert isinstance(result[0], bool), "First element should be bool"
        assert isinstance(result[1], str), "Second element should be str"


# ============================================================
# TESTS: calculate_confidence()
# ============================================================

class TestCalculateConfidence:
    """Suite de tests para cálculo de confianza."""
    
    def test_confidence_in_valid_range(self, agent):
        """Confianza siempre entre 0.0 y 1.0."""
        test_responses = [
            "corta",
            "respuesta normal de longitud media",
            "SECCIÓN1: mucho contenido " * 20,
        ]
        for response in test_responses:
            conf = agent.calculate_confidence(response, {})
            assert isinstance(conf, float), "Confidence should be float"
            assert 0.0 <= conf <= 1.0, f"Confidence {conf} out of range"
    
    def test_confidence_increases_with_quality(self, agent):
        """Confianza debería aumentar con mejor respuesta."""
        poor_response = "algo corto"
        good_response = "SECCIÓN1: Contenido\nSECCIÓN2: Análisis\nPuntuación: 8/10"
        
        poor_conf = agent.calculate_confidence(poor_response, {})
        good_conf = agent.calculate_confidence(good_response, {})
        
        assert good_conf > poor_conf, "Better response should have higher confidence"
    
    def test_confidence_never_exceeds_one(self, agent):
        """Confianza nunca debe exceder 1.0 incluso con respuesta perfecta."""
        perfect_response = (
            "SECCIÓN1: " + "contenido " * 50 + "\n"
            "SECCIÓN2: " + "análisis " * 50 + "\n"
            "Puntuación: 10/10 ✓ " * 10
        )
        conf = agent.calculate_confidence(perfect_response, {})
        assert conf <= 1.0, f"Confidence {conf} exceeds 1.0!"


# ============================================================
# TESTS: suggest_improvements()
# ============================================================

class TestSuggestImprovements:
    """Suite de tests para sugerencias de mejora."""
    
    def test_returns_list_of_strings(self, agent):
        """Siempre retorna List[str]."""
        suggestions = agent.suggest_improvements("respuesta", {})
        assert isinstance(suggestions, list), "Should return list"
        assert all(isinstance(s, str) for s in suggestions), "All items should be strings"
    
    def test_empty_suggestions_for_perfect_response(self, agent):
        """Respuesta perfecta puede tener pocas sugerencias."""
        perfect_response = (
            "SECCIÓN1: Análisis detallado\n"
            "SECCIÓN2: Conclusiones\n"
            "Recomendación: Hacer X\n"
            "Puntuación: 9/10\n"
        )
        suggestions = agent.suggest_improvements(perfect_response, {})
        assert len(suggestions) <= 3, "Perfect response shouldn't have many suggestions"
    
    def test_suggestions_for_incomplete_response(self, agent):
        """Respuesta incompleta tiene sugerencias útiles."""
        incomplete_response = "algo corto"
        suggestions = agent.suggest_improvements(incomplete_response, {})
        assert len(suggestions) > 0, "Should have suggestions for incomplete response"


# ============================================================
# TESTS: Integration Tests
# ============================================================

class TestIntegration:
    """Tests de integración del flujo completo."""
    
    def test_valid_workflow(self, agent, valid_input):
        """Flujo completo con input válido."""
        is_valid, msg = agent.validate_input(valid_input)
        assert is_valid, f"Valid input rejected: {msg}"
        
        response = (
            "SECCIÓN1: Análisis del problema\n"
            "SECCIÓN2: Recomendaciones\n"
            "Puntuación: 7/10"
        )
        
        is_valid, msg = agent.validate_output(response)
        assert is_valid, f"Valid output rejected: {msg}"
        
        conf = agent.calculate_confidence(response, valid_input.context or {})
        assert 0.0 <= conf <= 1.0, f"Invalid confidence: {conf}"
