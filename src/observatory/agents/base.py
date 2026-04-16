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
            return f"[Simulated] Response to: {prompt[:100]}"
        response = await self.ia.generate(prompt=prompt, system=system, temperature=0.7)
        return response.content

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
