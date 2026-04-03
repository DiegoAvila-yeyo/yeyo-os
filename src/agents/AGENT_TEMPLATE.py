"""
YeyoOS — Agent Template (Phase 3+)
Usar como base para nuevos agentes - SIGUE QUALITY STANDARDS

Reemplaza:
  {AgentName} → Tu nombre de agente (ej: TranscriptAgent)
  {agent_name} → Slug lowercase (ej: transcript_agent)
  {domain} → Dominio (ej: transcription)
  {base_conf} → Confianza base (0.60-0.70)
"""

import re
from typing import Any, Dict, List

from src.agents.base import Agent, AgentInput


class {AgentName}Agent(Agent):
    """Agente especializado en {descripción breve}."""
    
    def __init__(self):
        super().__init__(
            name="{AgentName}Agent",
            domain="{domain}"
        )
        # Inicializa datos específicos del dominio
        self.domain_config = {
            "key": "value",
        }
    
    def get_system_prompt(self, context: Dict[str, Any]) -> str:
        """Retorna prompt del sistema especializado para el dominio."""
        # Obtén parámetros del contexto de forma segura
        param1 = context.get("param1", "default_value")
        param2 = context.get("param2", "default_value")
        
        return f"""Eres un experto en {domain}.

Tu objetivo es [objetivo específico].

CONTEXTO:
- Parámetro 1: {param1}
- Parámetro 2: {param2}

CRITERIOS A EVALUAR:
1. [Criterio 1]: [Descripción]
2. [Criterio 2]: [Descripción]

FORMATO DE RESPUESTA:
- SECCIÓN 1: [Instrucciones]
  * Punto 1
  * Punto 2
- SECCIÓN 2: [Instrucciones]

Sé específico y actionable."""
    
    def validate_input(self, agent_input: AgentInput) -> tuple[bool, str]:
        """Valida que input sea válido para este dominio.
        
        Returns:
            tuple[bool, str]: (válido, mensaje_error)
        """
        content = agent_input.content.lower()
        
        # Verificación 1: Longitud mínima
        if not content or len(content.strip()) < 20:
            return False, "Entrada muy corta (mínimo 20 caracteres)"
        
        # Verificación 2: Contiene palabras clave del dominio
        required_keywords = ["keyword1", "keyword2"]
        if not any(kw in content for kw in required_keywords):
            return False, "Falta contexto del dominio (menciona palabras clave específicas)"
        
        # Verificación 3: No contiene patrones peligrosos
        if any(pattern in content for pattern in ["__", "eval(", "exec("]):
            return False, "Entrada contiene patrones sospechosos"
        
        return True, ""
    
    def validate_output(self, response: str) -> tuple[bool, str]:
        """Valida que output cumpla con formato y contenido esperado.
        
        Returns:
            tuple[bool, str]: (válido, mensaje_error)
        """
        # Verificación 1: Longitud mínima
        if not response or len(response.strip()) < 80:
            return False, "Respuesta muy corta (mínimo 80 caracteres)"
        
        # Verificación 2: Tiene secciones requeridas (ESPECÍFICO, NO genérico)
        required_sections = ["SECCIÓN1", "SECCIÓN2"]
        missing_sections = [s for s in required_sections if s not in response]
        if missing_sections:
            return False, f"Faltan secciones: {', '.join(missing_sections)}"
        
        # Verificación 3: Contiene evaluación/análisis (usar REGEX específico)
        # ❌ NO: any(c.isdigit() for c in response[:100])
        # ✅ SÍ: re.search(patrón específico)
        has_evaluation = bool(re.search(
            r'\b\d+\s*[/-]\s*10\b|\[\d+/10\]|\d+%|bueno|malo|excelente',
            response,
            re.IGNORECASE
        ))
        if not has_evaluation:
            return False, "Falta evaluación/análisis cuantitativo"
        
        return True, ""
    
    def calculate_confidence(self, response: str, input_context: Dict[str, Any]) -> float:
        """Calcula confianza [0.0-1.0] en la calidad de la respuesta.
        
        Returns:
            float: Confianza entre 0.0 y 1.0
        """
        base_conf = 0.65  # Línea base para este dominio
        
        # Bonus 1: Tiene secciones estructuradas
        sections_found = sum(1 for s in ["SECCIÓN1", "SECCIÓN2"] if s in response)
        base_conf += (sections_found / 2) * 0.15  # Máx +0.15
        
        # Bonus 2: Contiene análisis específico (REGEX, no genérico)
        if re.search(r'\b\d+\s*[/-]\s*10\b|\d+%', response):
            base_conf += 0.1
        
        # Bonus 3: Tiene sugerencias/recomendaciones
        if "recomendación" in response.lower() or "sugerencia" in response.lower():
            base_conf += 0.08
        
        # Clamp a [0.0, 1.0]
        return min(1.0, base_conf)
    
    def suggest_improvements(self, response: str, input_context: Dict[str, Any]) -> List[str]:
        """Sugiere mejoras al análisis realizado.
        
        Returns:
            List[str]: Lista de sugerencias específicas
        """
        suggestions = []
        
        # Sugerencia 1: Si falta sección crítica
        if "SECCIÓN1" not in response:
            suggestions.append("Incluye SECCIÓN1 con [qué debe contener]")
        
        # Sugerencia 2: Si falta análisis cuantitativo
        if not re.search(r'\d+%|\d+/10', response):
            suggestions.append("Proporciona métricas cuantitativas (% o puntuación)")
        
        # Sugerencia 3: Si es muy corto
        if len(response) < 200:
            suggestions.append("Expande con más detalles y ejemplos específicos")
        
        # Sugerencia 4: Si falta contexto
        if "contexto" not in response.lower() and "ejemplo" not in response.lower():
            suggestions.append("Incluye ejemplos concretos o contextualización")
        
        return suggestions


# ====================================================
# PRUEBAS UNITARIAS - Crear archivo tests/agents/test_{agent_name}.py
# ====================================================

if __name__ == "__main__":
    """Tests básicos para desarrollo - luego mover a pytest"""
    agent = {AgentName}Agent()
    
    print("✓ Agent initialized")
    
    # Test validate_input
    valid_input = AgentInput(content="entrada válida con keyword1 y keyword2")
    result, msg = agent.validate_input(valid_input)
    assert result is True, f"Input validation failed: {msg}"
    print("✓ Valid input accepted")
    
    invalid_input = AgentInput(content="corta")
    result, msg = agent.validate_input(invalid_input)
    assert result is False, "Short input should be rejected"
    print("✓ Short input rejected")
    
    # Test validate_output
    valid_output = "SECCIÓN1: contenido\nSECCIÓN2: análisis\nPuntuación: 8/10"
    result, msg = agent.validate_output(valid_output)
    assert result is True, f"Output validation failed: {msg}"
    print("✓ Valid output accepted")
    
    invalid_output = "muy corta"
    result, msg = agent.validate_output(invalid_output)
    assert result is False, "Short output should be rejected"
    print("✓ Short output rejected")
    
    # Test confidence scoring
    conf = agent.calculate_confidence(valid_output, {})
    assert 0.0 <= conf <= 1.0, f"Confidence out of range: {conf}"
    print(f"✓ Confidence scoring OK: {conf:.2f}")
    
    # Test suggestions
    suggestions = agent.suggest_improvements(valid_output, {})
    assert isinstance(suggestions, list), "Should return List[str]"
    print(f"✓ Suggestions: {len(suggestions)} items")
    
    print("\n✅ All basic tests passed!")
