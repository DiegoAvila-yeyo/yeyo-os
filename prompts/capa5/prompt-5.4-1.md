## ═══════════════════════════════════════
## MICRO-FASE 5.4 — Image Node MiniChat v1
## Tipo: VSCODE | Prompts: 1 | Complejidad: Simple
## ═══════════════════════════════════════

### PROMPT 5.4-1 [VSCODE] — MiniChat v1 básico para Image Node

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 5.4 de Capa 5 (Órganos): crear MiniChat v1, un overlay de chat básico que aparece al hacer click en una imagen generada.

CONTEXTO:
- Micro-fases 5.2-5.3 completadas: Image Generation + img2img + LLaVA analysis
- MiniChat v1 = primera versión, solo Q&A de texto sobre la imagen
- Click en imagen generada → MiniChat overlay aparece → preguntas sobre la imagen
- Usa LLaVA (ImageAnalysisService de 5.3) para responder sobre la imagen
- Evolución planificada: v1(básico) → v2(contexto por nodo, 5.18) → v3(acciones, 5.19)
- Frontend: Next.js 14 + Tailwind + Zustand

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear estructura:
   mkdir -p frontend/src/components/minichat
   mkdir -p src/nodes/image/minichat

2. Crear archivo src/nodes/image/minichat/__init__.py:

   Ruta: ~/yeyo-os/src/nodes/image/minichat/__init__.py
   Contenido:
   from .service import MiniChatV1Service

3. Crear archivo src/nodes/image/minichat/service.py:

   Ruta: ~/yeyo-os/src/nodes/image/minichat/service.py
   Contenido:

   """
   YeyoOS — MiniChat v1 Service
   Micro-fase 5.4 — Capa 5: Órganos

   Primera versión de MiniChat: Q&A básico sobre imágenes.
   Usa LLaVA para responder preguntas contextuales sobre la imagen.
   """

   from typing import Optional
   from dataclasses import dataclass, field
   from datetime import datetime, timezone

   from src.nodes.image.analysis import ImageAnalysisService


   @dataclass
   class MiniChatMessage:
       role: str  # "user" | "assistant"
       content: str
       timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


   class MiniChatV1Service:
       """
       MiniChat v1 — chat básico sobre imágenes.
       Click en imagen → overlay → preguntas sobre la imagen.
       """

       def __init__(self):
           self._analysis_service = ImageAnalysisService()
           self._messages: list[MiniChatMessage] = []
           self._image_data: Optional[bytes] = None
           self._image_description: Optional[str] = None

       async def open_for_image(self, image_data: bytes) -> dict:
           """Abre MiniChat para una imagen específica."""
           self._image_data = image_data
           self._messages.clear()

           # Generar descripción inicial
           result = await self._analysis_service.analyze(
               image_data, "Describe esta imagen brevemente."
           )

           if "error" not in result:
               self._image_description = result["description"]
               greeting = f"Estoy viendo tu imagen. {result['description'][:100]}... ¿Qué quieres saber?"
           else:
               self._image_description = None
               greeting = "No pude analizar la imagen, pero puedo intentar responder preguntas."

           assistant_msg = MiniChatMessage(role="assistant", content=greeting)
           self._messages.append(assistant_msg)

           return {"message": greeting, "model_used": result.get("model_used")}

       async def ask(self, question: str) -> dict:
           """Hace una pregunta sobre la imagen actual."""
           if self._image_data is None:
               return {"error": "No hay imagen abierta en MiniChat"}

           user_msg = MiniChatMessage(role="user", content=question)
           self._messages.append(user_msg)

           result = await self._analysis_service.analyze(
               self._image_data, question
           )

           if "error" not in result:
               answer = result["description"]
           else:
               answer = "No pude analizar la imagen para responder tu pregunta."

           assistant_msg = MiniChatMessage(role="assistant", content=answer)
           self._messages.append(assistant_msg)

           return {
               "answer": answer,
               "model_used": result.get("model_used"),
               "question": question,
           }

       def get_messages(self) -> list[dict]:
           """Retorna historial de mensajes."""
           return [
               {"role": m.role, "content": m.content, "timestamp": m.timestamp.isoformat()}
               for m in self._messages
           ]

       def close(self) -> None:
           """Cierra MiniChat."""
           self._messages.clear()
           self._image_data = None
           self._image_description = None

4. Crear archivo frontend/src/components/minichat/MiniChatOverlay.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/minichat/MiniChatOverlay.tsx
   Contenido:

   /**
    * YeyoOS — MiniChat v1 Overlay
    * Micro-fase 5.4 — Capa 5: Órganos
    *
    * Overlay de chat que aparece al hacer click en una imagen.
    * v1: Q&A básico sobre la imagen usando LLaVA.
    */

   'use client';

   import React, { useState, useRef, useEffect } from 'react';

   interface MiniChatMessage {
     role: 'user' | 'assistant';
     content: string;
     timestamp: string;
   }

   interface MiniChatOverlayProps {
     isOpen: boolean;
     imageId: string;
     messages: MiniChatMessage[];
     onAsk: (question: string) => void;
     onClose: () => void;
     isLoading?: boolean;
   }

   export default function MiniChatOverlay({
     isOpen,
     imageId,
     messages,
     onAsk,
     onClose,
     isLoading = false,
   }: MiniChatOverlayProps) {
     const [input, setInput] = useState('');
     const messagesEndRef = useRef<HTMLDivElement>(null);

     useEffect(() => {
       messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
     }, [messages]);

     if (!isOpen) return null;

     const handleSend = () => {
       if (!input.trim() || isLoading) return;
       onAsk(input.trim());
       setInput('');
     };

     return (
       <div className="fixed bottom-4 right-4 w-80 bg-gray-900 border border-gray-600
                       rounded-xl shadow-2xl flex flex-col z-50"
            style={{ maxHeight: '400px' }}>
         {/* Header */}
         <div className="flex items-center justify-between px-3 py-2
                         bg-gray-800 rounded-t-xl border-b border-gray-700">
           <span className="text-sm font-medium text-gray-200">
             💬 MiniChat — Imagen
           </span>
           <button
             onClick={onClose}
             className="text-gray-400 hover:text-white text-xs"
           >
             ✕
           </button>
         </div>

         {/* Messages */}
         <div className="flex-1 overflow-y-auto px-3 py-2 space-y-2"
              style={{ maxHeight: '280px' }}>
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
             <div className="text-xs text-gray-400 animate-pulse">Analizando...</div>
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
             placeholder="Pregunta sobre la imagen..."
             className="flex-1 px-2 py-1 text-xs bg-gray-700 text-white rounded
                        border border-gray-600 focus:border-blue-500 focus:outline-none"
           />
           <button
             onClick={handleSend}
             disabled={!input.trim() || isLoading}
             className="px-2 py-1 bg-blue-600 text-white rounded text-xs
                        disabled:opacity-50"
           >
             →
           </button>
         </div>
       </div>
     );
   }

5. Crear archivo tests/unit/nodes/image/test_minichat_v1.py:

   Ruta: ~/yeyo-os/tests/unit/nodes/image/test_minichat_v1.py
   Contenido:

   """Tests para MiniChat v1 — Micro-fase 5.4"""

   import pytest
   from unittest.mock import AsyncMock, MagicMock
   from src.nodes.image.minichat.service import MiniChatV1Service


   class TestMiniChatV1:

       @pytest.mark.asyncio
       async def test_open_generates_greeting(self):
           service = MiniChatV1Service()
           service._analysis_service.analyze = AsyncMock(return_value={
               "description": "A beautiful sunset over the ocean",
               "model_used": "llava:7b",
           })
           result = await service.open_for_image(b"fake_image")
           assert "message" in result
           assert len(service._messages) == 1

       @pytest.mark.asyncio
       async def test_ask_about_image(self):
           service = MiniChatV1Service()
           service._image_data = b"fake_image"
           service._analysis_service.analyze = AsyncMock(return_value={
               "description": "There are 3 cats in the image",
               "model_used": "llava:7b",
           })
           result = await service.ask("How many cats?")
           assert result["answer"] == "There are 3 cats in the image"
           assert result["question"] == "How many cats?"

       @pytest.mark.asyncio
       async def test_ask_without_image_returns_error(self):
           service = MiniChatV1Service()
           result = await service.ask("test question")
           assert "error" in result

       @pytest.mark.asyncio
       async def test_messages_stored(self):
           service = MiniChatV1Service()
           service._image_data = b"fake_image"
           service._analysis_service.analyze = AsyncMock(return_value={
               "description": "Response", "model_used": "llava:7b",
           })
           await service.ask("Q1")
           await service.ask("Q2")
           messages = service.get_messages()
           assert len(messages) == 4  # 2 user + 2 assistant

       def test_close_clears_state(self):
           service = MiniChatV1Service()
           service._image_data = b"fake"
           service._messages.append(MagicMock())
           service.close()
           assert service._image_data is None
           assert len(service._messages) == 0

6. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/nodes/image/test_minichat_v1.py -v

VERIFICAR:
- [ ] MiniChat se abre al hacer click en imagen
- [ ] Genera greeting descriptivo usando LLaVA
- [ ] Puede hacer preguntas sobre la imagen
- [ ] Respuestas son contextuales a la imagen
- [ ] Historial de mensajes se almacena
- [ ] Close limpia todo el estado
- [ ] Frontend: overlay con mensajes, input, botón cerrar
- [ ] TODOS los tests pasan

SI FALLA:
- Import error: verificar __init__.py
- ImageAnalysisService mock: verificar que analyze se mockea

NO HACER:
- No implementar contexto por nodo (eso es MiniChat v2, 5.18)
- No implementar acciones ejecutables (eso es MiniChat v3, 5.19)
- No hacer MiniChat resizable/draggable aún

GATE: MiniChat v1 abre sobre imagen, Q&A contextual funciona, historial almacenado, overlay frontend funcional, todos los tests pasan.
```
