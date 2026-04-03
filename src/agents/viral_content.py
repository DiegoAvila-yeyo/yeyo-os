"""
YeyoOS — ViralContentAgent
Micro-fase 3.2.2 — Agente para análisis de contenido viral

Analiza contenido para maximizar su potencial viral:
- Hook efectivo (primeros 3 segundos)
- Momentum (mantiene atención)
- Call-to-action claro
- Resonancia emocional
- Timing/duración óptima
"""

import re
from src.agents.base import Agent, AgentInput, AgentOutput
from typing import Any, Dict, List


class ViralContentAgent(Agent):
    """Agente especializado en contenido viral."""
    
    def __init__(self):
        super().__init__(
            name="ViralContentAgent",
            domain="viral_content"
        )
        
        # Elementos clave para contenido viral
        self.viral_elements = {
            "hook": "Enganche visual/narrativo en primeros 3s",
            "momentum": "Mantenimiento de atención (sin caídas)",
            "emotion": "Provocación de emoción (risa, asombro, rabia)",
            "cta": "Call-to-action claro (like, share, comment)",
            "timing": "Duración óptima (15-60 segundos reel)",
            "pattern": "Sigue patrón viral conocido",
            "trending": "Usa trending sounds/trends",
        }
    
    def get_system_prompt(self, context: Dict[str, Any]) -> str:
        """Retorna prompt del sistema especializado en análisis de contenido viral."""
        content_type = context.get("content_type", "video")  # video, text, image, music
        platform = context.get("platform", "tiktok")  # tiktok, reels, shorts, etc
        
        return f"""Eres un experto en contenido viral {content_type} para {platform}.

Tu objetivo es analizar qué hace que el contenido sea viral y maximizar su potencial.

ELEMENTOS CLAVE DE VIRALIDAD ({content_type}):
1. HOOK (3s): ¿Captura atención inmediata?
2. MOMENTUM: ¿Se mantiene el engagement?
3. EMOCIÓN: ¿Qué emoción genera? (risa, asombro, rabia, etc)
4. CTA: ¿Call-to-action claro?
5. TIMING: ¿Duración óptima?
6. PATRÓN: ¿Sigue patrón viral?
7. TRENDING: ¿Usa trending content/sounds?

FORMATO DE ANÁLISIS:
- POTENCIAL VIRAL: [0-100]% (Estimado porcentaje de viralidad)
- FORTALEZAS:
  * [Elemento 1 que funciona bien]
  * [Elemento 2 que funciona bien]
- DEBILIDADES:
  * [Elemento que necesita mejorar]
  * [Cómo arreglarlo]
- RECOMENDACIONES:
  * [Cambio 1 para aumentar viralidad]
  * [Cambio 2 para aumentar viralidad]
- TRENDING OPORTUNIDADES:
  * [Sonido/trend a incorporar]
  * [Colaboración potencial]

Sé honesto pero constructivo. Prioriza viralidad real, no engagement falso."""
    
    def validate_input(self, agent_input: AgentInput) -> tuple[bool, str]:
        """Valida descripción/metadata de contenido."""
        content = agent_input.content.lower()
        
        # Debe tener información sobre el contenido
        if len(content) < 10:
            return False, "Descripción de contenido muy corta"
        
        # Idealmente debe especificar tipo
        valid_types = ["video", "reel", "short", "texto", "imagen", "audio"]
        has_type = any(t in content for t in valid_types)
        
        if not has_type and len(content) < 50:
            return False, "Especifica tipo de contenido (video, imagen, texto, etc)"
        
        return True, ""
    
    def validate_output(self, response: str) -> tuple[bool, str]:
        """Valida que el análisis sea completo."""
        if not response or len(response.strip()) < 50:
            return False, "Descripción de contenido muy corta"
        
        # Debe tener estimación de potencial (mejorado con regex correcto)
        has_viral_score = "potencial" in response.lower() or bool(re.search(r'\d+%|\[\d+-\d+\]|potencial.*\d+', response, re.IGNORECASE))
        
        # Debe tener recomendaciones
        has_recs = "recomendación" in response.lower() or "mejora" in response.lower()
        
        if not has_viral_score:
            return False, "Falta estimación de potencial viral"
        
        if not has_recs:
            return False, "Especifica tipo de contenido (video, imagen, texto, etc) y recomendaciones"
        
        return True, ""
    
    def calculate_confidence(self, response: str, input_context: Dict[str, Any]) -> float:
        """Calcula confianza en el análisis."""
        base_conf = 0.65
        
        # Análisis estructurado
        if "FORTALEZAS" in response and "DEBILIDADES" in response:
            base_conf += 0.2
        
        if "VIRAL" in response:
            base_conf += 0.1
        
        # Presencia de números/estimaciones con regex mejor
        if re.search(r'\d+%|\[\d+-\d+\]', response):
            base_conf += 0.05
        
        return min(1.0, base_conf)
    
    def suggest_improvements(self, response: str, input_context: Dict[str, Any]) -> List[str]:
        """Sugiere mejoras al análisis."""
        suggestions = []
        
        if "FORTALEZAS" not in response:
            suggestions.append("Identifica específicamente qué está funcionando bien")
        
        if "TRENDING" not in response:
            suggestions.append("Menciona oportunidades de trending/sounds actuales")
        
        if len(response) < 100:
            suggestions.append("Análisis profundo requiere más detalle")
        
        if "DEBILIDADES" not in response and "PROBLEMAS" not in response:
            suggestions.append("Identifica áreas de mejora en el contenido viral")
        
        return suggestions if suggestions else ["Análisis viral completo y específico"]
