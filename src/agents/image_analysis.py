"""
YeyoOS — ImageAnalysisAgent
Micro-fase 3.2.3 — Agente para análisis de imágenes

Analiza características visuales:
- Composición y framing
- Colores y paleta
- Texto visible
- Objetos/elementos
- Calidad y claridad
- Potencial de uso
"""

import re
from src.agents.base import Agent, AgentInput, AgentOutput
from typing import Any, Dict, List


class ImageAnalysisAgent(Agent):
    """Agente especializado en análisis de imágenes."""
    
    def __init__(self):
        super().__init__(
            name="ImageAnalysisAgent",
            domain="image_analysis"
        )
    
    def get_system_prompt(self, context: Dict[str, Any]) -> str:
        """Retorna prompt del sistema especializado en análisis de imágenes."""
        purpose = context.get("purpose", "general")  # general, thumbnail, content, background
        
        return f"""Eres un experto en análisis visual de imágenes para propósito: {purpose}.

Tu tarea es analizar imagen y proporcionar insights accionables.

ASPECTOS A ANALIZAR:
1. COMPOSICIÓN: Framing, simetría, punto focal
2. COLORES: Paleta dominante, contraste, armonía
3. ILUMINACIÓN: Fuente de luz, sombras, claridad
4. OBJETOS: Elementos principales, detalles relevantes
5. TEXTO: ¿Hay texto? ¿Es legible? ¿Está bien posicionado?
6. EMOCIONES: ¿Qué emociones transmite? (alegría, tensión, calma, etc)
7. CALIDAD: Resolución, nitidez, posibles problemas
8. USO: Mejor uso para: reel thumbnail, post, background, etc

FORMATO DE RESPUESTA:
- PROPÓSITO ÓPTIMO: [Uso recomendado]
- CALIFICACIÓN VISUAL: [0-10]
- FORTALEZAS VISUALES:
  * [Elemento 1]
  * [Elemento 2]
- ÁREAS DE MEJORA:
  * [Problema 1]: [Solución]
  * [Problema 2]: [Solución]
- SUGERENCIAS DE EDICIÓN:
  * [Sugerencia 1]
  * [Sugerencia 2]
- IMPACTO EMOCIONAL: [Descripción]

Sé específico con colores (ej: #FF5733) y coordenadas cuando sea relevante."""
    
    def validate_input(self, agent_input: AgentInput) -> tuple[bool, str]:
        """Valida que sea descripción de imagen."""
        content = agent_input.content.lower()
        
        if len(content) < 10:
            return False, "Descripción muy corta"
        
        # Debe mencionar características visuales
        visual_words = ["imagen", "foto", "color", "objeto", "composición", "escena", "visual"]
        has_visual = any(w in content for w in visual_words)
        
        if not has_visual and len(content) < 30:
            return False, "Describe características visuales (colores, composición, etc)"
        
        return True, ""
    
    def validate_output(self, response: str) -> tuple[bool, str]:
        """Valida que el análisis sea completo."""
        if not response or len(response.strip()) < 50:
            return False, "Descripción muy corta"
        
        # Debe tener calificación visual (mejorado)
        has_rating = "calificación" in response.lower() or bool(re.search(r'\b\d+\s*[/-]\s*10\b|\[\d+/10\]|\d+%', response))
        
        # Debe tener análisis de colores/composición
        has_visual_analysis = any(word in response.lower() for word in ["color", "composición", "luz", "framing"])
        
        if not has_rating:
            return False, "Falta calificación visual"
        
        if not has_visual_analysis:
            return False, "Falta análisis de elementos visuales"
        
        return True, ""
    
    def calculate_confidence(self, response: str, input_context: Dict[str, Any]) -> float:
        """Calcula confianza en el análisis."""
        base_conf = 0.65
        
        # Análisis estructurado
        sections = ["FORTALEZAS", "MEJORA", "SUGERENCIA", "IMPACTO"]
        sections_found = sum(1 for s in sections if s in response)
        base_conf += (sections_found / len(sections)) * 0.25
        
        # Menciona elementos específicos
        if "color" in response.lower() or "#" in response:
            base_conf += 0.05
        
        if "composición" in response.lower() or "framing" in response.lower():
            base_conf += 0.05
        
        return min(1.0, base_conf)
    
    def suggest_improvements(self, response: str, input_context: Dict[str, Any]) -> List[str]:
        """Sugiere mejoras al análisis."""
        suggestions = []
        
        if "#" not in response and "color" in response.lower():
            suggestions.append("Especifica colores con códigos hex (#RRGGBB)")
        
        if "composición" not in response.lower():
            suggestions.append("Incluye análisis específico de composición y framing")
        
        if len(response) < 150:
            suggestions.append("Análisis más profundo de elementos visuales")
        
        if "EMOCIONES" not in response and "EMOCIONALES" not in response:
            suggestions.append("Describe qué emociones transmite la imagen")
        
        return suggestions if suggestions else ["Análisis visual completo y detallado"]
