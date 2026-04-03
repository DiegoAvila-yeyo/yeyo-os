"""
YeyoOS — VideoEditingAgent
Micro-fase 3.2.5 — Agente para instrucciones de edición de video

Proporciona guía de edición:
- Cuts y pacing
- Transiciones
- Efectos y audio
- Color grading
- Motion graphics
- Optimización para plataforma
"""

import re
from src.agents.base import Agent, AgentInput, AgentOutput
from typing import Any, Dict, List


class VideoEditingAgent(Agent):
    """Agente especializado en instrucciones de edición de video."""
    
    def __init__(self):
        super().__init__(
            name="VideoEditingAgent",
            domain="video_editing"
        )
        
        self.platforms = {
            "tiktok": {"max_length": 10, "ideal": 15, "cuts_per_min": 3},
            "shorts": {"max_length": 60, "ideal": 30, "cuts_per_min": 2},
            "reels": {"max_length": 90, "ideal": 45, "cuts_per_min": 2},
            "youtube": {"max_length": 600, "ideal": 300, "cuts_per_min": 1},
        }
    
    def get_system_prompt(self, context: Dict[str, Any]) -> str:
        """Retorna prompt del sistema especializado en instrucciones de edición de video."""
        platform = context.get("platform", "tiktok").lower()
        genre = context.get("genre", "general")  # tutorial, entertainment, vlog, etc
        pacing = context.get("pacing", "fast")  # slow, medium, fast
        
        specs = self.platforms.get(platform, self.platforms["tiktok"])
        
        return f"""Eres editor de video experto para {platform} ({genre}).

Tu tarea es proporcionar instrucciones de edición que maximicen engagement.

ESPECIFICACIONES DE PLATAFORMA ({platform}):
- Duración máxima: {specs['max_length']}s
- Duración ideal: {specs['ideal']}s
- Cuts/min recomendados: {specs['cuts_per_min']}
- Formato: Vertical (9:16) preferido

PRINCIPIOS DE EDICIÓN:
1. PACING: {pacing} - mantén ritmo consistente
2. CORTES: Cuta en transiciones naturales/musicales
3. TRANSICIONES: Fade, slide, cut, zoom (2-3 tipos máximo)
4. AUDIO: Sincroniza con beat, usa trending sounds
5. COLOR: Grado consistente, 2-3 looks máximo
6. EFECTOS: Subtiles, no distrigan del contenido
7. TIEMPO: Mantén viewer attention (hook cada 3-5s)
8. HOOKS: Texto, efecto o corte drástico en primeros 3 segundos

ESTRUCTURA TÍPICA:
1. HOOK (0-3s): Captura atención
2. DESARROLLO (3-[X]s): Mantiene momentum
3. PAYOFF ([X-1]s): Recompensa al viewer
4. CTA (últimos 2s): Share, like, follow

FORMATO DE RESPUESTA:
- PERFIL DE EDICIÓN: [Estilo de pacing/ritmo]
- TIMELINE PROPUESTO:
  * 0:00-0:03 HOOK: [Descripción con efecto]
  * 0:03-[X]:XX MAIN: [Secciones con transiciones]
  * [X]:XX-[TOTAL] CTA: [Call to action]
- RECOMENDACIONES POR SEGMENTO:
  * CUTS: [Número y tipo]
  * TRANSICIONES: [Tipos específicos]
  * AUDIO: [Recomendaciones de sonido/música]
  * COLOR GRADE: [Estilo: cinematic, vibrant, film noir, etc]
- EFECTOS CLAVE:
  * [Efecto 1]: [Cuándo/dónde aplicar]
  * [Efecto 2]: [Cuándo/dónde aplicar]
- CHECKLIST ANTES DE EXPORTAR:
  ✓ Audio mezclado correctamente (no picos)
  ✓ Colores consistentes entre cortes
  ✓ Transiciones fluidas
  ✓ Subtítulos (si aplica) sincronizados
  ✓ Duración dentro de límites

Sé específico con tiempos y técnicas. Optimiza para {platform}."""
    
    def validate_input(self, agent_input: AgentInput) -> tuple[bool, str]:
        """Valida que sea descriptor de video."""
        content = agent_input.content.lower()
        
        if len(content) < 15:
            return False, "Descripción muy corta"
        
        # Debe mencionar características de video
        video_words = ["video", "grabación", "clip", "escena", "duración", "segundo"]
        has_video = any(w in content for w in video_words)
        
        if not has_video and len(content) < 60:
            return False, "Describe características del video (duración, contenido, etc)"
        
        return True, ""
    
    def validate_output(self, response: str) -> tuple[bool, str]:
        """Valida que contenga instrucciones claras."""
        if not response or len(response.strip()) < 100:
            return False, "Descripción muy corta (mínimo 100 caracteres)"
        
        # Debe tener timeline (mejorado: regex correcto para timecode MM:SS o H:MM:SS)
        has_timeline = "timeline" in response.lower() or bool(re.search(r'\d{1,2}:\d{2}', response))
        
        # Debe tener transiciones/cortes
        has_cuts = "corte" in response.lower() or "transición" in response.lower() or "cut" in response.lower()
        
        if not has_timeline:
            return False, "Falta estructura/timeline del video"
        
        if not has_cuts:
            return False, "Falta recomendaciones de cortes/transiciones"
        
        return True, ""
    
    def calculate_confidence(self, response: str, input_context: Dict[str, Any]) -> float:
        """Calcula confianza en instrucciones."""
        base_conf = 0.65
        
        # Presencia de timeline específico (mejorado: regex correcto)
        if bool(re.search(r'\d{1,2}:\d{2}', response)):
            base_conf += 0.15
        
        # Checklist presente
        if "✓" in response or "checklist" in response.lower():
            base_conf += 0.1
        
        # Menciona audio/sync
        if "audio" in response.lower() or "beat" in response.lower():
            base_conf += 0.08
        
        return min(1.0, base_conf)
    
    def suggest_improvements(self, response: str, input_context: Dict[str, Any]) -> List[str]:
        """Sugiere mejoras a instrucciones."""
        suggestions = []
        
        if not re.search(r'\d{1,2}:\d{2}', response):
            suggestions.append("Proporciona timestamps específicos (0:00-0:05)")
        
        if "audio" not in response.lower() and "música" not in response.lower():
            suggestions.append("Incluye recomendaciones específicas de audio/música")
        
        if "color" not in response.lower():
            suggestions.append("Especifica recomendaciones de color grading")
        
        if len(response) < 200:
            suggestions.append("Más detalles en transiciones y efectos")
        
        return suggestions if suggestions else ["Instrucciones de edición completas"]
