## ═══════════════════════════════════════
## MICRO-FASE 5.1 — Chat Node
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 5.1-1 [VSCODE] — Nodo de Chat completo con multi-conversación

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 5.1 de Capa 5 (Órganos): crear el Chat Node, la interfaz completa de chat como nodo del sistema.

CONTEXTO:
- Micro-fase 5.0 completada: NodeBase abstracta con lifecycle, GPU, permisos
- Capa 2 tiene ContextualChatService para conversaciones con IA
- Capa 3 tiene ChatPanel con streaming display
- Frontend: Next.js 14 + Tailwind + Zustand
- Backend: Python 3.11 + FastAPI + Ollama qwen2.5:3b
- Hardware: GTX 1060 3GB VRAM, 16GB RAM

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear estructura de directorios:
   mkdir -p src/nodes/chat
   mkdir -p tests/unit/nodes/chat
   mkdir -p frontend/src/components/nodes/chat

2. Crear archivo src/nodes/chat/__init__.py:

   Ruta: ~/yeyo-os/src/nodes/chat/__init__.py
   Contenido:
   from .service import ChatNode

3. Crear archivo src/nodes/chat/service.py:

   Ruta: ~/yeyo-os/src/nodes/chat/service.py
   Contenido:

   """
   YeyoOS — Chat Node
   Micro-fase 5.1 — Capa 5: Órganos

   Nodo de chat completo: multi-conversación, búsqueda,
   export a markdown, placeholder de voz.
   Usa ContextualChatService de Capa 2.
   """

   import uuid
   from datetime import datetime, timezone
   from typing import Optional, AsyncIterator
   from dataclasses import dataclass, field

   from src.nodes.base import NodeBase, PrivilegeLevel


   @dataclass
   class ChatMessage:
       """Mensaje individual en una conversación."""
       id: str
       role: str  # "user" | "assistant" | "system"
       content: str
       timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


   @dataclass
   class Conversation:
       """Una conversación con historial de mensajes."""
       id: str
       title: str
       messages: list[ChatMessage] = field(default_factory=list)
       created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
       updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


   class ChatNode(NodeBase):
       """
       Nodo de Chat — órgano de comunicación con la IA.
       Multi-conversación, búsqueda, export, streaming.
       """

       def __init__(self):
           super().__init__(
               name="Chat",
               version="1.0.0",
               privilege_level=PrivilegeLevel.SANDBOX,
               container_config={"memory_limit": "512m", "cpu_shares": 512},
           )
           self._conversations: dict[str, Conversation] = {}
           self._active_conversation_id: Optional[str] = None

       async def initialize(self) -> None:
           """Inicializa el servicio de chat contextual."""
           default_conv = self._create_conversation("Nueva conversación")
           self._active_conversation_id = default_conv.id

       async def render_ui(self) -> dict:
           """Retorna configuración del componente React."""
           return {
               "component": "ChatNode",
               "props": {
                   "conversations": [
                       {"id": c.id, "title": c.title, "messageCount": len(c.messages)}
                       for c in self._conversations.values()
                   ],
                   "activeConversationId": self._active_conversation_id,
               },
           }

       async def process(self, input_data: dict) -> dict:
           """Procesa un mensaje del usuario y genera respuesta."""
           message = input_data.get("message", "")
           conv_id = input_data.get("conversation_id", self._active_conversation_id)

           if not conv_id or conv_id not in self._conversations:
               return {"error": "Conversación no encontrada"}

           conv = self._conversations[conv_id]

           user_msg = ChatMessage(
               id=f"msg-{uuid.uuid4().hex[:8]}",
               role="user",
               content=message,
           )
           conv.messages.append(user_msg)
           conv.updated_at = datetime.now(timezone.utc)

           from src.chat.contextual import ContextualChatService
           chat_service = ContextualChatService()
           response = await chat_service.send_message(message, context={
               "conversation_id": conv_id,
               "history": [
                   {"role": m.role, "content": m.content}
                   for m in conv.messages[-20:]  # Últimos 20 mensajes
               ],
           })

           assistant_msg = ChatMessage(
               id=f"msg-{uuid.uuid4().hex[:8]}",
               role="assistant",
               content=response.get("content", ""),
           )
           conv.messages.append(assistant_msg)
           conv.updated_at = datetime.now(timezone.utc)

           if len(conv.messages) == 2:
               conv.title = message[:50]

           return {
               "message": assistant_msg.content,
               "message_id": assistant_msg.id,
               "conversation_id": conv_id,
           }

       async def cleanup(self) -> None:
           """Limpia recursos del chat node."""
           self._conversations.clear()
           self._active_conversation_id = None

       # ═══════════════════════════════════
       # MÉTODOS ESPECÍFICOS DEL CHAT NODE
       # ═══════════════════════════════════

       def _create_conversation(self, title: str) -> Conversation:
           """Crea una nueva conversación."""
           conv = Conversation(
               id=f"conv-{uuid.uuid4().hex[:8]}",
               title=title,
           )
           self._conversations[conv.id] = conv
           return conv

       async def new_conversation(self, title: str = "Nueva conversación") -> dict:
           """Crea nueva conversación y la activa."""
           conv = self._create_conversation(title)
           self._active_conversation_id = conv.id
           return {"conversation_id": conv.id, "title": conv.title}

       async def switch_conversation(self, conversation_id: str) -> dict:
           """Cambia a otra conversación."""
           if conversation_id not in self._conversations:
               return {"error": "Conversación no encontrada"}
           self._active_conversation_id = conversation_id
           conv = self._conversations[conversation_id]
           return {
               "conversation_id": conv.id,
               "title": conv.title,
               "messages": [
                   {"id": m.id, "role": m.role, "content": m.content,
                    "timestamp": m.timestamp.isoformat()}
                   for m in conv.messages
               ],
           }

       async def search_messages(self, query: str) -> list[dict]:
           """Busca mensajes en todas las conversaciones."""
           results = []
           query_lower = query.lower()
           for conv in self._conversations.values():
               for msg in conv.messages:
                   if query_lower in msg.content.lower():
                       results.append({
                           "conversation_id": conv.id,
                           "conversation_title": conv.title,
                           "message_id": msg.id,
                           "role": msg.role,
                           "content": msg.content,
                           "timestamp": msg.timestamp.isoformat(),
                       })
           return results

       async def export_conversation(self, conversation_id: str) -> str:
           """Exporta una conversación a markdown."""
           if conversation_id not in self._conversations:
               raise ValueError("Conversación no encontrada")

           conv = self._conversations[conversation_id]
           lines = [f"# {conv.title}\n"]
           lines.append(f"*Exportado: {datetime.now(timezone.utc).isoformat()}*\n")
           lines.append("---\n")

           for msg in conv.messages:
               if msg.role == "user":
                   lines.append(f"**Usuario:** {msg.content}\n")
               elif msg.role == "assistant":
                   lines.append(f"**YeyoOS:** {msg.content}\n")
               lines.append("")

           return "\n".join(lines)

       async def delete_conversation(self, conversation_id: str) -> bool:
           """Elimina una conversación."""
           if conversation_id not in self._conversations:
               return False
           del self._conversations[conversation_id]
           if self._active_conversation_id == conversation_id:
               if self._conversations:
                   self._active_conversation_id = next(iter(self._conversations))
               else:
                   self._active_conversation_id = None
           return True

4. Crear archivo frontend/src/components/nodes/chat/ChatNode.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/nodes/chat/ChatNode.tsx
   Contenido:

   /**
    * YeyoOS — Chat Node Frontend
    * Micro-fase 5.1 — Capa 5: Órganos
    *
    * Chat completo con tabs de conversación, búsqueda,
    * export y botones de enviar/voz.
    */

   'use client';

   import React, { useState, useRef, useEffect, useCallback } from 'react';
   import NodeWrapper from '../NodeWrapper';

   interface Message {
     id: string;
     role: 'user' | 'assistant';
     content: string;
     timestamp: string;
   }

   interface ConversationTab {
     id: string;
     title: string;
     messageCount: number;
   }

   interface ChatNodeProps {
     nodeId: string;
     conversations: ConversationTab[];
     activeConversationId: string | null;
     onSendMessage: (message: string, conversationId: string) => void;
     onNewConversation: () => void;
     onSwitchConversation: (id: string) => void;
     onSearch: (query: string) => void;
     onExport: (conversationId: string) => void;
     onClose: (nodeId: string) => void;
     messages: Message[];
     isStreaming?: boolean;
   }

   export default function ChatNode({
     nodeId,
     conversations,
     activeConversationId,
     onSendMessage,
     onNewConversation,
     onSwitchConversation,
     onSearch,
     onExport,
     onClose,
     messages,
     isStreaming = false,
   }: ChatNodeProps) {
     const [input, setInput] = useState('');
     const [searchQuery, setSearchQuery] = useState('');
     const [showSearch, setShowSearch] = useState(false);
     const messagesEndRef = useRef<HTMLDivElement>(null);

     useEffect(() => {
       messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
     }, [messages]);

     const handleSend = useCallback(() => {
       if (!input.trim() || !activeConversationId) return;
       onSendMessage(input.trim(), activeConversationId);
       setInput('');
     }, [input, activeConversationId, onSendMessage]);

     const handleKeyDown = useCallback(
       (e: React.KeyboardEvent) => {
         if (e.key === 'Enter' && !e.shiftKey) {
           e.preventDefault();
           handleSend();
         }
       },
       [handleSend]
     );

     return (
       <NodeWrapper nodeId={nodeId} title="Chat" icon="💬" onClose={onClose}>
         <div className="flex flex-col h-full">
           {/* Conversation tabs */}
           <div className="flex items-center gap-1 px-2 py-1 bg-gray-800
                           border-b border-gray-700 overflow-x-auto shrink-0">
             {conversations.map((conv) => (
               <button
                 key={conv.id}
                 onClick={() => onSwitchConversation(conv.id)}
                 className={`px-3 py-1 text-xs rounded-t whitespace-nowrap
                   ${conv.id === activeConversationId
                     ? 'bg-gray-900 text-white'
                     : 'bg-gray-700 text-gray-400 hover:text-white'}`}
               >
                 {conv.title}
               </button>
             ))}
             <button
               onClick={onNewConversation}
               className="px-2 py-1 text-xs text-gray-400 hover:text-green-400"
             >
               +
             </button>
           </div>

           {/* Search bar */}
           {showSearch && (
             <div className="px-2 py-1 bg-gray-800 border-b border-gray-700">
               <input
                 type="text"
                 value={searchQuery}
                 onChange={(e) => setSearchQuery(e.target.value)}
                 onKeyDown={(e) => e.key === 'Enter' && onSearch(searchQuery)}
                 placeholder="Buscar mensajes..."
                 className="w-full px-2 py-1 text-sm bg-gray-700 text-white
                            rounded border border-gray-600 focus:border-blue-500
                            focus:outline-none"
               />
             </div>
           )}

           {/* Toolbar */}
           <div className="flex items-center gap-2 px-2 py-1 bg-gray-850
                           border-b border-gray-700 shrink-0">
             <button
               onClick={() => setShowSearch(!showSearch)}
               className="text-xs text-gray-400 hover:text-white"
               title="Buscar"
             >
               🔍
             </button>
             <button
               onClick={() => activeConversationId && onExport(activeConversationId)}
               className="text-xs text-gray-400 hover:text-white"
               title="Exportar a Markdown"
             >
               📥
             </button>
           </div>

           {/* Messages */}
           <div className="flex-1 overflow-y-auto px-3 py-2 space-y-3">
             {messages.map((msg) => (
               <div
                 key={msg.id}
                 className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
               >
                 <div
                   className={`max-w-[80%] px-3 py-2 rounded-lg text-sm
                     ${msg.role === 'user'
                       ? 'bg-blue-600 text-white'
                       : 'bg-gray-700 text-gray-200'}`}
                 >
                   {msg.content}
                 </div>
               </div>
             ))}
             {isStreaming && (
               <div className="flex justify-start">
                 <div className="bg-gray-700 px-3 py-2 rounded-lg text-sm text-gray-400">
                   <span className="animate-pulse">●●●</span>
                 </div>
               </div>
             )}
             <div ref={messagesEndRef} />
           </div>

           {/* Input */}
           <div className="flex items-center gap-2 px-3 py-2 bg-gray-800
                           border-t border-gray-700 shrink-0">
             <textarea
               value={input}
               onChange={(e) => setInput(e.target.value)}
               onKeyDown={handleKeyDown}
               placeholder="Escribe un mensaje..."
               rows={1}
               className="flex-1 px-3 py-2 text-sm bg-gray-700 text-white
                          rounded-lg border border-gray-600 focus:border-blue-500
                          focus:outline-none resize-none"
             />
             <button
               onClick={handleSend}
               disabled={!input.trim() || isStreaming}
               className="px-3 py-2 bg-blue-600 text-white rounded-lg text-sm
                          hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
             >
               Enviar
             </button>
             <button
               className="px-3 py-2 bg-gray-700 text-gray-400 rounded-lg text-sm
                          hover:text-white cursor-not-allowed"
               title="Voz (próximamente)"
               disabled
             >
               🎤
             </button>
           </div>
         </div>
       </NodeWrapper>
     );
   }

5. Crear archivo tests/unit/nodes/chat/__init__.py (vacío):

   Ruta: ~/yeyo-os/tests/unit/nodes/chat/__init__.py
   Contenido: (archivo vacío)

6. Crear archivo tests/unit/nodes/chat/test_chat_node.py:

   Ruta: ~/yeyo-os/tests/unit/nodes/chat/test_chat_node.py
   Contenido:

   """Tests para Chat Node — Micro-fase 5.1"""

   import pytest
   from unittest.mock import AsyncMock, patch, MagicMock
   from src.nodes.chat.service import ChatNode, Conversation, ChatMessage


   class TestChatNodeLifecycle:
       """Tests del lifecycle del Chat Node."""

       @pytest.mark.asyncio
       async def test_initialize_creates_default_conversation(self):
           node = ChatNode()
           await node.initialize()
           assert len(node._conversations) == 1
           assert node._active_conversation_id is not None

       @pytest.mark.asyncio
       async def test_render_ui_returns_component(self):
           node = ChatNode()
           await node.initialize()
           ui = await node.render_ui()
           assert ui["component"] == "ChatNode"
           assert "conversations" in ui["props"]

       @pytest.mark.asyncio
       async def test_cleanup_clears_conversations(self):
           node = ChatNode()
           await node.initialize()
           await node.cleanup()
           assert len(node._conversations) == 0
           assert node._active_conversation_id is None


   class TestChatNodeMultiConversation:
       """Tests de multi-conversación."""

       @pytest.mark.asyncio
       async def test_new_conversation_creates_tab(self):
           node = ChatNode()
           await node.initialize()
           result = await node.new_conversation("Test Conv")
           assert result["title"] == "Test Conv"
           assert len(node._conversations) == 2

       @pytest.mark.asyncio
       async def test_switch_conversation(self):
           node = ChatNode()
           await node.initialize()
           conv = await node.new_conversation("Segunda")
           result = await node.switch_conversation(conv["conversation_id"])
           assert node._active_conversation_id == conv["conversation_id"]

       @pytest.mark.asyncio
       async def test_switch_to_nonexistent_returns_error(self):
           node = ChatNode()
           await node.initialize()
           result = await node.switch_conversation("fake-id")
           assert "error" in result

       @pytest.mark.asyncio
       async def test_delete_conversation(self):
           node = ChatNode()
           await node.initialize()
           conv = await node.new_conversation("Para borrar")
           result = await node.delete_conversation(conv["conversation_id"])
           assert result is True
           assert conv["conversation_id"] not in node._conversations


   class TestChatNodeSearch:
       """Tests de búsqueda de mensajes."""

       @pytest.mark.asyncio
       async def test_search_finds_messages(self):
           node = ChatNode()
           await node.initialize()
           conv_id = node._active_conversation_id
           conv = node._conversations[conv_id]
           conv.messages.append(ChatMessage(
               id="msg-1", role="user", content="Hola mundo"
           ))
           conv.messages.append(ChatMessage(
               id="msg-2", role="assistant", content="Hola! Soy YeyoOS"
           ))
           results = await node.search_messages("mundo")
           assert len(results) == 1
           assert results[0]["content"] == "Hola mundo"

       @pytest.mark.asyncio
       async def test_search_case_insensitive(self):
           node = ChatNode()
           await node.initialize()
           conv_id = node._active_conversation_id
           conv = node._conversations[conv_id]
           conv.messages.append(ChatMessage(
               id="msg-1", role="user", content="PYTHON es genial"
           ))
           results = await node.search_messages("python")
           assert len(results) == 1


   class TestChatNodeExport:
       """Tests de export a markdown."""

       @pytest.mark.asyncio
       async def test_export_creates_markdown(self):
           node = ChatNode()
           await node.initialize()
           conv_id = node._active_conversation_id
           conv = node._conversations[conv_id]
           conv.title = "Test Export"
           conv.messages.append(ChatMessage(
               id="msg-1", role="user", content="Pregunta"
           ))
           conv.messages.append(ChatMessage(
               id="msg-2", role="assistant", content="Respuesta"
           ))
           md = await node.export_conversation(conv_id)
           assert "# Test Export" in md
           assert "**Usuario:** Pregunta" in md
           assert "**YeyoOS:** Respuesta" in md

       @pytest.mark.asyncio
       async def test_export_nonexistent_raises(self):
           node = ChatNode()
           await node.initialize()
           with pytest.raises(ValueError):
               await node.export_conversation("fake-id")

7. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/nodes/chat/test_chat_node.py -v

VERIFICAR:
- [ ] ChatNode hereda de NodeBase correctamente
- [ ] Multi-conversación: crear, cambiar, eliminar tabs
- [ ] Búsqueda funciona case-insensitive en todas las conversaciones
- [ ] Export genera markdown válido con formato correcto
- [ ] Frontend: ChatNode.tsx con tabs, mensajes, input, búsqueda, botón de voz (disabled)
- [ ] Streaming display con indicador de carga
- [ ] TODOS los tests pasan

SI FALLA:
- Import error: verificar que src/nodes/chat/__init__.py existe
- ContextualChatService: los tests de process necesitan mock (probar solo los métodos propios)
- pytest-asyncio: `pip install pytest-asyncio`

NO HACER:
- No implementar voice input real (solo placeholder)
- No conectar con ContextualChatService real en tests (usar mocks)
- No implementar MiniChat aquí (eso es 5.4/5.18/5.19)

GATE: ChatNode funcional con multi-conversación, búsqueda, export markdown, streaming display, todos los tests pasan.
```
