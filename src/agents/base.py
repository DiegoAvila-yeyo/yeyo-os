"""
YeyoOS — Agent Base Architecture & Interfaces
Micro-fase 3.1 — Capa 3: Agentes

Base classes and interfaces para todos los agentes.
Los agentes son "mentores" para Ollama, guiando decisiones en dominios específicos.

Un agente proporciona:
1. System prompts especializados (domain knowledge)
2. Input validation (asegura datos bien formados)
3. Output validation & enhancement (mejora respuestas del LLM)
4. Pattern injection from Flash Memory (contexto persistente)
5. Score/confidence calculation (cuán buena fue la respuesta)
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("yeyoos.agents")


@dataclass
class AgentInput:
    """Entrada a un agente."""
    content: str  # Prompt/tarea del usuario
    context: Dict[str, Any] = field(default_factory=dict)  # Contexto adicional
    metadata: Dict[str, Any] = field(default_factory=dict)  # Metadata
    
    def __post_init__(self):
        if not self.content or not isinstance(self.content, str):
            raise ValueError("content must be non-empty string")


@dataclass
class AgentOutput:
    """Salida de un agente."""
    response: str  # Respuesta generada
    confidence: float = 0.8  # [0.0-1.0] cuán confiado está el agente
    reasoning: str = ""  # Explicación de la decisión
    suggestions: List[str] = field(default_factory=list)  # Sugerencias para mejora
    tokens_used: int = 0
    
    def __post_init__(self):
        # Clamp confidence
        self.confidence = max(0.0, min(1.0, self.confidence))


class Agent(ABC):
    """
    Base class para todos los agentes de YeyoOS.
    
    Un agente es un "mentor" que guía a Ollama hacia mejores decisiones
    en un dominio específico.
    
    Responsabilidades:
    1. Validar input
    2. Generar system prompt especializado
    3. Validar output del LLM
    4. Inyectar patrones desde memoria persistente
    5. Calcular confianza
    """
    
    def __init__(self, name: str, domain: str):
        """
        Args:
            name: Nombre del agente (ej: "CodeReviewAgent")
            domain: Dominio de expertise (ej: "code_review")
        """
        self.name = name
        self.domain = domain
        self._enabled = True
    
    @abstractmethod
    def get_system_prompt(self, context: Dict[str, Any]) -> str:
        """
        Retorna el system prompt especializado para este agente.
        
        Se usa para guiar a Ollama hacia respuestas en este dominio.
        
        Returns:
            str: System prompt completo con instrucciones del dominio
        """
        pass
    
    @abstractmethod
    def validate_input(self, agent_input: AgentInput) -> tuple[bool, str]:
        """
        Valida que el input sea válido para este agente.
        
        Returns:
            (is_valid, error_message)
        """
        pass
    
    @abstractmethod
    def validate_output(self, response: str) -> tuple[bool, str]:
        """
        Valida que la respuesta del LLM sea válida para este dominio.
        
        Returns:
            (is_valid, error_message)
        """
        pass
    
    @abstractmethod
    def calculate_confidence(self, response: str, input_context: Dict[str, Any]) -> float:
        """
        Calcula confianza en la respuesta (0.0-1.0).
        
        Factores:
        - Completitud de la respuesta
        - Coherencia con input
        - Presencia de explicaciones
        - Estructura/formato
        """
        pass
    
    def suggest_improvements(self, response: str, input_context: Dict[str, Any]) -> List[str]:
        """
        Sugiere mejoras a la respuesta del LLM (optional override).
        
        Default: empty list.
        """
        return []
    
    def inject_patterns(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inyecta patrones desde Flash Memory en el contexto.
        (Implementado por subclases si es necesario)
        """
        return context
    
    async def process(self, agent_input: AgentInput) -> AgentOutput:
        """
        Pipeline completo del agente:
        1. Validar input
        2. Inyectar patrones
        3. Generar system prompt
        4. Validar output
        5. Calcular confianza
        6. Sugerir mejoras
        
        El LLM debe ser llamado EXTERNAMENTE con system_prompt.
        """
        # 1. Validar input
        is_valid, error_msg = self.validate_input(agent_input)
        if not is_valid:
            logger.warning(f"[{self.name}] Input validation failed: {error_msg}")
            return AgentOutput(
                response="",
                confidence=0.0,
                reasoning=f"Input validation failed: {error_msg}"
            )
        
        # 2. Inyectar patrones en contexto
        context = self.inject_patterns(agent_input.context)
        
        # 3. Generar system prompt (para ser usado con Ollama externamente)
        system_prompt = self.get_system_prompt(context)
        
        logger.debug(f"[{self.name}] System prompt generated ({len(system_prompt)} chars)")
        
        # El usuario debe usar este system_prompt con Ollama para obtener response
        # Luego llamar process_response() para validar
        
        return AgentOutput(
            response="",  # Será llenado por el usuario después de LLM
            confidence=0.0,
            reasoning=f"Use system_prompt: {system_prompt[:100]}..."
        )
    
    async def process_response(
        self,
        llm_response: str,
        agent_input: AgentInput
    ) -> AgentOutput:
        """
        Procesa la respuesta del LLM (después de que Ollama genera).
        
        Workflow:
        1. system_prompt = agent.get_system_prompt(context)
        2. llm_response = await ollama.generate(system_prompt, input)
        3. output = await agent.process_response(llm_response, input)
        """
        # 1. Validar output
        is_valid, error_msg = self.validate_output(llm_response)
        if not is_valid:
            logger.warning(f"[{self.name}] Output validation failed: {error_msg}")
            confidence = 0.2  # Low confidence si falla validación
        else:
            # 2. Calcular confianza
            confidence = self.calculate_confidence(llm_response, agent_input.context)
        
        # 3. Sugerir mejoras
        suggestions = self.suggest_improvements(llm_response, agent_input.context)
        
        output = AgentOutput(
            response=llm_response,
            confidence=confidence,
            suggestions=suggestions,
            reasoning=f"Validation: {'PASS' if is_valid else 'FAIL'}. "
                      f"Confidence: {confidence:.2f}"
        )
        
        logger.info(
            f"[{self.name}] Response processed: "
            f"confidence={confidence:.2f}, valid={is_valid}"
        )
        
        return output


class GenericAgent(Agent):
    """
    Agente genérico para dominios sin especialización específica.
    Usado como fallback o para testing.
    """
    
    def get_system_prompt(self, context: Dict[str, Any]) -> str:
        return (
            "Eres un asistente útil y preciso. "
            "Responde en español. "
            "Sé conciso pero completo. "
            "Si no sabes, di que no sabes."
        )
    
    def validate_input(self, agent_input: AgentInput) -> tuple[bool, str]:
        if not agent_input.content or len(agent_input.content.strip()) == 0:
            return False, "Content is empty"
        return True, ""
    
    def validate_output(self, response: str) -> tuple[bool, str]:
        if not response or len(response.strip()) == 0:
            return False, "Response is empty"
        if len(response) < 10:
            return False, "Response too short (< 10 chars)"
        return True, ""
    
    def calculate_confidence(self, response: str, input_context: Dict[str, Any]) -> float:
        """Simple heuristic: longer responses = higher confidence (up to a point)"""
        base_confidence = 0.5
        length_factor = min(len(response) / 200.0, 0.3)  # Max +0.3
        return min(1.0, base_confidence + length_factor)
