import time

from .base import BaseAgent, AgentResult


class WriterAgent(BaseAgent):
    name = "writer"
    emoji = "✍️"
    building = "Library"
    description = "Blog posts, tutoriales, documentación, emails"
    quick_tasks = [
        "Escribe un README para el módulo de memoria",
        "Genera un tutorial de cómo usar la API de video",
        "Redacta un blog post sobre el sistema de agentes",
    ]

    async def execute(self, task: str) -> AgentResult:
        start = time.time()
        system = (
            "Eres un escritor técnico profesional. Creas contenido claro, "
            "bien estructurado y atractivo. Responde en español con formato Markdown."
        )
        result = await self._ask_ollama(task, system)
        await self._store_memory(
            f"Content: {task[:50]} → written", "observatory:writer"
        )
        return AgentResult(
            success=True,
            output=result,
            memories_stored=1,
            duration_ms=int((time.time() - start) * 1000),
        )
