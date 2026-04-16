import time

from .base import BaseAgent, AgentResult


class SageAgent(BaseAgent):
    name = "sage"
    emoji = "🧙"
    building = "Pattern Palace"
    description = "Roadmap, priorización, estrategia"
    quick_tasks = [
        "Propón un roadmap para los próximos 3 meses",
        "Analiza pros/cons de migrar a PostgreSQL 16",
        "Prioriza los features más impactantes",
    ]

    async def execute(self, task: str) -> AgentResult:
        start = time.time()
        system = (
            "Eres un estratega senior. Analizas decisiones técnicas, priorizas "
            "features y creas roadmaps. Usa datos de todos los agentes para generar "
            "insights. Responde en español."
        )
        result = await self._ask_ollama(task, system)
        await self._store_memory(
            f"Strategy: {task[:50]}", "observatory:sage"
        )
        return AgentResult(
            success=True,
            output=result,
            memories_stored=1,
            duration_ms=int((time.time() - start) * 1000),
        )
