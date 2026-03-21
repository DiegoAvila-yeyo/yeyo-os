## ═══════════════════════════════════════
## MICRO-FASE 3.5 — Chat Panel
## Tipo: VSCODE | Prompts: 2 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 3.5-1 [VSCODE] — Panel de chat con streaming y renderizado Markdown

```
Estamos construyendo YeyoOS, un OS AI-nativo con interfaz Neural Hub. Esta es la micro-fase 3.5 de Capa 3 (Cuerpo): crear el panel de chat principal con soporte de streaming.

CONTEXTO:
- Micro-fases 3.0-3.4 completadas: Canvas, nodos, layout, conexiones
- El chat es el canal principal de comunicación con la IA
- Panel slide-in desde la derecha (400px de ancho)
- Streaming: batch flush cada 50ms (NO por carácter individual)
- Markdown rendering para respuestas de la IA
- Conecta a /api/v1/chat/stream via SSE (Server-Sent Events)
- Auto-scroll al recibir nuevos mensajes
- Stack: React + Tailwind CSS

Abre el directorio ~/yeyo-os/frontend en VS Code.

CREAR:

1. Instalar dependencias:
   cd ~/yeyo-os/frontend
   npm install react-markdown remark-gfm

2. Crear estructura de directorios:
   mkdir -p src/components/chat
   mkdir -p src/lib/store
   mkdir -p __tests__/components/chat

3. Crear archivo src/lib/store/chat-store.ts:

   Ruta: ~/yeyo-os/frontend/src/lib/store/chat-store.ts
   Contenido:

   /**
    * YeyoOS — Chat Store (Estado del Chat)
    * Micro-fase 3.5 — Capa 3: Cuerpo
    */

   import { create } from 'zustand';

   export interface ChatMessage {
     id: string;
     role: 'user' | 'assistant' | 'system';
     content: string;
     timestamp: number;
     isStreaming?: boolean;
   }

   export interface ChatState {
     messages: ChatMessage[];
     isStreaming: boolean;
     isPanelOpen: boolean;
     error: string | null;

     addMessage: (message: ChatMessage) => void;
     updateStreamingMessage: (id: string, content: string) => void;
     finalizeStreamingMessage: (id: string) => void;
     setStreaming: (streaming: boolean) => void;
     setPanelOpen: (open: boolean) => void;
     togglePanel: () => void;
     setError: (error: string | null) => void;
     clearMessages: () => void;
   }

   export const useChatStore = create<ChatState>((set) => ({
     messages: [],
     isStreaming: false,
     isPanelOpen: false,
     error: null,

     addMessage: (message) =>
       set((state) => ({
         messages: [...state.messages, message],
       })),

     updateStreamingMessage: (id, content) =>
       set((state) => ({
         messages: state.messages.map((m) =>
           m.id === id ? { ...m, content } : m
         ),
       })),

     finalizeStreamingMessage: (id) =>
       set((state) => ({
         messages: state.messages.map((m) =>
           m.id === id ? { ...m, isStreaming: false } : m
         ),
         isStreaming: false,
       })),

     setStreaming: (streaming) => set({ isStreaming: streaming }),
     setPanelOpen: (open) => set({ isPanelOpen: open }),
     togglePanel: () => set((state) => ({ isPanelOpen: !state.isPanelOpen })),
     setError: (error) => set({ error }),
     clearMessages: () => set({ messages: [] }),
   }));

4. Crear archivo src/components/chat/ChatPanel.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/chat/ChatPanel.tsx
   Contenido:

   /**
    * YeyoOS — ChatPanel (Panel de Chat Principal)
    * Micro-fase 3.5 — Capa 3: Cuerpo
    *
    * Panel slide-in con chat streaming, markdown rendering
    * y batch flush de 50ms.
    */

   'use client';

   import { useState, useRef, useEffect, useCallback, type FormEvent, type KeyboardEvent } from 'react';
   import ReactMarkdown from 'react-markdown';
   import remarkGfm from 'remark-gfm';
   import { useChatStore, type ChatMessage } from '@/lib/store/chat-store';

   const PANEL_WIDTH = 400;
   const BATCH_FLUSH_MS = 50;

   function generateId(): string {
     return `msg-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
   }

   function MessageBubble({ message }: { message: ChatMessage }) {
     const isUser = message.role === 'user';

     return (
       <div
         data-testid={`message-${message.id}`}
         className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}
       >
         <div
           className={`max-w-[85%] rounded-xl px-4 py-2.5 text-sm ${
             isUser
               ? 'bg-blue-600 text-white rounded-br-sm'
               : 'bg-[#1a1a2e] text-gray-200 rounded-bl-sm border border-[#333355]'
           }`}
         >
           {isUser ? (
             <p className="whitespace-pre-wrap">{message.content}</p>
           ) : (
             <div className="prose prose-invert prose-sm max-w-none">
               <ReactMarkdown remarkPlugins={[remarkGfm]}>
                 {message.content}
               </ReactMarkdown>
             </div>
           )}
           {message.isStreaming && (
             <span
               data-testid="streaming-indicator"
               className="inline-block w-2 h-4 bg-blue-400 animate-pulse ml-1"
             />
           )}
         </div>
       </div>
     );
   }

   function LoadingIndicator() {
     return (
       <div data-testid="loading-indicator" className="flex justify-start mb-3">
         <div className="bg-[#1a1a2e] rounded-xl px-4 py-3 border border-[#333355]">
           <div className="flex space-x-1.5">
             <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
             <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
             <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
           </div>
         </div>
       </div>
     );
   }

   export default function ChatPanel() {
     const [input, setInput] = useState('');
     const messagesEndRef = useRef<HTMLDivElement>(null);
     const inputRef = useRef<HTMLInputElement>(null);
     const abortControllerRef = useRef<AbortController | null>(null);

     const {
       messages,
       isStreaming,
       isPanelOpen,
       error,
       addMessage,
       updateStreamingMessage,
       finalizeStreamingMessage,
       setStreaming,
       setError,
     } = useChatStore();

     const scrollToBottom = useCallback(() => {
       messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
     }, []);

     useEffect(() => {
       scrollToBottom();
     }, [messages, scrollToBottom]);

     useEffect(() => {
       if (isPanelOpen) {
         inputRef.current?.focus();
       }
     }, [isPanelOpen]);

     const sendMessage = useCallback(
       async (text: string) => {
         if (!text.trim() || isStreaming) return;

         const userMessage: ChatMessage = {
           id: generateId(),
           role: 'user',
           content: text.trim(),
           timestamp: Date.now(),
         };
         addMessage(userMessage);
         setInput('');
         setError(null);
         setStreaming(true);

         const assistantId = generateId();
         const assistantMessage: ChatMessage = {
           id: assistantId,
           role: 'assistant',
           content: '',
           timestamp: Date.now(),
           isStreaming: true,
         };
         addMessage(assistantMessage);

         try {
           abortControllerRef.current = new AbortController();

           const response = await fetch('/api/v1/chat/stream', {
             method: 'POST',
             headers: { 'Content-Type': 'application/json' },
             body: JSON.stringify({ message: text.trim() }),
             signal: abortControllerRef.current.signal,
           });

           if (!response.ok) {
             throw new Error(`Error ${response.status}: ${response.statusText}`);
           }

           const reader = response.body?.getReader();
           if (!reader) throw new Error('No response body');

           const decoder = new TextDecoder();
           let buffer = '';
           let fullContent = '';
           let flushTimer: ReturnType<typeof setTimeout> | null = null;

           const flushBuffer = () => {
             if (buffer) {
               fullContent += buffer;
               updateStreamingMessage(assistantId, fullContent);
               buffer = '';
             }
             flushTimer = null;
           };

           while (true) {
             const { done, value } = await reader.read();
             if (done) break;

             const chunk = decoder.decode(value, { stream: true });
             buffer += chunk;

             if (!flushTimer) {
               flushTimer = setTimeout(flushBuffer, BATCH_FLUSH_MS);
             }
           }

           if (flushTimer) clearTimeout(flushTimer);
           flushBuffer();
           finalizeStreamingMessage(assistantId);
         } catch (err) {
           if ((err as Error).name === 'AbortError') return;
           setError((err as Error).message);
           finalizeStreamingMessage(assistantId);
         }
       },
       [isStreaming, addMessage, updateStreamingMessage, finalizeStreamingMessage, setStreaming, setError]
     );

     const handleSubmit = (e: FormEvent) => {
       e.preventDefault();
       sendMessage(input);
     };

     const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
       if (e.key === 'Enter' && !e.shiftKey) {
         e.preventDefault();
         sendMessage(input);
       }
     };

     if (!isPanelOpen) return null;

     return (
       <div
         data-testid="chat-panel"
         className="fixed top-0 right-0 h-full bg-[#0d0d14] border-l border-[#1a1a2e] shadow-2xl flex flex-col z-50 animate-slide-in-right"
         style={{ width: `${PANEL_WIDTH}px` }}
       >
         <div className="flex items-center justify-between px-4 py-3 border-b border-[#1a1a2e]">
           <h2 className="text-white font-semibold text-sm">💬 Chat — YeyoOS</h2>
           <button
             data-testid="close-panel"
             onClick={() => useChatStore.getState().setPanelOpen(false)}
             className="text-gray-400 hover:text-white transition-colors text-lg"
           >
             ✕
           </button>
         </div>

         <div className="flex-1 overflow-y-auto px-4 py-3 scrollbar-thin scrollbar-thumb-[#333355]">
           {messages.map((msg) => (
             <MessageBubble key={msg.id} message={msg} />
           ))}
           {isStreaming && messages[messages.length - 1]?.role !== 'assistant' && (
             <LoadingIndicator />
           )}
           <div ref={messagesEndRef} />
         </div>

         {error && (
           <div data-testid="chat-error" className="px-4 py-2 bg-red-900/30 border-t border-red-800 text-red-300 text-xs">
             {error}
           </div>
         )}

         <form
           onSubmit={handleSubmit}
           className="flex items-center gap-2 px-4 py-3 border-t border-[#1a1a2e]"
         >
           <input
             ref={inputRef}
             data-testid="chat-input"
             type="text"
             value={input}
             onChange={(e) => setInput(e.target.value)}
             onKeyDown={handleKeyDown}
             placeholder="Escribe un mensaje..."
             disabled={isStreaming}
             className="flex-1 bg-[#1a1a2e] text-gray-200 rounded-lg px-3 py-2 text-sm placeholder-gray-500 border border-[#333355] focus:border-blue-500 focus:outline-none disabled:opacity-50"
           />
           <button
             data-testid="send-button"
             type="submit"
             disabled={isStreaming || !input.trim()}
             className="bg-blue-600 text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
           >
             Enviar
           </button>
         </form>
       </div>
     );
   }

   export { PANEL_WIDTH, BATCH_FLUSH_MS, MessageBubble, LoadingIndicator, generateId };

5. Ejecutar verificación de tipos:
   cd ~/yeyo-os/frontend
   npx tsc --noEmit --strict src/components/chat/ChatPanel.tsx 2>&1 || true

VERIFICAR:
- [ ] Archivo src/components/chat/ChatPanel.tsx existe
- [ ] Archivo src/lib/store/chat-store.ts existe
- [ ] Panel slide-in de 400px desde la derecha
- [ ] Mensajes de usuario y asistente con estilos distintos
- [ ] Streaming con batch flush de 50ms
- [ ] Markdown rendering con react-markdown
- [ ] Input con Enter para enviar
- [ ] Loading indicator mientras la IA piensa
- [ ] Auto-scroll al recibir mensajes
- [ ] Botón de cerrar panel

SI FALLA:
- react-markdown no instalado: npm install react-markdown remark-gfm
- Import error: verificar paths en tsconfig
- Zustand error: npm install zustand

NO HACER:
- No implementar historial de conversaciones (micro-fase futura)
- No agregar autenticación al chat
- No optimizar re-renders prematuramente
- No agregar temas claros (solo dark mode)

GATE: ChatPanel renderiza, streaming con batch flush 50ms, markdown funciona, auto-scroll, Enter envía, tests en prompt 3.5-2.
```
