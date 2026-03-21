## ═══════════════════════════════════════
## MICRO-FASE 3.5 — Chat Panel Tests
## Tipo: VSCODE | Prompts: 2 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 3.5-2 [VSCODE] — Tests del ChatPanel y ChatStore

```
Estamos construyendo YeyoOS, un OS AI-nativo con interfaz Neural Hub. Esta es la parte 2 de micro-fase 3.5 de Capa 3 (Cuerpo): tests para el ChatPanel y ChatStore.

CONTEXTO:
- Prompt 3.5-1 completado: ChatPanel.tsx y chat-store.ts creados
- ChatPanel: panel slide-in 400px, streaming batch flush 50ms, markdown
- ChatStore: Zustand store con mensajes, streaming state, panel open/close
- Testing: Jest + React Testing Library

Abre el directorio ~/yeyo-os/frontend en VS Code.

CREAR:

1. Crear archivo __tests__/lib/store/chat-store.test.ts:

   Ruta: ~/yeyo-os/frontend/__tests__/lib/store/chat-store.test.ts
   Contenido:

   /**
    * Tests para ChatStore — Micro-fase 3.5
    */

   import { useChatStore } from '@/lib/store/chat-store';
   import type { ChatMessage } from '@/lib/store/chat-store';
   import { act } from '@testing-library/react';

   describe('ChatStore', () => {
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

     describe('addMessage', () => {
       it('agrega un mensaje al array', () => {
         const msg: ChatMessage = {
           id: 'msg-1',
           role: 'user',
           content: 'Hola YeyoOS',
           timestamp: Date.now(),
         };
         act(() => {
           useChatStore.getState().addMessage(msg);
         });
         expect(useChatStore.getState().messages).toHaveLength(1);
         expect(useChatStore.getState().messages[0].content).toBe('Hola YeyoOS');
       });

       it('mantiene el orden de los mensajes', () => {
         act(() => {
           useChatStore.getState().addMessage({
             id: 'msg-1',
             role: 'user',
             content: 'Primero',
             timestamp: 1,
           });
           useChatStore.getState().addMessage({
             id: 'msg-2',
             role: 'assistant',
             content: 'Segundo',
             timestamp: 2,
           });
         });
         const messages = useChatStore.getState().messages;
         expect(messages[0].content).toBe('Primero');
         expect(messages[1].content).toBe('Segundo');
       });
     });

     describe('updateStreamingMessage', () => {
       it('actualiza el contenido de un mensaje existente', () => {
         act(() => {
           useChatStore.getState().addMessage({
             id: 'stream-1',
             role: 'assistant',
             content: 'Hola',
             timestamp: Date.now(),
             isStreaming: true,
           });
           useChatStore.getState().updateStreamingMessage('stream-1', 'Hola mundo');
         });
         expect(useChatStore.getState().messages[0].content).toBe('Hola mundo');
       });

       it('no modifica otros mensajes', () => {
         act(() => {
           useChatStore.getState().addMessage({
             id: 'msg-1',
             role: 'user',
             content: 'Original',
             timestamp: 1,
           });
           useChatStore.getState().addMessage({
             id: 'stream-1',
             role: 'assistant',
             content: '',
             timestamp: 2,
             isStreaming: true,
           });
           useChatStore.getState().updateStreamingMessage('stream-1', 'Updated');
         });
         expect(useChatStore.getState().messages[0].content).toBe('Original');
         expect(useChatStore.getState().messages[1].content).toBe('Updated');
       });
     });

     describe('finalizeStreamingMessage', () => {
       it('marca el mensaje como no streaming', () => {
         act(() => {
           useChatStore.getState().addMessage({
             id: 'stream-1',
             role: 'assistant',
             content: 'Respuesta completa',
             timestamp: Date.now(),
             isStreaming: true,
           });
           useChatStore.getState().finalizeStreamingMessage('stream-1');
         });
         expect(useChatStore.getState().messages[0].isStreaming).toBe(false);
         expect(useChatStore.getState().isStreaming).toBe(false);
       });
     });

     describe('panel state', () => {
       it('setPanelOpen abre el panel', () => {
         act(() => {
           useChatStore.getState().setPanelOpen(true);
         });
         expect(useChatStore.getState().isPanelOpen).toBe(true);
       });

       it('togglePanel alterna el estado', () => {
         act(() => {
           useChatStore.getState().togglePanel();
         });
         expect(useChatStore.getState().isPanelOpen).toBe(true);
         act(() => {
           useChatStore.getState().togglePanel();
         });
         expect(useChatStore.getState().isPanelOpen).toBe(false);
       });
     });

     describe('error handling', () => {
       it('setError guarda el error', () => {
         act(() => {
           useChatStore.getState().setError('Connection failed');
         });
         expect(useChatStore.getState().error).toBe('Connection failed');
       });

       it('setError con null limpia el error', () => {
         act(() => {
           useChatStore.getState().setError('Error');
           useChatStore.getState().setError(null);
         });
         expect(useChatStore.getState().error).toBeNull();
       });
     });

     describe('clearMessages', () => {
       it('vacía el array de mensajes', () => {
         act(() => {
           useChatStore.getState().addMessage({
             id: 'msg-1',
             role: 'user',
             content: 'test',
             timestamp: Date.now(),
           });
           useChatStore.getState().clearMessages();
         });
         expect(useChatStore.getState().messages).toHaveLength(0);
       });
     });
   });

2. Crear archivo __tests__/components/chat/ChatPanel.test.tsx:

   Ruta: ~/yeyo-os/frontend/__tests__/components/chat/ChatPanel.test.tsx
   Contenido:

   /**
    * Tests para ChatPanel — Micro-fase 3.5
    */

   import { render, screen, fireEvent, act } from '@testing-library/react';
   import ChatPanel, { PANEL_WIDTH, BATCH_FLUSH_MS } from '@/components/chat/ChatPanel';
   import { useChatStore } from '@/lib/store/chat-store';

   // Mock react-markdown
   jest.mock('react-markdown', () => {
     return function MockReactMarkdown({ children }: { children: string }) {
       return <div data-testid="markdown-content">{children}</div>;
     };
   });

   jest.mock('remark-gfm', () => () => {});

   describe('ChatPanel', () => {
     beforeEach(() => {
       act(() => {
         useChatStore.setState({
           messages: [],
           isStreaming: false,
           isPanelOpen: true,
           error: null,
         });
       });
     });

     describe('rendering', () => {
       it('renderiza cuando isPanelOpen es true', () => {
         render(<ChatPanel />);
         expect(screen.getByTestId('chat-panel')).toBeInTheDocument();
       });

       it('no renderiza cuando isPanelOpen es false', () => {
         act(() => {
           useChatStore.setState({ isPanelOpen: false });
         });
         render(<ChatPanel />);
         expect(screen.queryByTestId('chat-panel')).not.toBeInTheDocument();
       });

       it('tiene el ancho correcto', () => {
         render(<ChatPanel />);
         const panel = screen.getByTestId('chat-panel');
         expect(panel.style.width).toBe(`${PANEL_WIDTH}px`);
       });

       it('muestra el título del chat', () => {
         render(<ChatPanel />);
         expect(screen.getByText(/Chat — YeyoOS/)).toBeInTheDocument();
       });

       it('muestra el campo de input', () => {
         render(<ChatPanel />);
         expect(screen.getByTestId('chat-input')).toBeInTheDocument();
       });

       it('muestra el botón de enviar', () => {
         render(<ChatPanel />);
         expect(screen.getByTestId('send-button')).toBeInTheDocument();
       });
     });

     describe('mensajes', () => {
       it('muestra mensajes del store', () => {
         act(() => {
           useChatStore.getState().addMessage({
             id: 'msg-1',
             role: 'user',
             content: 'Hola YeyoOS',
             timestamp: Date.now(),
           });
         });
         render(<ChatPanel />);
         expect(screen.getByText('Hola YeyoOS')).toBeInTheDocument();
       });

       it('muestra indicador de streaming', () => {
         act(() => {
           useChatStore.getState().addMessage({
             id: 'stream-1',
             role: 'assistant',
             content: 'Generando...',
             timestamp: Date.now(),
             isStreaming: true,
           });
         });
         render(<ChatPanel />);
         expect(screen.getByTestId('streaming-indicator')).toBeInTheDocument();
       });

       it('renderiza markdown en mensajes del asistente', () => {
         act(() => {
           useChatStore.getState().addMessage({
             id: 'msg-1',
             role: 'assistant',
             content: '**Hola** mundo',
             timestamp: Date.now(),
           });
         });
         render(<ChatPanel />);
         expect(screen.getByTestId('markdown-content')).toBeInTheDocument();
       });
     });

     describe('input', () => {
       it('actualiza el input al escribir', () => {
         render(<ChatPanel />);
         const input = screen.getByTestId('chat-input') as HTMLInputElement;
         fireEvent.change(input, { target: { value: 'test message' } });
         expect(input.value).toBe('test message');
       });

       it('botón enviar está deshabilitado con input vacío', () => {
         render(<ChatPanel />);
         const btn = screen.getByTestId('send-button');
         expect(btn).toBeDisabled();
       });

       it('botón enviar está deshabilitado durante streaming', () => {
         act(() => {
           useChatStore.setState({ isStreaming: true });
         });
         render(<ChatPanel />);
         const input = screen.getByTestId('chat-input') as HTMLInputElement;
         fireEvent.change(input, { target: { value: 'test' } });
         expect(screen.getByTestId('send-button')).toBeDisabled();
       });

       it('input está deshabilitado durante streaming', () => {
         act(() => {
           useChatStore.setState({ isStreaming: true });
         });
         render(<ChatPanel />);
         expect(screen.getByTestId('chat-input')).toBeDisabled();
       });
     });

     describe('panel controls', () => {
       it('botón cerrar cierra el panel', () => {
         render(<ChatPanel />);
         fireEvent.click(screen.getByTestId('close-panel'));
         expect(useChatStore.getState().isPanelOpen).toBe(false);
       });
     });

     describe('error display', () => {
       it('muestra error cuando existe', () => {
         act(() => {
           useChatStore.setState({ error: 'Connection failed' });
         });
         render(<ChatPanel />);
         expect(screen.getByTestId('chat-error')).toBeInTheDocument();
         expect(screen.getByText('Connection failed')).toBeInTheDocument();
       });

       it('no muestra error cuando es null', () => {
         render(<ChatPanel />);
         expect(screen.queryByTestId('chat-error')).not.toBeInTheDocument();
       });
     });

     describe('constantes', () => {
       it('PANEL_WIDTH es 400', () => {
         expect(PANEL_WIDTH).toBe(400);
       });

       it('BATCH_FLUSH_MS es 50', () => {
         expect(BATCH_FLUSH_MS).toBe(50);
       });
     });
   });

3. Ejecutar tests:
   cd ~/yeyo-os/frontend
   npx jest __tests__/lib/store/chat-store.test.ts __tests__/components/chat/ChatPanel.test.tsx --no-cache

VERIFICAR:
- [ ] Tests del ChatStore: addMessage, updateStreaming, finalizeStreaming, togglePanel, setError, clearMessages
- [ ] Tests del ChatPanel: renderiza/oculta, muestra mensajes, streaming indicator, markdown, input, botones
- [ ] Panel se cierra con botón ✕
- [ ] Botón enviar deshabilitado con input vacío o durante streaming
- [ ] Input deshabilitado durante streaming
- [ ] Error se muestra cuando existe
- [ ] TODOS los tests pasan

SI FALLA:
- Mock de react-markdown: verificar que el mock retorna un componente funcional
- Zustand state: usar act() al llamar setState
- DOM queries: verificar data-testid correctos

NO HACER:
- No testear la conexión real a /api/v1/chat/stream (eso es integration test)
- No testear el batch flush timing (difícil de testear unitariamente)
- No testear auto-scroll (requiere DOM real)

GATE: ChatStore tiene CRUD completo de mensajes, ChatPanel renderiza correctamente, todos los tests pasan.
```
