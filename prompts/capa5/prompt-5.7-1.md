## ═══════════════════════════════════════
## MICRO-FASE 5.7 — Code Node (Editor)
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 5.7-1 [VSCODE] — Monaco editor con asistencia IA

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 5.7 de Capa 5 (Órganos): crear el Code Node con Monaco editor y asistencia IA.

CONTEXTO:
- Micro-fases 5.0-5.6 completadas: NodeBase, Chat, Image, Video
- Monaco editor via @monaco-editor/react
- Syntax highlighting, tabs múltiples, file tree
- IA: explicar código, sugerir fixes, generar código
- code-server lazy loaded (500MB-1GB RAM, solo cuando se abre)
- Frontend: Next.js 14 + Tailwind + Zustand
- Backend: Python 3.11 + FastAPI + Ollama qwen2.5:3b

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear estructura:
   mkdir -p src/nodes/code
   mkdir -p tests/unit/nodes/code
   mkdir -p frontend/src/components/nodes/code

2. Crear archivo src/nodes/code/__init__.py:

   Ruta: ~/yeyo-os/src/nodes/code/__init__.py
   Contenido:
   from .service import CodeNode

3. Crear archivo src/nodes/code/service.py:

   Ruta: ~/yeyo-os/src/nodes/code/service.py
   Contenido:

   """
   YeyoOS — Code Node
   Micro-fase 5.7 — Capa 5: Órganos

   Editor de código con Monaco + asistencia IA.
   IA: explicar, sugerir fixes, generar código.
   code-server lazy loaded (500MB-1GB RAM).
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


   @dataclass
   class CodeTab:
       """Tab de código abierto."""
       id: str
       filename: str
       language: str
       content: str
       is_modified: bool = False
       created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


   class CodeNode(NodeBase):
       """
       Nodo de Código — órgano de desarrollo de YeyoOS.
       Monaco editor con syntax highlighting, tabs y asistencia IA.
       """

       def __init__(self):
           super().__init__(
               name="Code",
               version="1.0.0",
               privilege_level=PrivilegeLevel.SANDBOX,
               container_config={
                   "memory_limit": "1g",
                   "cpu_shares": 768,
                   "lazy_load": True,  # code-server on demand
               },
           )
           self._tabs: dict[str, CodeTab] = {}
           self._active_tab_id: Optional[str] = None

       async def initialize(self) -> None:
           """Inicializa el Code Node."""
           pass  # code-server se carga lazy

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
                   "supportedLanguages": SUPPORTED_LANGUAGES,
               },
           }

       async def process(self, input_data: dict) -> dict:
           """Procesa acciones de código."""
           action = input_data.get("action", "")

           if action == "explain":
               return await self._ai_explain(input_data.get("code", ""))
           elif action == "fix":
               return await self._ai_suggest_fix(
                   input_data.get("code", ""), input_data.get("error", "")
               )
           elif action == "generate":
               return await self._ai_generate(
                   input_data.get("prompt", ""), input_data.get("language", "python")
               )
           elif action == "open_file":
               return self._open_tab(
                   input_data.get("filename", "untitled"),
                   input_data.get("content", ""),
                   input_data.get("language", "python"),
               )
           elif action == "save":
               return self._save_tab(
                   input_data.get("tab_id", ""), input_data.get("content", "")
               )
           else:
               return {"error": f"Acción desconocida: {action}"}

       async def cleanup(self) -> None:
           self._tabs.clear()
           self._active_tab_id = None

       # ═══════════════════════════════════
       # MÉTODOS ESPECÍFICOS
       # ═══════════════════════════════════

       def _open_tab(self, filename: str, content: str, language: str) -> dict:
           """Abre un nuevo tab de código."""
           tab = CodeTab(
               id=f"tab-{uuid.uuid4().hex[:8]}",
               filename=filename,
               language=language if language in SUPPORTED_LANGUAGES else "python",
               content=content,
           )
           self._tabs[tab.id] = tab
           self._active_tab_id = tab.id
           return {"tab_id": tab.id, "filename": filename, "language": tab.language}

       def _save_tab(self, tab_id: str, content: str) -> dict:
           """Guarda contenido de un tab."""
           if tab_id not in self._tabs:
               return {"error": "Tab no encontrado"}
           tab = self._tabs[tab_id]
           tab.content = content
           tab.is_modified = False
           return {"tab_id": tab_id, "saved": True}

       def close_tab(self, tab_id: str) -> dict:
           """Cierra un tab."""
           if tab_id not in self._tabs:
               return {"error": "Tab no encontrado"}
           del self._tabs[tab_id]
           if self._active_tab_id == tab_id:
               self._active_tab_id = next(iter(self._tabs), None)
           return {"closed": True}

       async def _ai_explain(self, code: str) -> dict:
           """IA explica el código."""
           from src.ia.ollama_provider import OllamaProvider
           provider = OllamaProvider()
           response = await provider.generate(
               prompt=f"Explica este código de forma clara y concisa:\n\n```\n{code}\n```",
               system="Eres un experto programador. Explica código de forma clara, "
                      "mencionando qué hace, cómo funciona y posibles mejoras. "
                      "Responde en español.",
               temperature=0.5,
           )
           return {"explanation": response.content}

       async def _ai_suggest_fix(self, code: str, error: str) -> dict:
           """IA sugiere fix para un error."""
           from src.ia.ollama_provider import OllamaProvider
           provider = OllamaProvider()
           response = await provider.generate(
               prompt=f"Este código tiene un error:\n\n```\n{code}\n```\n\nError: {error}\n\n"
                       f"Sugiere cómo arreglarlo.",
               system="Eres un experto debugger. Identifica el problema y sugiere "
                      "la corrección más simple. Muestra el código corregido. "
                      "Responde en español.",
               temperature=0.3,
           )
           return {"suggestion": response.content}

       async def _ai_generate(self, prompt: str, language: str) -> dict:
           """IA genera código desde prompt."""
           from src.ia.ollama_provider import OllamaProvider
           provider = OllamaProvider()
           response = await provider.generate(
               prompt=f"Genera código en {language}:\n{prompt}",
               system=f"Eres un experto en {language}. Genera código limpio, "
                      f"bien documentado y funcional. Solo retorna el código, "
                      f"sin explicaciones adicionales.",
               temperature=0.5,
           )
           return {"code": response.content, "language": language}

4. Crear archivo frontend/src/components/nodes/code/CodeNode.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/nodes/code/CodeNode.tsx
   Contenido:

   /**
    * YeyoOS — Code Node Frontend
    * Micro-fase 5.7 — Capa 5: Órganos
    *
    * Monaco editor con tabs, syntax highlighting y asistencia IA.
    */

   'use client';

   import React, { useState, useCallback } from 'react';
   import NodeWrapper from '../NodeWrapper';

   interface CodeTabInfo {
     id: string;
     filename: string;
     language: string;
     isModified: boolean;
   }

   interface CodeNodeProps {
     nodeId: string;
     tabs: CodeTabInfo[];
     activeTabId: string | null;
     supportedLanguages: string[];
     onSwitchTab: (tabId: string) => void;
     onCloseTab: (tabId: string) => void;
     onSave: (tabId: string, content: string) => void;
     onAiExplain: (code: string) => void;
     onAiFix: (code: string, error: string) => void;
     onAiGenerate: (prompt: string, language: string) => void;
     onClose: (nodeId: string) => void;
     editorContent?: string;
   }

   export default function CodeNode({
     nodeId,
     tabs,
     activeTabId,
     supportedLanguages,
     onSwitchTab,
     onCloseTab,
     onSave,
     onAiExplain,
     onAiFix,
     onAiGenerate,
     onClose,
     editorContent = '',
   }: CodeNodeProps) {
     const [content, setContent] = useState(editorContent);
     const [aiPrompt, setAiPrompt] = useState('');
     const [showAiPanel, setShowAiPanel] = useState(false);

     const handleSave = useCallback(() => {
       if (activeTabId) onSave(activeTabId, content);
     }, [activeTabId, content, onSave]);

     return (
       <NodeWrapper nodeId={nodeId} title="Code" icon="💻" onClose={onClose}
                    initialWidth={800} initialHeight={600}>
         <div className="flex flex-col h-full">
           {/* Tabs */}
           <div className="flex items-center gap-1 px-2 py-1 bg-gray-800
                           border-b border-gray-700 overflow-x-auto shrink-0">
             {tabs.map((tab) => (
               <div
                 key={tab.id}
                 className={`flex items-center gap-1 px-3 py-1 text-xs rounded-t
                   cursor-pointer group
                   ${tab.id === activeTabId
                     ? 'bg-gray-900 text-white'
                     : 'bg-gray-700 text-gray-400 hover:text-white'}`}
               >
                 <span onClick={() => onSwitchTab(tab.id)}>
                   {tab.isModified ? '● ' : ''}{tab.filename}
                 </span>
                 <button
                   onClick={(e) => { e.stopPropagation(); onCloseTab(tab.id); }}
                   className="opacity-0 group-hover:opacity-100 text-gray-500
                              hover:text-red-400 ml-1"
                 >
                   ×
                 </button>
               </div>
             ))}
           </div>

           {/* AI Toolbar */}
           <div className="flex items-center gap-2 px-2 py-1 bg-gray-850
                           border-b border-gray-700 shrink-0">
             <button
               onClick={() => onAiExplain(content)}
               className="px-2 py-1 text-xs bg-blue-600 text-white rounded
                          hover:bg-blue-500"
             >
               🤖 Explicar
             </button>
             <button
               onClick={() => setShowAiPanel(!showAiPanel)}
               className="px-2 py-1 text-xs bg-purple-600 text-white rounded
                          hover:bg-purple-500"
             >
               ✨ Generar
             </button>
             <button
               onClick={handleSave}
               className="px-2 py-1 text-xs bg-green-600 text-white rounded
                          hover:bg-green-500 ml-auto"
             >
               💾 Guardar
             </button>
           </div>

           {/* AI Generate Panel */}
           {showAiPanel && (
             <div className="flex items-center gap-2 px-2 py-1 bg-gray-800
                             border-b border-gray-700">
               <input
                 type="text"
                 value={aiPrompt}
                 onChange={(e) => setAiPrompt(e.target.value)}
                 placeholder="Describe qué código generar..."
                 className="flex-1 px-2 py-1 text-xs bg-gray-700 text-white
                            rounded border border-gray-600 focus:outline-none"
               />
               <button
                 onClick={() => {
                   if (aiPrompt.trim()) onAiGenerate(aiPrompt, 'python');
                   setAiPrompt('');
                 }}
                 className="px-2 py-1 text-xs bg-purple-600 text-white rounded"
               >
                 Generar
               </button>
             </div>
           )}

           {/* Editor area (Monaco placeholder — real Monaco loaded via @monaco-editor/react) */}
           <div className="flex-1 bg-gray-950 font-mono text-sm">
             <textarea
               value={content}
               onChange={(e) => setContent(e.target.value)}
               className="w-full h-full bg-transparent text-green-400 p-3
                          resize-none focus:outline-none font-mono"
               spellCheck={false}
               placeholder="// Monaco editor se carga aquí..."
             />
           </div>
         </div>
       </NodeWrapper>
     );
   }

5. Crear tests/unit/nodes/code/__init__.py (vacío):

   Ruta: ~/yeyo-os/tests/unit/nodes/code/__init__.py
   Contenido: (archivo vacío)

6. Crear archivo tests/unit/nodes/code/test_code_node.py:

   Ruta: ~/yeyo-os/tests/unit/nodes/code/test_code_node.py
   Contenido:

   """Tests para Code Node — Micro-fase 5.7"""

   import pytest
   from unittest.mock import AsyncMock, patch, MagicMock
   from src.nodes.code.service import CodeNode, SUPPORTED_LANGUAGES


   class TestCodeNodeLifecycle:

       def test_node_name(self):
           node = CodeNode()
           assert node.name == "Code"

       @pytest.mark.asyncio
       async def test_render_ui_has_languages(self):
           node = CodeNode()
           ui = await node.render_ui()
           assert "supportedLanguages" in ui["props"]
           assert "python" in ui["props"]["supportedLanguages"]


   class TestCodeNodeTabs:

       def test_open_tab(self):
           node = CodeNode()
           result = node._open_tab("test.py", "print('hi')", "python")
           assert result["filename"] == "test.py"
           assert len(node._tabs) == 1
           assert node._active_tab_id == result["tab_id"]

       def test_open_multiple_tabs(self):
           node = CodeNode()
           node._open_tab("a.py", "", "python")
           node._open_tab("b.js", "", "javascript")
           assert len(node._tabs) == 2

       def test_save_tab(self):
           node = CodeNode()
           result = node._open_tab("test.py", "old", "python")
           save_result = node._save_tab(result["tab_id"], "new content")
           assert save_result["saved"] is True
           assert node._tabs[result["tab_id"]].content == "new content"

       def test_close_tab(self):
           node = CodeNode()
           result = node._open_tab("test.py", "", "python")
           close_result = node.close_tab(result["tab_id"])
           assert close_result["closed"] is True
           assert len(node._tabs) == 0

       def test_invalid_language_defaults_to_python(self):
           node = CodeNode()
           result = node._open_tab("test.xyz", "", "fake_lang")
           assert node._tabs[result["tab_id"]].language == "python"


   class TestCodeNodeAI:

       @pytest.mark.asyncio
       async def test_ai_explain(self):
           node = CodeNode()
           mock_provider = MagicMock()
           mock_provider.generate = AsyncMock(return_value=MagicMock(
               content="Esta función suma dos números"
           ))
           with patch("src.nodes.code.service.OllamaProvider", return_value=mock_provider):
               result = await node._ai_explain("def add(a, b): return a + b")
               assert "explanation" in result
               assert len(result["explanation"]) > 0

       @pytest.mark.asyncio
       async def test_ai_generate(self):
           node = CodeNode()
           mock_provider = MagicMock()
           mock_provider.generate = AsyncMock(return_value=MagicMock(
               content="def fibonacci(n):\n    if n <= 1: return n\n    return fibonacci(n-1) + fibonacci(n-2)"
           ))
           with patch("src.nodes.code.service.OllamaProvider", return_value=mock_provider):
               result = await node._ai_generate("función fibonacci", "python")
               assert "code" in result
               assert result["language"] == "python"

7. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/nodes/code/test_code_node.py -v

VERIFICAR:
- [ ] CodeNode hereda de NodeBase
- [ ] Monaco editor placeholder en frontend
- [ ] Tabs: abrir, cerrar, guardar, cambiar
- [ ] Syntax highlighting por lenguaje
- [ ] IA: explicar código genera respuesta
- [ ] IA: generar código retorna código con lenguaje
- [ ] Lenguaje inválido defaults a Python
- [ ] TODOS los tests pasan

SI FALLA:
- Import error: verificar __init__.py
- OllamaProvider mock: verificar patch path
- @monaco-editor/react: es dependencia de frontend, no de tests

NO HACER:
- No instalar Monaco realmente (placeholder en tests)
- No implementar sandbox de ejecución (eso es 5.8)
- No implementar Git (eso es 5.9)
- No implementar code-server real

GATE: CodeNode con Monaco editor, tabs múltiples, asistencia IA (explicar, fix, generar), syntax highlighting, todos los tests pasan.
```
