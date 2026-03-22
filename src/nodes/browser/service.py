"""
YeyoOS — Browser Node
Micro-fase 5.13 — Capa 5: Órganos

Webview sandboxed con resumen de páginas por IA.
Seguridad: iframe sandboxed, sin acceso a internals del OS.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass, field

from src.nodes.base import NodeBase, PrivilegeLevel


@dataclass
class Bookmark:
    """Marcador."""
    id: str
    title: str
    url: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class HistoryEntry:
    """Entrada de historial."""
    url: str
    title: str
    visited_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class BrowserNode(NodeBase):
    """
    Nodo de Browser — órgano de navegación web de YeyoOS.
    Webview sandboxed con resumen de páginas por IA.
    """

    def __init__(self):
        super().__init__(
            name="Browser",
            version="1.0.0",
            privilege_level=PrivilegeLevel.SANDBOX,
            container_config={
                "memory_limit": "1g",
                "cpu_shares": 512,
                "sandbox": True,
            },
        )
        self._current_url: str = "about:blank"
        self._history: list[HistoryEntry] = []
        self._history_index: int = -1
        self._bookmarks: list[Bookmark] = []

    async def initialize(self) -> None:
        pass

    async def render_ui(self) -> dict:
        return {
            "component": "BrowserNode",
            "props": {
                "currentUrl": self._current_url,
                "canGoBack": self._history_index > 0,
                "canGoForward": self._history_index < len(self._history) - 1,
                "bookmarks": [
                    {"id": b.id, "title": b.title, "url": b.url}
                    for b in self._bookmarks
                ],
            },
        }

    async def process(self, input_data: dict) -> dict:
        action = input_data.get("action", "")

        if action == "navigate":
            return self._navigate(input_data.get("url", ""))
        elif action == "back":
            return self._go_back()
        elif action == "forward":
            return self._go_forward()
        elif action == "bookmark":
            return self._add_bookmark(
                input_data.get("title", ""), input_data.get("url", "")
            )
        elif action == "summarize":
            return await self._summarize_page(input_data.get("page_text", ""))
        else:
            return {"error": f"Acción desconocida: {action}"}

    async def cleanup(self) -> None:
        self._history.clear()
        self._bookmarks.clear()

    # ═══════════════════════════════════
    # NAVEGACIÓN
    # ═══════════════════════════════════

    def _navigate(self, url: str) -> dict:
        """Navega a una URL."""
        if not url.strip():
            return {"error": "URL vacía"}

        if not url.startswith(("http://", "https://", "about:")):
            url = f"https://{url}"

        entry = HistoryEntry(url=url, title=url)
        self._history_index += 1
        self._history = self._history[:self._history_index]
        self._history.append(entry)
        self._current_url = url

        return {"url": url, "navigated": True}

    def _go_back(self) -> dict:
        """Navega hacia atrás."""
        if self._history_index <= 0:
            return {"error": "No hay historial previo"}
        self._history_index -= 1
        entry = self._history[self._history_index]
        self._current_url = entry.url
        return {"url": entry.url, "navigated": True}

    def _go_forward(self) -> dict:
        """Navega hacia adelante."""
        if self._history_index >= len(self._history) - 1:
            return {"error": "No hay historial siguiente"}
        self._history_index += 1
        entry = self._history[self._history_index]
        self._current_url = entry.url
        return {"url": entry.url, "navigated": True}

    def _add_bookmark(self, title: str, url: str) -> dict:
        """Añade un bookmark."""
        if not url:
            url = self._current_url
        if not title:
            title = url
        bookmark = Bookmark(
            id=f"bm-{uuid.uuid4().hex[:8]}",
            title=title,
            url=url,
        )
        self._bookmarks.append(bookmark)
        return {"bookmark_id": bookmark.id, "title": title, "url": url}

    async def _summarize_page(self, page_text: str) -> dict:
        """Resume el contenido de la página con Ollama."""
        if not page_text.strip():
            return {"error": "No hay texto de página para resumir"}

        from src.ia.ollama_provider import OllamaProvider
        provider = OllamaProvider()
        response = await provider.generate(
            prompt=f"Resume este contenido de página web de forma concisa:\n\n{page_text[:3000]}",
            system="Eres un experto en resumir contenido web. "
                   "Genera un resumen claro, conciso y útil en español. "
                   "Máximo 3 párrafos.",
            temperature=0.5,
        )
        return {"summary": response.content, "url": self._current_url}
