import time

from .base import BaseAgent, AgentResult


class RobotAgent(BaseAgent):
    name = "robot"
    emoji = "🤖"
    building = "Workflow Factory"
    description = "Workflows, cron jobs, integraciones"
    quick_tasks = [
        "Crea un workflow para backup diario de la DB",
        "Automatiza la limpieza de archivos temporales",
        "Diseña una integración con GitHub webhooks",
    ]

    async def execute(self, task: str) -> AgentResult:
        start = time.time()
        system = (
            "Eres un ingeniero de automatización. Diseñas workflows, cron jobs e "
            "integraciones entre servicios. Responde en español con código y "
            "configuración."
        )
        result = await self._ask_ollama(task, system)
        await self._store_memory(
            f"Automation: {task[:50]}", "observatory:robot"
        )
        return AgentResult(
            success=True,
            output=result,
            memories_stored=1,
            duration_ms=int((time.time() - start) * 1000),
        )
