## ═══════════════════════════════════════
## MICRO-FASE 5.13 — Browser Node
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 5.13-1 [VSCODE] — Webview embebido con resumen de páginas por IA

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 5.13 de Capa 5 (Órganos): crear el Browser Node con webview sandboxed y resumen de páginas con IA.

CONTEXTO:
- Micro-fases 5.0-5.12 completadas
- Webview via iframe o webview component
- URL bar, back/forward, bookmarks
- "Summarize this page" → Ollama resume texto visible
- Seguridad: iframe sandboxed, sin acceso a internals del OS
- Frontend: Next.js 14 + Tailwind + Zustand
- Backend: Python 3.11 + FastAPI + Ollama qwen2.5:3b

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear estructura:
   mkdir -p src/nodes/browser
   mkdir -p tests/unit/nodes/browser
   mkdir -p frontend/src/components/nodes/browser

2. Crear archivo src/nodes/browser/__init__.py:

   Ruta: ~/yeyo-os/src/nodes/browser/__init__.py
   Contenido:
   from .service import BrowserNode

3. Crear archivo src/nodes/browser/service.py:

   Ruta: ~/yeyo-os/src/nodes/browser/service.py
   Contenido:

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
           # Truncar forward history
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

4. Crear archivo frontend/src/components/nodes/browser/BrowserNode.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/nodes/browser/BrowserNode.tsx
   Contenido:

   /**
    * YeyoOS — Browser Node Frontend
    * Micro-fase 5.13 — Capa 5: Órganos
    *
    * Webview sandboxed con navegación y resumen IA.
    */

   'use client';

   import React, { useState } from 'react';
   import NodeWrapper from '../NodeWrapper';

   interface BrowserNodeProps {
     nodeId: string;
     currentUrl: string;
     canGoBack: boolean;
     canGoForward: boolean;
     bookmarks: { id: string; title: string; url: string }[];
     onNavigate: (url: string) => void;
     onBack: () => void;
     onForward: () => void;
     onBookmark: () => void;
     onSummarize: () => void;
     onClose: (nodeId: string) => void;
   }

   export default function BrowserNode({
     nodeId, currentUrl, canGoBack, canGoForward, bookmarks,
     onNavigate, onBack, onForward, onBookmark, onSummarize, onClose,
   }: BrowserNodeProps) {
     const [urlInput, setUrlInput] = useState(currentUrl);

     const handleNavigate = () => {
       if (urlInput.trim()) onNavigate(urlInput.trim());
     };

     return (
       <NodeWrapper nodeId={nodeId} title="Browser" icon="🌐" onClose={onClose}
                    initialWidth={800} initialHeight={600}>
         <div className="flex flex-col h-full">
           {/* Navigation bar */}
           <div className="flex items-center gap-2 px-2 py-2 bg-gray-800
                           border-b border-gray-700 shrink-0">
             <button onClick={onBack} disabled={!canGoBack}
               className="px-2 py-1 text-xs bg-gray-700 rounded disabled:opacity-30">
               ←
             </button>
             <button onClick={onForward} disabled={!canGoForward}
               className="px-2 py-1 text-xs bg-gray-700 rounded disabled:opacity-30">
               →
             </button>
             <input
               type="text"
               value={urlInput}
               onChange={(e) => setUrlInput(e.target.value)}
               onKeyDown={(e) => e.key === 'Enter' && handleNavigate()}
               className="flex-1 px-3 py-1 text-sm bg-gray-700 text-white
                          rounded-full border border-gray-600 focus:border-blue-500
                          focus:outline-none"
             />
             <button onClick={onBookmark}
               className="px-2 py-1 text-xs text-yellow-400 hover:text-yellow-300">
               ⭐
             </button>
             <button onClick={onSummarize}
               className="px-2 py-1 text-xs bg-blue-600 text-white rounded
                          hover:bg-blue-500">
               📝 Resumir
             </button>
           </div>

           {/* Sandboxed iframe */}
           <div className="flex-1 bg-white">
             <iframe
               src={currentUrl}
               className="w-full h-full border-none"
               sandbox="allow-scripts allow-same-origin allow-forms"
               title="Browser content"
               referrerPolicy="no-referrer"
             />
           </div>
         </div>
       </NodeWrapper>
     );
   }

5. Crear tests/unit/nodes/browser/__init__.py (vacío):

   Ruta: ~/yeyo-os/tests/unit/nodes/browser/__init__.py
   Contenido: (archivo vacío)

6. Crear archivo tests/unit/nodes/browser/test_browser_node.py:

   Ruta: ~/yeyo-os/tests/unit/nodes/browser/test_browser_node.py
   Contenido:

   """Tests para Browser Node — Micro-fase 5.13"""

   import pytest
   from unittest.mock import AsyncMock, patch, MagicMock
   from src.nodes.browser.service import BrowserNode


   class TestBrowserNavigation:

       def test_navigate_sets_url(self):
           node = BrowserNode()
           result = node._navigate("https://example.com")
           assert result["url"] == "https://example.com"
           assert node._current_url == "https://example.com"

       def test_navigate_adds_https(self):
           node = BrowserNode()
           result = node._navigate("example.com")
           assert result["url"] == "https://example.com"

       def test_navigate_empty_url_error(self):
           node = BrowserNode()
           result = node._navigate("")
           assert "error" in result

       def test_back_and_forward(self):
           node = BrowserNode()
           node._navigate("https://a.com")
           node._navigate("https://b.com")
           node._navigate("https://c.com")

           back_result = node._go_back()
           assert back_result["url"] == "https://b.com"

           forward_result = node._go_forward()
           assert forward_result["url"] == "https://c.com"

       def test_back_at_start_error(self):
           node = BrowserNode()
           result = node._go_back()
           assert "error" in result


   class TestBrowserBookmarks:

       def test_add_bookmark(self):
           node = BrowserNode()
           node._current_url = "https://example.com"
           result = node._add_bookmark("Example", "https://example.com")
           assert result["title"] == "Example"
           assert len(node._bookmarks) == 1


   class TestBrowserSummarize:

       @pytest.mark.asyncio
       async def test_summarize_page(self):
           node = BrowserNode()
           mock_provider = MagicMock()
           mock_provider.generate = AsyncMock(return_value=MagicMock(
               content="Esta página habla sobre tecnología."
           ))
           with patch("src.nodes.browser.service.OllamaProvider", return_value=mock_provider):
               result = await node._summarize_page("Lots of text about tech...")
               assert "summary" in result
               assert len(result["summary"]) > 0

       @pytest.mark.asyncio
       async def test_summarize_empty_text_error(self):
           node = BrowserNode()
           result = await node._summarize_page("")
           assert "error" in result

7. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/nodes/browser/test_browser_node.py -v

VERIFICAR:
- [ ] Navegación: URL, back, forward funcionan
- [ ] URLs sin https:// se completan automáticamente
- [ ] Bookmarks se añaden y listan
- [ ] Summarize genera resumen con Ollama
- [ ] iframe sandboxed en frontend (allow-scripts, allow-same-origin, allow-forms)
- [ ] Historial de navegación funciona correctamente
- [ ] TODOS los tests pasan

SI FALLA:
- Import error: verificar __init__.py
- OllamaProvider mock: verificar patch path

NO HACER:
- No permitir iframe sin sandbox
- No dar acceso al filesystem desde iframe
- No implementar extensiones de browser

GATE: BrowserNode con navegación, bookmarks, resumen IA, iframe sandboxed, historial back/forward, todos los tests pasan.
```
