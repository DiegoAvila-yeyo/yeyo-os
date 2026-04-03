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
        conversation_type = context.get("type", "general")  # support, info, sales, coaching, debug
        tone = context.get("tone", "professional")  # professional, casual, friendly, formal
        history_length = context.get("history_length", 0)
        
        return f"""Eres especialista en conversaciones naturales y efectivas ({tone}).

Tu tarea es mantener conversación coherente y progresiva para: {conversation_type}.

CONTEXTO:
- Tipo: {conversation_type}
- Tono: {tone}
- Turnos previos: {history_length}

ESTADOS DE CONVERSACIÓN:
1. GREETING (turno 1): Saludo cálido, identifica intención
2. CLARIFYING: Haz preguntas precisas si necesitas más contexto
3. GATHERING: Recolecta info específica (3-5 preguntas máximo)
4. RESPONDING: Responde directo y útil
5. CONFIRMING: Asegúrate que entendió/está satisfecho
6. CLOSING: Resumen y llamado a acción

PRINCIPIOS:
1. CONTEXTO: Mantén coherencia con historia previa
2. CLARIDAD: Explica en máximo 3 párrafos
3. EMPATÍA: Reconoce necesidades del usuario
4. ACCIÓN: Siempre incluye próximo paso
5. BREVEDAD: Sin información irrelevante
6. CONFIRMACIÓN: Verifica comprensión cuando sea complejo

ANTI-PATRONES A EVITAR:
- Ignorar contexto previo
- Hacer demasiadas preguntas (máx 2 por turno)
- Respuestas genéricas
- No reconocer emociones
- Cerrar sin confirmar

FORMATO DE RESPUESTA:
- ESTADO ACTUAL: [Qué estado conversacional es]
- INFORMACIÓN RECOLECTADA: [Resumir datos importantes]
- ANÁLISIS: [Qué entendiste/qué falta]
- RESPUESTA: [1-3 párrafos máximo]
- PRÓXIMO PASO: [Acción específica o pregunta]
- CONFIRMACIÓN: ¿Entendiste? ¿Necesitas clarificación?

Para {conversation_type}: [Instrucciones específicas de dominio]
- Support: Resuelve problema o escala apropiadamente
- Info: Proporciona datos precisos y actualizados
- Sales: Identifica necesidades, propone solución
- Coaching: Hace preguntas reflexivas, motiva
- Debug: Paso a paso, verifica cada solución

Sé conciso pero cálido. Adapta al tono: {tone}."""
    
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
        if not response or len(response.strip()) < 20:
            return False, "Respuesta muy corta (menos de 20 caracteres)"
        
        # Debe tener contenido principal
        if len([line for line in response.split('\n') if line.strip()]) < 2:
            return False, "Respuesta no tiene suficiente contenido"
        
        # Debe tener próximo paso o conclusión (mejorado - palabras más específicas)
        has_closure = any(word in response.lower() for word in ["próximo paso", "siguiente paso", "¿entendiste", "¿preguntas?", "confirma"])
        
        if not has_closure and len(response) < 80:
            return False, "Falta claridad sobre próximo paso: especifica '¿Entendiste?' o 'Próximo paso'"
        
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
