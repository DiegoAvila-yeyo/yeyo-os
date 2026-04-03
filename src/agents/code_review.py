"""
YeyoOS — CodeReviewAgent
Micro-fase 3.2.1 — Agente para revisión de código

Valida y mejora código generado. Chequea:
- Sintaxis correcta
- Tipo hints presentes
- Docstrings en español
- Seguridad (no eval, exec, etc)
- Legibilidad
"""

from src.agents.base import Agent, AgentInput, AgentOutput
from typing import Any, Dict, List
import re


class CodeReviewAgent(Agent):
    """Agente especializado en revisión de código."""
    
    def __init__(self):
        super().__init__(
            name="CodeReviewAgent",
            domain="code_review"
        )
        
        # Patrones de seguridad peligrosos (regex consistente)
        self.dangerous_patterns = [
            r"eval\s*\(",
            r"exec\s*\(",
            r"__import__\s*\(",
            r"subprocess\.call\s*\(",  # Consistente: con \s*
            r"os\.system\s*\(",
            r"pickle\.loads?\s*\(",
        ]
    
    def get_system_prompt(self, context: Dict[str, Any]) -> str:
        """Retorna prompt del sistema especializado en revisión de código."""
        lenguaje = context.get("lenguaje", "python")
        
        return f"""Eres un experto revisor de código {lenguaje}.

Tu tarea es analizar código y proporcionar feedback de calidad.

CHECKLIST DE REVISIÓN:
1. ✓ Sintaxis correcta
2. ✓ Type hints presentes (Python) o tipos explícitos
3. ✓ Docstrings en español (si aplica)
4. ✓ Sin patrones de seguridad peligrosos (eval, exec, etc)
5. ✓ Variables con nombres descriptivos
6. ✓ Funciones con responsabilidad única
7. ✓ Manejo de errores apropiado
8. ✓ Comentarios útiles (no obvios)

FORMATO DE RESPUESTA:
- ESTADO: [CORRECTO/PROBLEMAS]
- PUNTUACIÓN: [0-10]
- PROBLEMAS ENCONTRADOS:
  - [Problema 1]: [Cómo arreglarlo]
  - ...
- MEJORAS SUGERIDAS:
  - [Sugerencia 1]
  - ...

Sé específico y constructivo. Prioriza seguridad y legibilidad."""
    
    def validate_input(self, agent_input: AgentInput) -> tuple[bool, str]:
        """Valida que el código sea razonable."""
        if not agent_input.content or len(agent_input.content.strip()) < 5:
            return False, "Código muy corto (< 5 chars)"
        
        if "```" in agent_input.content:
            # OK, tiene code fences
            pass
        elif len(agent_input.content) < 20:
            return False, "Posible no-código o snippet muy pequeño"
        
        return True, ""
    
    def validate_output(self, response: str) -> tuple[bool, str]:
        """Valida que la revisión sea completa."""
        if not response or len(response.strip()) < 20:
            return False, "Revisión muy corta (menos de 20 caracteres)"
        
        # Chequea que tiene estructura mínima
        has_status = "ESTADO" in response or "estado" in response
        # Regex específico para puntuación: 0-10, [0/10], etc.
        has_score = "PUNTUACIÓN" in response or "puntuación" in response or bool(re.search(r'\b\d+\s*[/-]\s*10\b|\[\d+/10\]|\d+%', response))
        
        if not (has_status or has_score):
            return False, "Formato incompleto (falta ESTADO y/o PUNTUACIÓN)"
        
        return True, ""
    
    def calculate_confidence(self, response: str, input_context: Dict[str, Any]) -> float:
        """Calcula confianza en la revisión."""
        base_conf = 0.6
        
        # Presencia de estructura
        if "PROBLEMAS" in response:
            base_conf += 0.15
        if "MEJORAS" in response or "SUGERENCIAS" in response:
            base_conf += 0.15
        
        # Presencia de número/score con validación mejorada
        if re.search(r'\b\d+\s*[/-]\s*10\b|\[\d+/10\]', response):
            base_conf += 0.1
        
        return min(1.0, base_conf)
    
    def suggest_improvements(self, response: str, input_context: Dict[str, Any]) -> List[str]:
        """Sugiere mejoras a la propia revisión."""
        suggestions = []
        
        if "CÓDIGO CORRECTO" in response.upper() and "PROBLEMAS" not in response.upper():
            suggestions.append("Si el código es correcto, aún proporciona sugerencias de mejora")
        
        if len(response) < 50:
            suggestions.append("Revisión muy breve, proporciona más detalle")
        
        if not re.search(r'\b\d+\s*[/-]\s*10\b|\[\d+/10\]', response):
            suggestions.append("Incluye puntuación explícita del código (ej: 7/10)")
        
        if "MEJORAS" not in response.upper() and len(response) < 300:
            suggestions.append("Agrega sugerencias específicas para mejorar el código")
        
        return suggestions if suggestions else ["Revisión completa y bien estructurada"]
