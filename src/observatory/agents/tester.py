import time

from .base import BaseAgent, AgentResult


class TesterAgent(BaseAgent):
    name = "tester"
    emoji = "💪"
    building = "Gym"
    description = "Tests automatizados, monitoreo de uptime, QA"
    quick_tasks = [
        "Verifica que el endpoint /api/v1/memory/stats responde",
        "Lista los tests que existen en el proyecto",
        "Genera un test plan para el módulo de video",
    ]

    async def execute(self, task: str) -> AgentResult:
        start = time.time()
        task_lower = task.lower()
        if "endpoint" in task_lower or "api" in task_lower or "health" in task_lower:
            result = await self._check_endpoints()
        else:
            system = (
                "Eres un QA engineer. Genera test plans, verifica calidad y "
                "sugiere mejoras de testing. Responde en español."
            )
            result = await self._ask_ollama(task, system)
        await self._store_memory(
            f"QA: {task} → {result[:200]}", "observatory:tester"
        )
        return AgentResult(
            success=True,
            output=result,
            memories_stored=1,
            duration_ms=int((time.time() - start) * 1000),
        )

    async def _check_endpoints(self) -> str:
        import aiohttp

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "http://localhost:8000/health",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    health = await resp.json()
                    return f"Health check: status={resp.status}\n{health}"
        except Exception as e:
            return f"Health check failed: {e}"
