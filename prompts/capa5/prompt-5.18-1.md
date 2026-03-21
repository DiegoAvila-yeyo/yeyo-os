## ═══════════════════════════════════════
## MICRO-FASE 5.18 — MiniChat v2 (Node Context)
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 5.18-1 [VSCODE] — MiniChat v2 con contexto del nodo activo

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 5.18 de Capa 5 (Órganos): actualizar MiniChat a v2 con contexto del nodo activo.

CONTEXTO:
- Micro-fase 5.4 completada: MiniChat v1 (Q&A básico sobre imágenes)
- Evolución: v1(básico) → v2(contexto por nodo) → v3(acciones, 5.19)
- MiniChat v2: sabe en qué nodo está y ofrece ayuda contextual
- Desde Image Node: "Describe esta imagen", "Genera una variación"
- Desde Code Node: "Explica este código", "Encuentra bugs"
- Desde Video Node: "Transcribe este video", "Recorta del minuto X al Y"
- Contexto inyectado en system prompt de la IA
- Frontend: Next.js 14 + Tailwind + Zustand

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear estructura:
   mkdir -p src/minichat
   mkdir -p tests/unit/minichat

2. Crear archivo src/minichat/__init__.py:

   Ruta: ~/yeyo-os/src/minichat/__init__.py
   Contenido:
   from .service import MiniChatV2Service

3. Crear archivo src/minichat/service.py:

   Ruta: ~/yeyo-os/src/minichat/service.py
   Contenido:

   """
   YeyoOS — MiniChat v2 Service (Node Context)
   Micro-fase 5.18 — Capa 5: Órganos

   MiniChat v2: conoce el nodo activo y proporciona ayuda contextual.
   System prompt se adapta al nodo. Sugerencias contextuales.
   """

   from typing import Optional
   from dataclasses import dataclass, field
   from datetime import datetime, timezone


   # Contextos por tipo de nodo
   NODE_CONTEXTS: dict[str, dict] = {
       "chat": {
           "system_prompt": "Estás en el nodo de Chat de YeyoOS. Ayudas con conversaciones, "
                            "búsqueda de mensajes y exportación.",
           "suggestions": [
               "Busca en mis conversaciones anteriores",
               "Exporta esta conversación",
               "Crea una nueva conversación sobre...",
           ],
       },
       "image": {
           "system_prompt": "Estás en el nodo de Imagen de YeyoOS. Puedes describir imágenes, "
                            "generar variaciones y transformar imágenes.",
           "suggestions": [
               "Describe esta imagen",
               "Genera una variación de esta imagen",
               "Cambia el estilo a pixel art",
               "¿Qué objetos hay en la imagen?",
           ],
       },
       "video": {
           "system_prompt": "Estás en el nodo de Video de YeyoOS. Ayudas con edición de video "
                            "usando FFmpeg, subtítulos y TTS.",
           "suggestions": [
               "Recorta del minuto 2 al 5",
               "Transcribe este video",
               "Genera subtítulos",
               "Concatena estos videos",
           ],
       },
       "code": {
           "system_prompt": "Estás en el nodo de Código de YeyoOS. Ayudas con edición, "
                            "explicación, debugging y ejecución de código.",
           "suggestions": [
               "Explica este código",
               "Encuentra bugs en este código",
               "Ejecuta este código",
               "Genera un commit message",
           ],
       },
       "automation": {
           "system_prompt": "Estás en el nodo de Automatización de YeyoOS. Ayudas con "
                            "pipelines visuales y conexiones entre nodos.",
           "suggestions": [
               "Crea un pipeline que...",
               "Conecta estos pasos",
               "Valida este pipeline",
               "Programa una publicación",
           ],
       },
       "files": {
           "system_prompt": "Estás en el nodo de Archivos de YeyoOS. Ayudas con búsqueda "
                            "de archivos, organización y preview.",
           "suggestions": [
               "Busca mis documentos de impuestos",
               "Organiza esta carpeta",
               "¿Qué archivos grandes tengo?",
           ],
       },
       "browser": {
           "system_prompt": "Estás en el nodo de Browser de YeyoOS. Ayudas con navegación "
                            "web y resumen de páginas.",
           "suggestions": [
               "Resume esta página",
               "¿De qué trata este sitio?",
               "Guarda en marcadores",
           ],
       },
       "config": {
           "system_prompt": "Estás en el nodo de Configuración de YeyoOS. Ayudas con "
                            "ajustes del sistema, modelos y GPU.",
           "suggestions": [
               "¿Cuánta VRAM estoy usando?",
               "Descarga un nuevo modelo",
               "¿Qué modelos tengo instalados?",
           ],
       },
   }

   DEFAULT_CONTEXT = {
       "system_prompt": "Estás en YeyoOS, un OS AI-nativo. ¿En qué puedo ayudarte?",
       "suggestions": ["¿Qué puedo hacer aquí?"],
   }


   @dataclass
   class MiniChatV2Message:
       role: str
       content: str
       timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


   class MiniChatV2Service:
       """
       MiniChat v2 — chat contextual por nodo.
       Sabe en qué nodo está y adapta su comportamiento.
       """

       def __init__(self):
           self._messages: list[MiniChatV2Message] = []
           self._current_node_type: Optional[str] = None
           self._current_node_id: Optional[str] = None

       def set_context(self, node_type: str, node_id: str) -> dict:
           """Establece contexto del nodo activo."""
           self._current_node_type = node_type
           self._current_node_id = node_id
           self._messages.clear()

           context = NODE_CONTEXTS.get(node_type, DEFAULT_CONTEXT)
           return {
               "node_type": node_type,
               "suggestions": context["suggestions"],
               "greeting": f"MiniChat activo en nodo {node_type}. ¿En qué te ayudo?",
           }

       def get_suggestions(self) -> list[str]:
           """Retorna sugerencias contextuales."""
           context = NODE_CONTEXTS.get(self._current_node_type, DEFAULT_CONTEXT)
           return context["suggestions"]

       def get_system_prompt(self) -> str:
           """Retorna system prompt contextual."""
           context = NODE_CONTEXTS.get(self._current_node_type, DEFAULT_CONTEXT)
           return context["system_prompt"]

       async def send_message(self, message: str) -> dict:
           """Envía mensaje con contexto del nodo inyectado."""
           user_msg = MiniChatV2Message(role="user", content=message)
           self._messages.append(user_msg)

           system_prompt = self.get_system_prompt()

           from src.ia.ollama_provider import OllamaProvider
           provider = OllamaProvider()
           from src.ia.interfaces import IAMessage

           messages = [IAMessage(role="system", content=system_prompt)]
           for m in self._messages[-10:]:
               messages.append(IAMessage(role=m.role, content=m.content))

           response = await provider.chat(messages, temperature=0.7)

           assistant_msg = MiniChatV2Message(
               role="assistant", content=response.content
           )
           self._messages.append(assistant_msg)

           return {
               "response": response.content,
               "node_type": self._current_node_type,
               "suggestions": self.get_suggestions(),
           }

       def get_messages(self) -> list[dict]:
           return [
               {"role": m.role, "content": m.content, "timestamp": m.timestamp.isoformat()}
               for m in self._messages
           ]

       def clear(self) -> None:
           self._messages.clear()
           self._current_node_type = None
           self._current_node_id = None

4. Crear archivo frontend/src/components/minichat/MiniChatV2.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/minichat/MiniChatV2.tsx
   Contenido:

   /**
    * YeyoOS — MiniChat v2 (Node Context)
    * Micro-fase 5.18 — Capa 5: Órganos
    *
    * MiniChat contextual: sabe en qué nodo está y sugiere acciones relevantes.
    */

   'use client';

   import React, { useState, useRef, useEffect } from 'react';

   interface MiniChatV2Props {
     isOpen: boolean;
     nodeType: string;
     nodeId: string;
     messages: { role: string; content: string }[];
     suggestions: string[];
     onSend: (message: string) => void;
     onSuggestionClick: (suggestion: string) => void;
     onClose: () => void;
     isLoading?: boolean;
   }

   export default function MiniChatV2({
     isOpen, nodeType, nodeId, messages, suggestions,
     onSend, onSuggestionClick, onClose, isLoading = false,
   }: MiniChatV2Props) {
     const [input, setInput] = useState('');
     const messagesEndRef = useRef<HTMLDivElement>(null);

     useEffect(() => {
       messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
     }, [messages]);

     if (!isOpen) return null;

     const handleSend = () => {
       if (!input.trim() || isLoading) return;
       onSend(input.trim());
       setInput('');
     };

     return (
       <div className="fixed bottom-4 right-4 w-80 bg-gray-900 border border-gray-600
                       rounded-xl shadow-2xl flex flex-col z-50"
            style={{ maxHeight: '450px' }}>
         {/* Header with context */}
         <div className="flex items-center justify-between px-3 py-2
                         bg-gray-800 rounded-t-xl border-b border-gray-700">
           <div>
             <span className="text-sm font-medium text-gray-200">
               💬 MiniChat
             </span>
             <span className="text-[10px] text-gray-500 ml-2">
               📍 {nodeType}
             </span>
           </div>
           <button onClick={onClose} className="text-gray-400 hover:text-white text-xs">
             ✕
           </button>
         </div>

         {/* Suggestions */}
         {messages.length === 0 && (
           <div className="px-3 py-2 flex flex-wrap gap-1">
             {suggestions.map((s, i) => (
               <button
                 key={i}
                 onClick={() => onSuggestionClick(s)}
                 className="px-2 py-1 text-[10px] bg-gray-700 text-gray-300
                            rounded-full hover:bg-gray-600"
               >
                 {s}
               </button>
             ))}
           </div>
         )}

         {/* Messages */}
         <div className="flex-1 overflow-y-auto px-3 py-2 space-y-2"
              style={{ maxHeight: '300px' }}>
           {messages.map((msg, i) => (
             <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
               <div className={`max-w-[85%] px-2 py-1 rounded-lg text-xs
                 ${msg.role === 'user'
                   ? 'bg-blue-600 text-white'
                   : 'bg-gray-700 text-gray-200'}`}>
                 {msg.content}
               </div>
             </div>
           ))}
           {isLoading && (
             <div className="text-xs text-gray-400 animate-pulse">Pensando...</div>
           )}
           <div ref={messagesEndRef} />
         </div>

         {/* Input */}
         <div className="flex items-center gap-1 px-2 py-2 border-t border-gray-700">
           <input
             type="text"
             value={input}
             onChange={(e) => setInput(e.target.value)}
             onKeyDown={(e) => e.key === 'Enter' && handleSend()}
             placeholder={`Pregunta sobre ${nodeType}...`}
             className="flex-1 px-2 py-1 text-xs bg-gray-700 text-white rounded
                        border border-gray-600 focus:border-blue-500 focus:outline-none"
           />
           <button onClick={handleSend} disabled={!input.trim() || isLoading}
             className="px-2 py-1 bg-blue-600 text-white rounded text-xs disabled:opacity-50">
             →
           </button>
         </div>
       </div>
     );
   }

5. Crear archivo tests/unit/minichat/__init__.py (vacío):

   Ruta: ~/yeyo-os/tests/unit/minichat/__init__.py
   Contenido: (archivo vacío)

6. Crear archivo tests/unit/minichat/test_minichat_v2.py:

   Ruta: ~/yeyo-os/tests/unit/minichat/test_minichat_v2.py
   Contenido:

   """Tests para MiniChat v2 — Micro-fase 5.18"""

   import pytest
   from src.minichat.service import MiniChatV2Service, NODE_CONTEXTS, DEFAULT_CONTEXT


   class TestMiniChatV2Context:

       def test_set_context_changes_node_type(self):
           service = MiniChatV2Service()
           result = service.set_context("image", "node-123")
           assert result["node_type"] == "image"
           assert service._current_node_type == "image"

       def test_suggestions_change_per_node(self):
           service = MiniChatV2Service()
           service.set_context("image", "node-1")
           image_suggestions = service.get_suggestions()

           service.set_context("code", "node-2")
           code_suggestions = service.get_suggestions()

           assert image_suggestions != code_suggestions

       def test_image_node_has_describe_suggestion(self):
           service = MiniChatV2Service()
           service.set_context("image", "node-1")
           suggestions = service.get_suggestions()
           assert any("imagen" in s.lower() or "describe" in s.lower() for s in suggestions)

       def test_code_node_has_explain_suggestion(self):
           service = MiniChatV2Service()
           service.set_context("code", "node-1")
           suggestions = service.get_suggestions()
           assert any("código" in s.lower() or "explica" in s.lower() for s in suggestions)

       def test_video_node_has_trim_suggestion(self):
           service = MiniChatV2Service()
           service.set_context("video", "node-1")
           suggestions = service.get_suggestions()
           assert any("recorta" in s.lower() or "minuto" in s.lower() for s in suggestions)

       def test_unknown_node_uses_default(self):
           service = MiniChatV2Service()
           service.set_context("unknown_node", "node-1")
           suggestions = service.get_suggestions()
           assert suggestions == DEFAULT_CONTEXT["suggestions"]

       def test_system_prompt_includes_node_context(self):
           service = MiniChatV2Service()
           service.set_context("image", "node-1")
           prompt = service.get_system_prompt()
           assert "imagen" in prompt.lower() or "image" in prompt.lower()


   class TestMiniChatV2Messages:

       def test_clear_resets_state(self):
           service = MiniChatV2Service()
           service.set_context("image", "node-1")
           service._messages.append(
               MiniChatV2Service.__init__  # Dummy, just to have something
           )
           service.clear()
           assert service._current_node_type is None
           assert len(service._messages) == 0

       def test_all_node_contexts_defined(self):
           expected_nodes = {"chat", "image", "video", "code", "automation",
                             "files", "browser", "config"}
           assert expected_nodes.issubset(set(NODE_CONTEXTS.keys()))

       def test_each_context_has_suggestions(self):
           for node_type, context in NODE_CONTEXTS.items():
               assert "suggestions" in context, f"{node_type} missing suggestions"
               assert len(context["suggestions"]) > 0, f"{node_type} has no suggestions"

       def test_each_context_has_system_prompt(self):
           for node_type, context in NODE_CONTEXTS.items():
               assert "system_prompt" in context, f"{node_type} missing system_prompt"
               assert len(context["system_prompt"]) > 0

7. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/minichat/test_minichat_v2.py -v

VERIFICAR:
- [ ] Contexto cambia según el nodo activo
- [ ] Sugerencias son diferentes para cada nodo
- [ ] Image Node: sugerencias de imagen
- [ ] Code Node: sugerencias de código
- [ ] Video Node: sugerencias de video
- [ ] System prompt incluye contexto del nodo
- [ ] Nodo desconocido usa contexto default
- [ ] Todos los nodos principales tienen contexto definido
- [ ] TODOS los tests pasan

SI FALLA:
- Import error: verificar __init__.py
- NODE_CONTEXTS: verificar que todos los nodos están cubiertos

NO HACER:
- No implementar acciones ejecutables (eso es MiniChat v3, 5.19)
- No cambiar MiniChat v1 (es backward compatible)

GATE: MiniChat v2 contextual, sugerencias por nodo, system prompt adaptado, todos los nodos cubiertos, todos los tests pasan.
```
