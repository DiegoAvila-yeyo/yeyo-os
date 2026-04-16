import time

from .base import BaseAgent, AgentResult


class ScientistAgent(BaseAgent):
    name = "scientist"
    emoji = "🔬"
    building = "Lab"
    description = "Investiga papers, documentación técnica y repos"
    quick_tasks = [
        "Investiga qué hace el módulo de memoria de este proyecto",
        "Resume las mejores prácticas de FastAPI",
        "Analiza la arquitectura de este repositorio",
    ]

    async def execute(self, task: str) -> AgentResult:
        start = time.time()
        system = (
            "Eres un investigador científico. Analiza documentación, código y "
            "papers con rigor académico. Responde en español con citas y evidencia."
        )
        result = await self._ask_ollama(task, system)
        await self._store_memory(
            f"Research: {task} → {result[:200]}", "observatory:scientist"
        )
        return AgentResult(
            success=True,
            output=result,
            memories_stored=1,
            duration_ms=int((time.time() - start) * 1000),
        )
