import asyncio
from dataclasses import dataclass, field
from typing import Optional
import time


@dataclass
class AgentResult:
    success: bool
    output: str
    files_created: list[str] = field(default_factory=list)
    memories_stored: int = 0
    duration_ms: int = 0
    error: Optional[str] = None


class BaseAgent:
    name: str = "base"
    emoji: str = "🤖"
    building: str = "HQ"
    description: str = "Base agent"
    quick_tasks: list[str] = []

    def __init__(self, ia_provider=None, memory=None):
        self.ia = ia_provider
        self.memory = memory

    async def execute(self, task: str) -> AgentResult:
        raise NotImplementedError

    async def _ask_ollama(self, prompt: str, system: str = "") -> str:
        if self.ia is None:
            return self._simulated_response(prompt)
        try:
            response = await asyncio.wait_for(
                self.ia.generate(prompt=prompt, system=system, temperature=0.7),
                timeout=8.0,
            )
            return response.content if response.content else self._simulated_response(prompt)
        except Exception:
            return self._simulated_response(prompt)

    def _simulated_response(self, prompt: str) -> str:
        """Generate a structured fallback response when Ollama is unavailable."""
        task_snippet = prompt[:120].replace("\n", " ")
        return (
            f"[Análisis simulado — Ollama no disponible]\n\n"
            f"Tarea recibida: {task_snippet}...\n\n"
            f"Agente: {self.name} ({self.emoji})\n\n"
            f"Resultado: Esta tarea requiere acceso a un modelo de lenguaje. "
            f"El agente {self.name} ha registrado la solicitud y proporcionará "
            f"un análisis completo cuando Ollama esté disponible con el modelo configurado. "
            f"En modo simulación, todas las operaciones de lectura/verificación de APIs "
            f"se ejecutan normalmente; solo la generación de texto IA usa esta respuesta de fallback."
        )

    async def _store_memory(self, content: str, namespace: str) -> bool:
        if self.memory is None:
            return False
        try:
            await self.memory.store(
                content=content,
                type="fact",
                source=f"observatory:{self.name}",
                namespace=namespace,
            )
            return True
        except Exception:
            return False
