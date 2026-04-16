import time

from .base import BaseAgent, AgentResult


class OptimizerAgent(BaseAgent):
    name = "optimizer"
    emoji = "⚡"
    building = "Pattern Palace"
    description = "Performance, optimización, benchmarks"
    quick_tasks = [
        "Analiza la complejidad del módulo de orquestador",
        "Sugiere optimizaciones para las queries de memoria",
        "Genera un reporte de rendimiento del sistema",
    ]

    async def execute(self, task: str) -> AgentResult:
        start = time.time()
        system = (
            "Eres un experto en optimización y rendimiento. Analizas complejidad "
            "algorítmica, bottlenecks y sugieres mejoras con datos concretos. "
            "Responde en español."
        )
        result = await self._ask_ollama(task, system)
        await self._store_memory(
            f"Optimization: {task[:50]}", "observatory:optimizer"
        )
        return AgentResult(
            success=True,
            output=result,
            memories_stored=1,
            duration_ms=int((time.time() - start) * 1000),
        )
