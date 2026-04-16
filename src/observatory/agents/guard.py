import time

from .base import BaseAgent, AgentResult


class GuardAgent(BaseAgent):
    name = "guard"
    emoji = "🛡️"
    building = "Security Station"
    description = "Seguridad, vulnerabilidades, compliance"
    quick_tasks = [
        "Escanea las dependencias Python por vulnerabilidades",
        "Verifica la seguridad de la configuración CORS",
        "Audita los endpoints de la API para SQL injection",
    ]

    async def execute(self, task: str) -> AgentResult:
        start = time.time()
        system = (
            "Eres un experto en ciberseguridad. Buscas vulnerabilidades, verificas "
            "configuraciones y generas reportes de compliance. Responde en español "
            "con severidad de cada hallazgo."
        )
        result = await self._ask_ollama(task, system)
        await self._store_memory(
            f"Security: {task[:50]}", "observatory:guard"
        )
        return AgentResult(
            success=True,
            output=result,
            memories_stored=1,
            duration_ms=int((time.time() - start) * 1000),
        )
