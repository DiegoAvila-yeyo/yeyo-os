"""
YeyoOS — ContentAnalysisAgent
Micro-fase 3.2.6 — Agente para análisis profundo de contenido

Analiza contenido para:
- Relevancia temática
- Factualidad
- Sesgo/polarización
- Engagement potencial
- Cumplimiento de normas
- Oportunidades de optimización
"""

from src.agents.base import Agent, AgentInput, AgentOutput
from typing import Any, Dict, List
import re


class ContentAnalysisAgent(Agent):
    """Agente especializado en análisis profundo de contenido."""
    
    def __init__(self):
        super().__init__(
            name="ContentAnalysisAgent",
            domain="content_analysis"
        )
        
        self.bias_indicators = {
            "loaded_language": ["claramente", "obviamente", "simplemente", "sin duda"],
            "extreme_claims": ["nunca", "siempre", "todos", "nadie"],
            "emotional": ["horrible", "magnífico", "perfecto", "terrible"],
        }
    
    def get_system_prompt(self, context: Dict[str, Any]) -> str:
        """Retorna prompt del sistema especializado en análisis profundo de contenido."""
        content_type = context.get("type", "general")  # news, opinion, tutorial, entertainment
        platform = context.get("platform", "general")
        audience = context.get("audience", "general")
        
        return f"""Eres analista experto en contenido para {platform} ({content_type}).

Tu tarea es analizar contenido profundamente e identificar fortalezas/debilidades.

CONTEXTO DE ANÁLISIS:
- Tipo de contenido: {content_type}
- Plataforma: {platform}
- Audiencia objetivo: {audience}

DIMENSIONES A EVALUAR:
1. RELEVANCIA: ¿Es contenido oportuno y valioso para audiencia?
2. FACTUALIDAD: ¿Información verificable/con fuentes?
3. SESGO: ¿Hay carga emocional excesiva o falta de balance?
4. CLARIDAD: ¿Mensaje claro y bien estructurado?
5. ORIGINALIDAD: ¿Aporta perspectiva nueva?
6. ENGAGEMENT: ¿Qué elementos generan engagement?
7. CUMPLIMIENTO: ¿Respeta normas de plataforma?
8. OPORTUNIDADES: ¿Cómo mejorar impacto?

INDICADORES DE SESGO A DETECTAR:
- Lenguaje cargado: absolutismo, exageración
- Falta de fuentes en claims
- Cherry-picking de información
- Ad hominem u ataques personales
- Falsa dicotomía

MATRIZ DE EVALUACIÓN:
- Puntuación: 0-100 para cada dimensión
- Recomendación final: Publicar, Revisar, Rechazar
- Explicación clara de calificación

FORMATO DE RESPUESTA:
- ANÁLISIS RÁPIDO:
  * Tipo: [Identifica tipo de contenido real]
  * Tono: [Neutral, positivo, negativo, mixto]
  * Potencial: [Bajo, Medio, Alto]

- EVALUACIÓN DETALLADA:
  * RELEVANCIA: [0-100] - Explicación
  * FACTUALIDAD: [0-100] - Explicación
  * SESGO: [0-100] - Análisis de carga emocional
  * CLARIDAD: [0-100] - Estructura y comprensibilidad
  * ORIGINALIDAD: [0-100] - Perspectivas nuevas
  * ENGAGEMENT: [0-100] - Potencial de interacción
  * CUMPLIMIENTO: [0-100] - ¿Viola políticas?

- PUNTOS FUERTES:
  * [Fortaleza 1 con evidencia]
  * [Fortaleza 2 con evidencia]

- PROBLEMAS IDENTIFICADOS:
  * [Problema 1]: [Impacto] → [Solución]
  * [Problema 2]: [Impacto] → [Solución]

- OPORTUNIDADES DE MEJORA:
  * [Oportunidad 1]
  * [Oportunidad 2]

- RECOMENDACIÓN FINAL: [PUBLICAR / REVISAR / RECHAZAR]
  Justificación: [Resumen ejecutivo]

Sé crítico pero constructivo. Evidencia cualquier claim."""
    
    def validate_input(self, agent_input: AgentInput) -> tuple[bool, str]:
        """Valida que sea contenido analizable."""
        content = agent_input.content.lower()
        
        if len(content) < 20:
            return False, "Contenido muy corto para análisis"
        
        # Debe tener suficiente estructura
        if len(content) < 100 and "análisis" not in content and "revisar" not in content:
            return False, "Proporciona contenido más sustancial para analizar"
        
        return True, ""
    
    def validate_output(self, response: str) -> tuple[bool, str]:
        """Valida que el análisis sea completo."""
        if not response or len(response.strip()) < 100:
            return False, "Proporciona contenido más sustancial para analizar (mínimo 100 caracteres)"
        
        # Debe tener evaluaciones numéricas con regex específico (0-100, [0/100], etc)
        has_scores = bool(re.search(r'\b\d{1,3}\s*[/-]\s*100\b|\[\d{1,3}/100\]|\d+%', response))
        
        # Debe tener recomendación
        has_recommendation = any(word in response.upper() for word in ["PUBLICAR", "REVISAR", "RECHAZAR", "RECOMENDACIÓN"])
        
        # Debe tener problemas identificados
        has_problems = "problema" in response.lower() or "issue" in response.lower() or "debilidad" in response.lower()
        
        if not has_scores:
            return False, "Falta evaluaciones numéricas"
        
        if not has_recommendation:
            return False, "Falta recomendación final"
        
        return True, ""
    
    def calculate_confidence(self, response: str, input_context: Dict[str, Any]) -> float:
        """Calcula confianza en el análisis."""
        base_conf = 0.62
        
        # Estructura completa (categorías)
        categories = ["RELEVANCIA", "FACTUALIDAD", "SESGO", "CLARIDAD", "ORIGINALIDAD"]
        found = sum(1 for cat in categories if cat in response)
        base_conf += (found / len(categories)) * 0.25
        
        # Presencia de problemas/fortalezas identificadas
        if "PROBLEMAS" in response and "FUERTES" in response:
            base_conf += 0.08
        
        # Evidencia de análisis crítico
        if any(word in response.lower() for word in ["sesgo", "carga", "balance", "parcial"]):
            base_conf += 0.05
        
        return min(1.0, base_conf)
    
    def suggest_improvements(self, response: str, input_context: Dict[str, Any]) -> List[str]:
        """Sugiere mejoras al análisis."""
        suggestions = []
        
        if "SESGO" not in response:
            suggestions.append("Incluye análisis específico de sesgo/balance")
        
        if "FACTUALIDAD" not in response:
            suggestions.append("Especifica dónde se necesitan fuentes/verificación")
        
        if not re.search(r'\b\d{1,3}\s*[/-]\s*100\b|\[\d{1,3}/100\]|\d+%', response):
            suggestions.append("Incluye evaluaciones numéricas de cada dimensión")
        
        if "RECOMENDACIÓN" not in response.upper():
            suggestions.append("Proporciona recomendación clara (PUBLICAR/REVISAR/RECHAZAR)")
        
        return suggestions if suggestions else ["Análisis profundo y completo"]
