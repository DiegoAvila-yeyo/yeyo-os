import time

from .base import BaseAgent, AgentResult


class MinerAgent(BaseAgent):
    name = "miner"
    emoji = "⛏️"
    building = "Error Mine"
    description = "Scraping de datos, tendencias y oportunidades"
    quick_tasks = [
        "Busca los repos trending en GitHub hoy",
        "Analiza tendencias de Python en los últimos 7 días",
        "Encuentra issues abiertos en repos populares de FastAPI",
    ]

    async def execute(self, task: str) -> AgentResult:
        start = time.time()
        system = (
            "Eres un buscador de oportunidades. Analiza datos, tendencias y "
            "oportunidades de negocio/tecnología. Responde en español con datos concretos."
        )
        result = await self._ask_ollama(task, system)
        await self._store_memory(
            f"Miner finding: {task} → {result[:200]}", "observatory:miner"
        )
        return AgentResult(
            success=True,
            output=result,
            memories_stored=1,
            duration_ms=int((time.time() - start) * 1000),
        )
