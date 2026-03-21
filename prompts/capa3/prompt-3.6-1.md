## ═══════════════════════════════════════
## MICRO-FASE 3.6 — MiniChat Overlay
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 3.6-1 [VSCODE] — Widget flotante de MiniChat con Ctrl+Space

```
Estamos construyendo YeyoOS, un OS AI-nativo con interfaz Neural Hub. Esta es la micro-fase 3.6 de Capa 3 (Cuerpo): crear el MiniChat overlay, un widget flotante para chat rápido.

CONTEXTO:
- Micro-fase 3.5 completada: ChatPanel con streaming y ChatStore
- MiniChat es un widget compacto (300x200px) flotante sobre el canvas
- Draggable, resizable (mínimo 250x150, máximo 500x400)
- Muestra los últimos 3 mensajes
- Click en "expandir" abre el ChatPanel completo
- Keyboard shortcut: Ctrl+Space para toggle
- Reutiliza el ChatStore de micro-fase 3.5

Abre el directorio ~/yeyo-os/frontend en VS Code.

CREAR:

1. Crear archivo src/components/chat/MiniChat.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/chat/MiniChat.tsx
   Contenido:

   /**
    * YeyoOS — MiniChat (Widget Flotante de Chat Rápido)
    * Micro-fase 3.6 — Capa 3: Cuerpo
    *
    * Widget compacto flotante sobre el canvas.
    * Ctrl+Space para toggle. Click expandir para ChatPanel.
    */

   'use client';

   import { useState, useRef, useEffect, useCallback, type FormEvent, type KeyboardEvent } from 'react';
   import { useChatStore } from '@/lib/store/chat-store';

   const DEFAULT_WIDTH = 300;
   const DEFAULT_HEIGHT = 200;
   const MIN_WIDTH = 250;
   const MIN_HEIGHT = 150;
   const MAX_WIDTH = 500;
   const MAX_HEIGHT = 400;
   const MAX_VISIBLE_MESSAGES = 3;

   export interface MiniChatProps {
     initialX?: number;
     initialY?: number;
   }

   export default function MiniChat({ initialX = 20, initialY = 20 }: MiniChatProps) {
     const [isVisible, setIsVisible] = useState(false);
     const [position, setPosition] = useState({ x: initialX, y: initialY });
     const [size, setSize] = useState({ width: DEFAULT_WIDTH, height: DEFAULT_HEIGHT });
     const [isDragging, setIsDragging] = useState(false);
     const [isResizing, setIsResizing] = useState(false);
     const [input, setInput] = useState('');

     const dragOffsetRef = useRef({ x: 0, y: 0 });
     const resizeStartRef = useRef({ x: 0, y: 0, w: 0, h: 0 });
     const containerRef = useRef<HTMLDivElement>(null);

     const { messages, isStreaming, addMessage, setPanelOpen } = useChatStore();
     const visibleMessages = messages.slice(-MAX_VISIBLE_MESSAGES);

     useEffect(() => {
       const handleKeyDown = (e: globalThis.KeyboardEvent) => {
         if (e.ctrlKey && e.code === 'Space') {
           e.preventDefault();
           setIsVisible((prev) => !prev);
         }
       };
       window.addEventListener('keydown', handleKeyDown);
       return () => window.removeEventListener('keydown', handleKeyDown);
     }, []);

     const handleDragStart = useCallback(
       (e: React.MouseEvent) => {
         if ((e.target as HTMLElement).dataset.resize) return;
         setIsDragging(true);
         dragOffsetRef.current = {
           x: e.clientX - position.x,
           y: e.clientY - position.y,
         };
       },
       [position]
     );

     useEffect(() => {
       if (!isDragging) return;

       const handleMove = (e: MouseEvent) => {
         setPosition({
           x: Math.max(0, e.clientX - dragOffsetRef.current.x),
           y: Math.max(0, e.clientY - dragOffsetRef.current.y),
         });
       };
       const handleUp = () => setIsDragging(false);

       window.addEventListener('mousemove', handleMove);
       window.addEventListener('mouseup', handleUp);
       return () => {
         window.removeEventListener('mousemove', handleMove);
         window.removeEventListener('mouseup', handleUp);
       };
     }, [isDragging]);

     const handleResizeStart = useCallback(
       (e: React.MouseEvent) => {
         e.stopPropagation();
         setIsResizing(true);
         resizeStartRef.current = {
           x: e.clientX,
           y: e.clientY,
           w: size.width,
           h: size.height,
         };
       },
       [size]
     );

     useEffect(() => {
       if (!isResizing) return;

       const handleMove = (e: MouseEvent) => {
         const ref = resizeStartRef.current;
         setSize({
           width: Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, ref.w + (e.clientX - ref.x))),
           height: Math.min(MAX_HEIGHT, Math.max(MIN_HEIGHT, ref.h + (e.clientY - ref.y))),
         });
       };
       const handleUp = () => setIsResizing(false);

       window.addEventListener('mousemove', handleMove);
       window.addEventListener('mouseup', handleUp);
       return () => {
         window.removeEventListener('mousemove', handleMove);
         window.removeEventListener('mouseup', handleUp);
       };
     }, [isResizing]);

     const handleExpand = useCallback(() => {
       setIsVisible(false);
       setPanelOpen(true);
     }, [setPanelOpen]);

     const handleSend = useCallback(
       (e: FormEvent) => {
         e.preventDefault();
         if (!input.trim() || isStreaming) return;
         addMessage({
           id: `mini-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
           role: 'user',
           content: input.trim(),
           timestamp: Date.now(),
         });
         setInput('');
       },
       [input, isStreaming, addMessage]
     );

     const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
       if (e.key === 'Enter' && !e.shiftKey) {
         e.preventDefault();
         handleSend(e as unknown as FormEvent);
       }
     };

     if (!isVisible) return null;

     return (
       <div
         ref={containerRef}
         data-testid="minichat"
         className="fixed bg-[#0d0d14] border border-[#333355] rounded-xl shadow-2xl flex flex-col z-[60] select-none"
         style={{
           left: `${position.x}px`,
           top: `${position.y}px`,
           width: `${size.width}px`,
           height: `${size.height}px`,
         }}
       >
         <div
           data-testid="minichat-header"
           className="flex items-center justify-between px-3 py-2 border-b border-[#1a1a2e] cursor-move"
           onMouseDown={handleDragStart}
         >
           <span className="text-gray-300 text-xs font-medium">⚡ MiniChat</span>
           <div className="flex gap-2">
             <button
               data-testid="minichat-expand"
               onClick={handleExpand}
               className="text-gray-400 hover:text-blue-400 text-xs transition-colors"
               title="Expandir a ChatPanel"
             >
               ⤢
             </button>
             <button
               data-testid="minichat-close"
               onClick={() => setIsVisible(false)}
               className="text-gray-400 hover:text-white text-xs transition-colors"
             >
               ✕
             </button>
           </div>
         </div>

         <div className="flex-1 overflow-y-auto px-3 py-2 text-xs space-y-1.5">
           {visibleMessages.length === 0 ? (
             <p className="text-gray-500 text-center mt-4">Sin mensajes aún</p>
           ) : (
             visibleMessages.map((msg) => (
               <div
                 key={msg.id}
                 data-testid={`minichat-msg-${msg.id}`}
                 className={`rounded px-2 py-1 ${
                   msg.role === 'user'
                     ? 'bg-blue-600/20 text-blue-200 text-right'
                     : 'bg-[#1a1a2e] text-gray-300'
                 }`}
               >
                 <p className="truncate">{msg.content}</p>
               </div>
             ))
           )}
         </div>

         <form
           onSubmit={handleSend}
           className="flex items-center gap-1.5 px-3 py-2 border-t border-[#1a1a2e]"
         >
           <input
             data-testid="minichat-input"
             type="text"
             value={input}
             onChange={(e) => setInput(e.target.value)}
             onKeyDown={handleKeyDown}
             placeholder="Mensaje rápido..."
             disabled={isStreaming}
             className="flex-1 bg-[#1a1a2e] text-gray-200 rounded px-2 py-1 text-xs placeholder-gray-500 border border-[#333355] focus:border-blue-500 focus:outline-none disabled:opacity-50"
           />
           <button
             data-testid="minichat-send"
             type="submit"
             disabled={isStreaming || !input.trim()}
             className="bg-blue-600 text-white rounded px-2 py-1 text-xs hover:bg-blue-500 disabled:opacity-40 transition-colors"
           >
             ➤
           </button>
         </form>

         <div
           data-resize="true"
           data-testid="minichat-resize"
           onMouseDown={handleResizeStart}
           className="absolute bottom-0 right-0 w-4 h-4 cursor-se-resize"
         />
       </div>
     );
   }

   export { DEFAULT_WIDTH, DEFAULT_HEIGHT, MIN_WIDTH, MIN_HEIGHT, MAX_WIDTH, MAX_HEIGHT, MAX_VISIBLE_MESSAGES };

2. Crear archivo __tests__/components/chat/MiniChat.test.tsx:

   Ruta: ~/yeyo-os/frontend/__tests__/components/chat/MiniChat.test.tsx
   Contenido:

   /**
    * Tests para MiniChat — Micro-fase 3.6
    */

   import { render, screen, fireEvent, act } from '@testing-library/react';
   import MiniChat, {
     DEFAULT_WIDTH,
     DEFAULT_HEIGHT,
     MAX_VISIBLE_MESSAGES,
   } from '@/components/chat/MiniChat';
   import { useChatStore } from '@/lib/store/chat-store';

   describe('MiniChat', () => {
     beforeEach(() => {
       act(() => {
         useChatStore.setState({
           messages: [],
           isStreaming: false,
           isPanelOpen: false,
           error: null,
         });
       });
     });

     describe('visibility', () => {
       it('no es visible por defecto', () => {
         render(<MiniChat />);
         expect(screen.queryByTestId('minichat')).not.toBeInTheDocument();
       });

       it('toggle con Ctrl+Space', () => {
         render(<MiniChat />);
         fireEvent.keyDown(window, { key: ' ', code: 'Space', ctrlKey: true });
         expect(screen.getByTestId('minichat')).toBeInTheDocument();
       });

       it('segundo Ctrl+Space lo oculta', () => {
         render(<MiniChat />);
         fireEvent.keyDown(window, { key: ' ', code: 'Space', ctrlKey: true });
         expect(screen.getByTestId('minichat')).toBeInTheDocument();
         fireEvent.keyDown(window, { key: ' ', code: 'Space', ctrlKey: true });
         expect(screen.queryByTestId('minichat')).not.toBeInTheDocument();
       });

       it('botón cerrar lo oculta', () => {
         render(<MiniChat />);
         fireEvent.keyDown(window, { key: ' ', code: 'Space', ctrlKey: true });
         fireEvent.click(screen.getByTestId('minichat-close'));
         expect(screen.queryByTestId('minichat')).not.toBeInTheDocument();
       });
     });

     describe('mensajes', () => {
       it('muestra "Sin mensajes" cuando está vacío', () => {
         render(<MiniChat />);
         fireEvent.keyDown(window, { key: ' ', code: 'Space', ctrlKey: true });
         expect(screen.getByText('Sin mensajes aún')).toBeInTheDocument();
       });

       it('muestra solo los últimos N mensajes', () => {
         act(() => {
           for (let i = 0; i < 5; i++) {
             useChatStore.getState().addMessage({
               id: `msg-${i}`,
               role: 'user',
               content: `Mensaje ${i}`,
               timestamp: i,
             });
           }
         });
         render(<MiniChat />);
         fireEvent.keyDown(window, { key: ' ', code: 'Space', ctrlKey: true });
         const msgs = screen.getAllByTestId(/^minichat-msg-/);
         expect(msgs.length).toBe(MAX_VISIBLE_MESSAGES);
       });
     });

     describe('expand', () => {
       it('botón expandir abre ChatPanel y cierra MiniChat', () => {
         render(<MiniChat />);
         fireEvent.keyDown(window, { key: ' ', code: 'Space', ctrlKey: true });
         fireEvent.click(screen.getByTestId('minichat-expand'));
         expect(useChatStore.getState().isPanelOpen).toBe(true);
         expect(screen.queryByTestId('minichat')).not.toBeInTheDocument();
       });
     });

     describe('input', () => {
       it('tiene campo de input', () => {
         render(<MiniChat />);
         fireEvent.keyDown(window, { key: ' ', code: 'Space', ctrlKey: true });
         expect(screen.getByTestId('minichat-input')).toBeInTheDocument();
       });

       it('enviar agrega mensaje al store', () => {
         render(<MiniChat />);
         fireEvent.keyDown(window, { key: ' ', code: 'Space', ctrlKey: true });
         const input = screen.getByTestId('minichat-input');
         fireEvent.change(input, { target: { value: 'Hola' } });
         fireEvent.click(screen.getByTestId('minichat-send'));
         expect(useChatStore.getState().messages).toHaveLength(1);
         expect(useChatStore.getState().messages[0].content).toBe('Hola');
       });

       it('input deshabilitado durante streaming', () => {
         act(() => {
           useChatStore.setState({ isStreaming: true });
         });
         render(<MiniChat />);
         fireEvent.keyDown(window, { key: ' ', code: 'Space', ctrlKey: true });
         expect(screen.getByTestId('minichat-input')).toBeDisabled();
       });
     });

     describe('dimensiones', () => {
       it('tiene dimensiones por defecto correctas', () => {
         render(<MiniChat />);
         fireEvent.keyDown(window, { key: ' ', code: 'Space', ctrlKey: true });
         const minichat = screen.getByTestId('minichat');
         expect(minichat.style.width).toBe(`${DEFAULT_WIDTH}px`);
         expect(minichat.style.height).toBe(`${DEFAULT_HEIGHT}px`);
       });

       it('tiene handle de resize', () => {
         render(<MiniChat />);
         fireEvent.keyDown(window, { key: ' ', code: 'Space', ctrlKey: true });
         expect(screen.getByTestId('minichat-resize')).toBeInTheDocument();
       });
     });

     describe('drag', () => {
       it('tiene header con cursor move para drag', () => {
         render(<MiniChat />);
         fireEvent.keyDown(window, { key: ' ', code: 'Space', ctrlKey: true });
         const header = screen.getByTestId('minichat-header');
         expect(header.className).toContain('cursor-move');
       });
     });
   });

3. Ejecutar tests:
   cd ~/yeyo-os/frontend
   npx jest __tests__/components/chat/MiniChat.test.tsx --no-cache

VERIFICAR:
- [ ] Archivo src/components/chat/MiniChat.tsx existe
- [ ] MiniChat no visible por defecto
- [ ] Ctrl+Space toggle funciona
- [ ] Muestra últimos 3 mensajes
- [ ] Botón expandir abre ChatPanel y cierra MiniChat
- [ ] Draggable por header
- [ ] Resizable por handle
- [ ] Input funciona y envía al store
- [ ] TODOS los tests pasan

SI FALLA:
- keyDown event: usar { key: ' ', code: 'Space', ctrlKey: true }
- State management: verificar que act() envuelve cambios de estado
- DOM queries: verificar data-testid correctos

NO HACER:
- No conectar al backend (solo al store)
- No agregar historial persistente
- No complicar el resize con aspect ratio

GATE: MiniChat flota, Ctrl+Space toggle, muestra últimos 3 mensajes, expande a ChatPanel, drag/resize funciona, todos los tests pasan.
```
