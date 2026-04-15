"""
YeyoOS — Code Node (Editor)
Micro-fase 5.7 — Capa 5: Órganos

Editor de código con tabs, syntax highlighting config,
IA para explicar/generar/sugerir fixes.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass, field

from src.nodes.base import NodeBase, PrivilegeLevel


SUPPORTED_LANGUAGES = [
    "python", "javascript", "typescript", "html", "css",
    "json", "yaml", "markdown", "bash", "sql",
    "rust", "go", "java", "c", "cpp",
]

LANGUAGE_EXTENSIONS = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".html": "html", ".css": "css", ".json": "json",
    ".yml": "yaml", ".yaml": "yaml", ".md": "markdown",
    ".sh": "bash", ".sql": "sql", ".rs": "rust",
    ".go": "go", ".java": "java", ".c": "c", ".cpp": "cpp",
    ".h": "c", ".hpp": "cpp",
}


@dataclass
class CodeTab:
    """Tab abierto en el editor."""
    id: str
    filename: str
    language: str
    content: str
    is_modified: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CodeNode(NodeBase):
    """
    Nodo de Código — editor con tabs, IA para explicar/generar/sugerir.
    """

    def __init__(self):
        super().__init__(
            name="Code",
            version="1.0.0",
            privilege_level=PrivilegeLevel.SANDBOX,
            container_config={"memory_limit": "1g", "cpu_shares": 768},
        )
        self._tabs: dict[str, CodeTab] = {}
        self._active_tab_id: Optional[str] = None

    async def initialize(self) -> None:
        """Inicializa el editor con un tab vacío."""
        tab = self._create_tab("untitled.py", "python", "")
        self._active_tab_id = tab.id

    async def render_ui(self) -> dict:
        return {
            "component": "CodeNode",
            "props": {
                "tabs": [
                    {"id": t.id, "filename": t.filename, "language": t.language,
                     "isModified": t.is_modified}
                    for t in self._tabs.values()
                ],
                "activeTabId": self._active_tab_id,
                "languages": SUPPORTED_LANGUAGES,
            },
        }

    async def process(self, input_data: dict) -> dict:
        action = input_data.get("action", "explain")

        if action == "explain":
            return await self._explain_code(input_data.get("code", ""))
        elif action == "generate":
            return await self._generate_code(
                input_data.get("prompt", ""),
                input_data.get("language", "python"),
            )
        elif action == "suggest_fix":
            return await self._suggest_fix(
                input_data.get("code", ""),
                input_data.get("error", ""),
            )
        else:
            return {"error": f"Acción desconocida: {action}"}

    async def cleanup(self) -> None:
        self._tabs.clear()
        self._active_tab_id = None

    # ═══════════════════════════════════
    # TAB MANAGEMENT
    # ═══════════════════════════════════

    def _create_tab(self, filename: str, language: str, content: str) -> CodeTab:
        if language not in SUPPORTED_LANGUAGES:
            language = "python"
        tab = CodeTab(
            id=f"tab-{uuid.uuid4().hex[:8]}",
            filename=filename,
            language=language,
            content=content,
        )
        self._tabs[tab.id] = tab
        return tab

    async def open_tab(self, filename: str, content: str = "", language: str = "") -> dict:
        """Abre un nuevo tab."""
        if not language:
            ext = "." + filename.rsplit(".", 1)[-1] if "." in filename else ""
            language = LANGUAGE_EXTENSIONS.get(ext, "python")
        tab = self._create_tab(filename, language, content)
        self._active_tab_id = tab.id
        return {"tab_id": tab.id, "filename": filename, "language": language}

    async def close_tab(self, tab_id: str) -> bool:
        if tab_id not in self._tabs:
            return False
        del self._tabs[tab_id]
        if self._active_tab_id == tab_id:
            self._active_tab_id = next(iter(self._tabs), None)
        return True

    async def save_tab(self, tab_id: str, content: str) -> dict:
        if tab_id not in self._tabs:
            return {"error": "Tab no encontrado"}
        tab = self._tabs[tab_id]
        tab.content = content
        tab.is_modified = False
        return {"tab_id": tab_id, "saved": True}

    async def switch_tab(self, tab_id: str) -> dict:
        if tab_id not in self._tabs:
            return {"error": "Tab no encontrado"}
        self._active_tab_id = tab_id
        tab = self._tabs[tab_id]
        return {"tab_id": tab_id, "content": tab.content, "language": tab.language}

    # ═══════════════════════════════════
    # IA FEATURES
    # ═══════════════════════════════════

    async def _explain_code(self, code: str) -> dict:
        """Usa IA para explicar código."""
        from src.ia.ollama_provider import OllamaProvider
        provider = OllamaProvider()
        response = await provider.generate(
            prompt=f"Explain this code concisely in Spanish:\n\n```\n{code}\n```",
            system="You are a code expert. Explain briefly in 3-5 sentences in Spanish.",
            temperature=0.3,
        )
        return {"explanation": response.content.strip()}

    async def _generate_code(self, prompt: str, language: str) -> dict:
        """Genera código desde prompt. Enriquece el system prompt con buenas prácticas."""
        from src.ia.ollama_provider import OllamaProvider

        # Buscar buenas prácticas relevantes de codigo:conocimiento + codigo:usuario
        memory_context = ""
        if self._memory_service:
            memory_context = await self._memory_service.get_code_context(
                f"{language} {prompt}", limit=3
            )

        system = f"You are a {language} expert. Return clean, working code only."
        if memory_context:
            system += (
                "\n\n[Best practices to apply in your code]\n"
                + memory_context
            )

        provider = OllamaProvider()
        response = await provider.generate(
            prompt=f"Generate {language} code for: {prompt}\nReturn only the code, no explanation.",
            system=system,
            temperature=0.5,
        )
        code = response.content.strip()

        # Guardar código generado exitoso en memoria
        if self._memory_service and code and not code.startswith("Error"):
            try:
                await self._memory_service.store_result(
                    content=f"Generé código {language}: {prompt}",
                    namespace="codigo:usuario",
                    memory_type="skill",
                    source="code_generation",
                    metadata={"language": language, "prompt": prompt,
                              "code_preview": code[:300]},
                )
            except Exception:
                pass

        return {"code": code, "language": language}

    async def _suggest_fix(self, code: str, error: str) -> dict:
        """Sugiere fix para un error. Usa buenas prácticas de código si hay memoria."""
        from src.ia.ollama_provider import OllamaProvider

        memory_context = ""
        if self._memory_service:
            memory_context = await self._memory_service.get_code_context(
                error or code[:200], limit=2
            )

        system = "You are a debugging expert. Return only the fixed code."
        if memory_context:
            system += (
                "\n\n[Relevant best practices]\n"
                + memory_context
            )

        provider = OllamaProvider()
        response = await provider.generate(
            prompt=f"Fix this code that has an error:\n\nCode:\n```\n{code}\n```\n\nError: {error}\n\nReturn only the fixed code.",
            system=system,
            temperature=0.3,
        )
        return {"fixed_code": response.content.strip(), "original_error": error}
