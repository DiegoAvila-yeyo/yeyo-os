"""
YeyoOS — ThumbnailAgent
Micro-fase 3.2.4 — Agente para generación de thumbnails

Genera instrucciones para creación de thumbnails efectivos:
- Composición que llama atención
- Contraste y legibilidad
- Texto destacado
- Emoción clara
- Compliance con plataforma
"""

from src.agents.base import Agent, AgentInput, AgentOutput
from typing import Any, Dict, List
import re


class ThumbnailAgent(Agent):
    """Agente especializado en generación/evaluación de thumbnails."""
    
    def __init__(self):
        super().__init__(
            name="ThumbnailAgent",
            domain="thumbnail"
        )
        
        self.platforms = {
            "youtube": {"size": "1280x720", "aspect": "16:9", "text_safe": "0-20% margen"},
            "tiktok": {"size": "1080x1920", "aspect": "9:16", "text_safe": "10-20% margen"},  # Consistente
            "shorts": {"size": "1440x2560", "aspect": "9:16", "text_safe": "15-25% margen"},  # Consistente
            "twitch": {"size": "1280x720", "aspect": "16:9", "text_safe": "5-15% margen"},
        }
    
    def get_system_prompt(self, context: Dict[str, Any]) -> str:
        """Retorna prompt del sistema especializado en generación de thumbnails."""
        platform = context.get("platform", "youtube").lower()
        topic = context.get("topic", "general")
        style = context.get("style", "modern")  # modern, retro, minimalist, dramatic
        
        platform_specs = self.platforms.get(platform, self.platforms["youtube"])
        
        return f"""Eres experto en diseño de thumbnails para {platform} ({style}).

Tu tarea es crear o evaluar thumbnails que maximizen clicks y engagement.

ESPECIFICACIONES TÉCNICAS ({platform}):
- Tamaño: {platform_specs['size']}
- Aspect ratio: {platform_specs['aspect']}
- Área segura para texto: {platform_specs['text_safe']}
- Formato: PNG/JPEG con >150dpi

PRINCIPIOS DE CTR (Click-Through Rate):
1. CONTRASTE: Alto contraste entre elementos (80%+ diferencia)
2. FOCAL POINT: Un punto focal claro, sin competencia visual
3. EXPRESIÓN: Emoción exagerada en rostros (sorpresa, miedo, alegría extrema)
4. TIPOGRAFÍA: Sans-serif bold, 70+ puntos, máximo 3-5 palabras
5. COLORES: 2-3 colores máximo, complementarios o contrastantes
6. ESPACIO NEGATIVO: Deja respiración visual (15% mínimo)
7. BRANDING: Logo/name visible pero no dominante
8. CONSISTENCIA: Visual consistent con serie/canal

FÓRMULA DE ÉXITO:
Expresión + Contraste + Texto Claro + Colores Bold + Curiosidad = CTR Alto

FORMATO DE RESPUESTA:
- POTENCIAL CTR: [0-100]% (Estimado)
- ESPECIFICACIONES FINALES:
  * Dimensiones: [WxH pixels]
  * Colores: [Color 1 #HEX, Color 2 #HEX, Color 3 #HEX]
  * Tipografía: [Fuente, tamaño, estilo]
- COMPOSICIÓN RECOMENDADA:
  * Fondo: [Descripción]
  * Elemento principal: [Descripción con posición]
  * Texto principal: [Texto sugerido]
  * Elemento secundario: [Opcional]
- CHECKLIST FINAL:
  ✓ Contraste suficiente para móvil
  ✓ Legible en tamaño pequeño (100x100px)
  ✓ Emoción clara y evidente
  ✓ Coherente con {platform} trends
- SUGERENCIAS DE ITERACIÓN:
  * [Si A, entonces B]
  * [Alternativa de prueba]

Sé técnico pero creativo. Prioriza engagement sobre estética pura."""
    
    def validate_input(self, agent_input: AgentInput) -> tuple[bool, str]:
        """Valida que sea descriptor de thumbnail."""
        content = agent_input.content.lower()
        
        if len(content) < 15:
            return False, "Descripción muy corta para thumbnail"
        
        # Debe tener contexto (tema, plataforma, etc)
        has_context = any(word in content for word in ["tema", "título", "video", "contenido", "para", "youtube", "tiktok", "instagram"])
        
        if not has_context and len(content) < 50:
            return False, "Especifica tema, plataforma o contexto del thumbnail"
        
        return True, ""
    
    def validate_output(self, response: str) -> tuple[bool, str]:
        """Valida que contenga especificaciones técnicas."""
        if not response or len(response.strip()) < 80:
            return False, "Especificaciones muy cortas (mínimo 80 caracteres)"
        
        # Debe tener dimensiones (mejorado: busca patrón NxN, no solo "x")
        has_specs = bool(re.search(r'\d+\s*x\s*\d+', response.lower())) or "dimensión" in response.lower()
        
        # Debe tener colores
        has_colors = "#" in response or "color" in response.lower()
        
        if not has_specs:
            return False, "Falta especificaciones técnicas (dimensiones)"
        
        if not has_colors:
            return False, "Falta especificación de colores"
        
        return True, ""
    
    def calculate_confidence(self, response: str, input_context: Dict[str, Any]) -> float:
        """Calcula confianza en las recomendaciones."""
        base_conf = 0.68
        
        # Presencia de especificaciones técnicas (mejorado: busca patrón real)
        if bool(re.search(r'\d+\s*x\s*\d+', response.lower())) or "dimensión" in response.lower():
            base_conf += 0.15
        
        # Colores especificados
        if "#" in response:
            base_conf += 0.1
        
        # Checklist presente
        if "✓" in response or "checklist" in response.lower():
            base_conf += 0.07
        
        return min(1.0, base_conf)
    
    def suggest_improvements(self, response: str, input_context: Dict[str, Any]) -> List[str]:
        """Sugiere mejoras a las recomendaciones."""
        suggestions = []
        
        if "#" not in response:
            suggestions.append("Especifica colores con código hex (#RRGGBB)")
        
        if "CTR" not in response and "%" in response:
            suggestions.append("Proporciona estimado de CTR esperado")
        
        if "tipografía" not in response.lower() and "fuente" not in response.lower():
            suggestions.append("Detalla recomendaciones de fuente/tipografía")
        
        if len(response) < 200:
            suggestions.append("Incluye más detalles técnicos y de composición")
        
        return suggestions if suggestions else ["Recomendaciones técnicas completas"]
