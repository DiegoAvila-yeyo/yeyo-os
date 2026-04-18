"""
YeyoOS — ConversationAgent
Micro-fase 3.2.7 — Agente para gestión conversacional multi-turno

Maneja:
- Continuidad de contexto
- Recolección de información
- Clarificación de intenciones
- Seguimiento de estado
- Generación de respuestas naturales
"""

from src.agents.base import Agent, AgentInput, AgentOutput
from typing import Any, Dict, List


class ConversationAgent(Agent):
    """Agente especializado en conversaciones multi-turno."""
    
    def __init__(self):
        super().__init__(
            name="ConversationAgent",
            domain="conversation"
        )
        
        self.conversation_states = {
            "greeting": "Saludar e identificar intención",
            "clarifying": "Hacer preguntas para clarificar",
            "gathering": "Recolectar información necesaria",
            "responding": "Responder a solicitud",
            "confirming": "Confirmar comprensión",
            "closing": "Cerrar conversación",
        }
    
    def get_system_prompt(self, context: Dict[str, Any]) -> str:
        """Retorna prompt del sistema especializado en conversaciones multi-turno."""
        conversation_type = context.get("type", "general")
        tone = context.get("tone", "professional")
        history_length = context.get("history_length", 0)
        
        return f"""Eres YeyoOS, un asistente de IA útil, directo y amigable ({tone}).

Mantén conversaciones naturales y coherentes. Tipo de conversación: {conversation_type}. Turnos previos: {history_length}.

REGLAS:
- Responde directamente sin usar etiquetas ni encabezados internos (NO uses "ESTADO:", "ANÁLISIS:", etc.)
- Sé conciso: 1-3 párrafos máximo
- Mantén coherencia con el historial previo
- Adapta el tono a: {tone}
- Siempre ofrece ayuda o una pregunta de seguimiento relevante

Para {conversation_type}:
- Support: Resuelve el problema paso a paso
- Info: Datos precisos y útiles
- Sales: Identifica necesidad y propón solución
- Coaching: Preguntas reflexivas y motivación
- Debug: Diagnóstico sistemático
- General: Conversación natural y útil

Responde en el mismo idioma que el usuario."""
    
    def validate_input(self, agent_input: AgentInput) -> tuple[bool, str]:
        """Valida que sea mensaje conversacional."""
        content = agent_input.content.lower()
        
        if len(content) < 5:
            return False, "Mensaje muy corto"
        
        # Debe tener algún contenido sustancial
        if len(content) < 10 and not any(c in content for c in "?!"):
            return False, "Mensaje incompleto o sin intención clara"
        
        return True, ""
    
    def validate_output(self, response: str) -> tuple[bool, str]:
        """Valida que sea respuesta conversacional."""
        if not response or len(response.strip()) < 10:
            return False, "Respuesta muy corta"
        
        # Must have some actual content lines
        if len([line for line in response.split('\n') if line.strip()]) < 1:
            return False, "Respuesta sin contenido"
        
        return True, ""
    
    def calculate_confidence(self, response: str, input_context: Dict[str, Any]) -> float:
        """Calcula confianza en la respuesta."""
        base_conf = 0.70
        
        # Estructura conversacional visible
        if "ESTADO" in response or "ANÁLISIS" in response:
            base_conf += 0.12
        
        # Presencia de próximo paso (mejorado: sin redundancia)
        if "próximo" in response.lower():
            base_conf += 0.08
        
        # Confirmación presente
        if "confirma" in response.lower() or "¿entendiste" in response.lower():
            base_conf += 0.05
        
        # Longitud apropiada (no demasiado corto, no demasiado largo)
        if 100 < len(response) < 800:
            base_conf += 0.05
        
        return min(1.0, base_conf)
    
    def suggest_improvements(self, response: str, input_context: Dict[str, Any]) -> List[str]:
        """Sugiere mejoras a la respuesta."""
        suggestions = []
        
        if "PRÓXIMO PASO" not in response and "PRÓXIMO" not in response:
            suggestions.append("Especifica claramente cuál es el próximo paso")
        
        if len([line for line in response.split('\n') if line.strip()]) < 3:
            suggestions.append("Expande la respuesta con más detalles o ejemplos")
        
        if "?" not in response:
            suggestions.append("Incluye pregunta de confirmación al final")
        
        if len(response) > 1000:
            suggestions.append("Condensa la respuesta (menos de 800 caracteres)")
        
        return suggestions if suggestions else ["Respuesta conversacional clara y completa"]
