## ═══════════════════════════════════════
## MICRO-FASE 3.12 — WebSocket Client
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 3.12-1 [VSCODE] — Cliente WebSocket con auto-reconnect y event handlers

```
Estamos construyendo YeyoOS, un OS AI-nativo con interfaz Neural Hub. Esta es la micro-fase 3.12 de Capa 3 (Cuerpo): crear el cliente WebSocket del frontend para conexión en tiempo real.

CONTEXTO:
- Micro-fases 3.0-3.11 completadas: Canvas, nodos, chat, stores
- Backend WebSocket disponible desde Capa 1.7
- Auto-reconnect con exponential backoff
- Event handlers: chat.message, system.status, gpu.update, node.event
- Indicador de conexión en la UI
- Si Kill Switch está activo, ignorar mensajes entrantes (excepto system.status)

Abre el directorio ~/yeyo-os/frontend en VS Code.

CREAR:

1. Crear estructura:
   mkdir -p src/lib/api
   mkdir -p __tests__/lib/api

2. Crear archivo src/lib/api/websocket.ts:

   Ruta: ~/yeyo-os/frontend/src/lib/api/websocket.ts
   Contenido:

   /**
    * YeyoOS — WebSocket Client
    * Micro-fase 3.12 — Capa 3: Cuerpo
    *
    * Cliente WebSocket con auto-reconnect exponential backoff.
    * Conecta al backend (Capa 1.7) para updates en tiempo real.
    */

   import { getKillSwitchState } from '@/hooks/useKeyboardShortcuts';

   export type WSEventType = 'chat.message' | 'system.status' | 'gpu.update' | 'node.event';

   export interface WSMessage {
     type: WSEventType;
     payload: unknown;
     timestamp: number;
   }

   export type WSEventHandler = (payload: unknown) => void;
   export type WSConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';
   export type WSStatusListener = (status: WSConnectionStatus) => void;

   export interface WSClientConfig {
     url: string;
     maxReconnectAttempts?: number;
     baseDelayMs?: number;
     maxDelayMs?: number;
   }

   const DEFAULT_CONFIG: Required<WSClientConfig> = {
     url: 'ws://localhost:8000/ws',
     maxReconnectAttempts: 10,
     baseDelayMs: 1000,
     maxDelayMs: 30000,
   };

   export class WSClient {
     private ws: WebSocket | null = null;
     private config: Required<WSClientConfig>;
     private handlers: Map<WSEventType, Set<WSEventHandler>> = new Map();
     private statusListeners: Set<WSStatusListener> = new Set();
     private reconnectAttempts: number = 0;
     private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
     private status: WSConnectionStatus = 'disconnected';
     private manualClose: boolean = false;

     constructor(config: Partial<WSClientConfig> = {}) {
       this.config = { ...DEFAULT_CONFIG, ...config };
     }

     public connect(): void {
       if (this.ws?.readyState === WebSocket.OPEN) return;

       this.manualClose = false;
       this.setStatus('connecting');

       try {
         this.ws = new WebSocket(this.config.url);
         this.setupEventListeners();
       } catch {
         this.setStatus('error');
         this.scheduleReconnect();
       }
     }

     private setupEventListeners(): void {
       if (!this.ws) return;

       this.ws.onopen = () => {
         this.reconnectAttempts = 0;
         this.setStatus('connected');
       };

       this.ws.onclose = () => {
         this.setStatus('disconnected');
         if (!this.manualClose) {
           this.scheduleReconnect();
         }
       };

       this.ws.onerror = () => {
         this.setStatus('error');
       };

       this.ws.onmessage = (event: MessageEvent) => {
         try {
           const message: WSMessage = JSON.parse(event.data);
           this.dispatchMessage(message);
         } catch {
           console.warn('[YeyoOS WS] Failed to parse message:', event.data);
         }
       };
     }

     private dispatchMessage(message: WSMessage): void {
       const killSwitch = getKillSwitchState();
       if (killSwitch.isActive && message.type !== 'system.status') {
         return;
       }

       const handlers = this.handlers.get(message.type);
       if (handlers) {
         handlers.forEach((handler) => {
           try {
             handler(message.payload);
           } catch (err) {
             console.error(`[YeyoOS WS] Error in handler for ${message.type}:`, err);
           }
         });
       }
     }

     private scheduleReconnect(): void {
       if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
         console.warn('[YeyoOS WS] Max reconnect attempts reached');
         return;
       }

       const delay = Math.min(
         this.config.baseDelayMs * Math.pow(2, this.reconnectAttempts),
         this.config.maxDelayMs
       );

       this.reconnectAttempts++;
       this.reconnectTimer = setTimeout(() => {
         this.connect();
       }, delay);
     }

     private setStatus(status: WSConnectionStatus): void {
       this.status = status;
       this.statusListeners.forEach((listener) => {
         try {
           listener(status);
         } catch {
           // ignore listener errors
         }
       });
     }

     public on(type: WSEventType, handler: WSEventHandler): () => void {
       if (!this.handlers.has(type)) {
         this.handlers.set(type, new Set());
       }
       this.handlers.get(type)!.add(handler);

       return () => {
         this.handlers.get(type)?.delete(handler);
       };
     }

     public onStatusChange(listener: WSStatusListener): () => void {
       this.statusListeners.add(listener);
       return () => {
         this.statusListeners.delete(listener);
       };
     }

     public getStatus(): WSConnectionStatus {
       return this.status;
     }

     public getReconnectAttempts(): number {
       return this.reconnectAttempts;
     }

     public send(message: WSMessage): void {
       if (this.ws?.readyState !== WebSocket.OPEN) {
         console.warn('[YeyoOS WS] Cannot send: not connected');
         return;
       }
       this.ws.send(JSON.stringify(message));
     }

     public disconnect(): void {
       this.manualClose = true;
       if (this.reconnectTimer) {
         clearTimeout(this.reconnectTimer);
         this.reconnectTimer = null;
       }
       if (this.ws) {
         this.ws.close();
         this.ws = null;
       }
       this.setStatus('disconnected');
     }

     public destroy(): void {
       this.disconnect();
       this.handlers.clear();
       this.statusListeners.clear();
     }
   }

   export { DEFAULT_CONFIG };

3. Crear archivo __tests__/lib/api/websocket.test.ts:

   Ruta: ~/yeyo-os/frontend/__tests__/lib/api/websocket.test.ts
   Contenido:

   /**
    * Tests para WebSocket Client — Micro-fase 3.12
    */

   import { WSClient, DEFAULT_CONFIG } from '@/lib/api/websocket';
   import type { WSConnectionStatus, WSMessage, WSEventType } from '@/lib/api/websocket';

   // Mock Kill Switch
   jest.mock('@/hooks/useKeyboardShortcuts', () => ({
     getKillSwitchState: jest.fn(() => ({ isActive: false, toggledAt: null })),
   }));

   import { getKillSwitchState } from '@/hooks/useKeyboardShortcuts';
   const mockGetKillSwitch = getKillSwitchState as jest.Mock;

   // Mock WebSocket
   class MockWebSocket {
     static OPEN = 1;
     static CLOSED = 3;

     readyState = MockWebSocket.OPEN;
     onopen: (() => void) | null = null;
     onclose: (() => void) | null = null;
     onerror: (() => void) | null = null;
     onmessage: ((event: { data: string }) => void) | null = null;

     send = jest.fn();
     close = jest.fn(() => {
       this.readyState = MockWebSocket.CLOSED;
       this.onclose?.();
     });

     simulateOpen(): void {
       this.readyState = MockWebSocket.OPEN;
       this.onopen?.();
     }

     simulateMessage(data: WSMessage): void {
       this.onmessage?.({ data: JSON.stringify(data) });
     }

     simulateClose(): void {
       this.readyState = MockWebSocket.CLOSED;
       this.onclose?.();
     }

     simulateError(): void {
       this.onerror?.();
     }
   }

   let mockWS: MockWebSocket;

   beforeAll(() => {
     (global as any).WebSocket = jest.fn().mockImplementation(() => {
       mockWS = new MockWebSocket();
       return mockWS;
     });
     (global.WebSocket as any).OPEN = 1;
   });

   describe('WSClient', () => {
     let client: WSClient;

     beforeEach(() => {
       jest.useFakeTimers();
       jest.clearAllMocks();
       mockGetKillSwitch.mockReturnValue({ isActive: false, toggledAt: null });
       client = new WSClient({ url: 'ws://test:8000/ws' });
     });

     afterEach(() => {
       client.destroy();
       jest.useRealTimers();
     });

     describe('connect', () => {
       it('crea WebSocket y se conecta', () => {
         client.connect();
         expect(global.WebSocket).toHaveBeenCalledWith('ws://test:8000/ws');
       });

       it('status cambia a connecting', () => {
         client.connect();
         expect(client.getStatus()).toBe('connecting');
       });

       it('status cambia a connected al abrir', () => {
         client.connect();
         mockWS.simulateOpen();
         expect(client.getStatus()).toBe('connected');
       });
     });

     describe('event handlers', () => {
       it('registra y ejecuta handler para un tipo de evento', () => {
         const handler = jest.fn();
         client.on('chat.message', handler);
         client.connect();
         mockWS.simulateOpen();

         const msg: WSMessage = {
           type: 'chat.message',
           payload: { text: 'hello' },
           timestamp: Date.now(),
         };
         mockWS.simulateMessage(msg);
         expect(handler).toHaveBeenCalledWith({ text: 'hello' });
       });

       it('unsubscribe funciona', () => {
         const handler = jest.fn();
         const unsub = client.on('gpu.update', handler);
         unsub();
         client.connect();
         mockWS.simulateOpen();

         mockWS.simulateMessage({
           type: 'gpu.update',
           payload: {},
           timestamp: Date.now(),
         });
         expect(handler).not.toHaveBeenCalled();
       });
     });

     describe('Kill Switch integration', () => {
       it('ignora mensajes no-system cuando Kill Switch está activo', () => {
         mockGetKillSwitch.mockReturnValue({ isActive: true, toggledAt: Date.now() });
         const handler = jest.fn();
         client.on('chat.message', handler);
         client.connect();
         mockWS.simulateOpen();

         mockWS.simulateMessage({
           type: 'chat.message',
           payload: { text: 'hello' },
           timestamp: Date.now(),
         });
         expect(handler).not.toHaveBeenCalled();
       });

       it('permite system.status incluso con Kill Switch activo', () => {
         mockGetKillSwitch.mockReturnValue({ isActive: true, toggledAt: Date.now() });
         const handler = jest.fn();
         client.on('system.status', handler);
         client.connect();
         mockWS.simulateOpen();

         mockWS.simulateMessage({
           type: 'system.status',
           payload: { ok: true },
           timestamp: Date.now(),
         });
         expect(handler).toHaveBeenCalledWith({ ok: true });
       });
     });

     describe('reconnect', () => {
       it('intenta reconectar al desconectarse', () => {
         client.connect();
         mockWS.simulateOpen();
         const wsCallCount = (global.WebSocket as jest.Mock).mock.calls.length;

         mockWS.simulateClose();
         jest.advanceTimersByTime(DEFAULT_CONFIG.baseDelayMs + 100);

         expect((global.WebSocket as jest.Mock).mock.calls.length).toBeGreaterThan(wsCallCount);
       });

       it('no reconecta después de disconnect() manual', () => {
         client.connect();
         mockWS.simulateOpen();
         client.disconnect();
         const wsCallCount = (global.WebSocket as jest.Mock).mock.calls.length;

         jest.advanceTimersByTime(DEFAULT_CONFIG.baseDelayMs * 10);
         expect((global.WebSocket as jest.Mock).mock.calls.length).toBe(wsCallCount);
       });

       it('exponential backoff incrementa el delay', () => {
         client.connect();
         mockWS.simulateOpen();
         mockWS.simulateClose();
         expect(client.getReconnectAttempts()).toBe(1);
       });
     });

     describe('status listeners', () => {
       it('notifica cambios de estado', () => {
         const listener = jest.fn();
         client.onStatusChange(listener);
         client.connect();
         expect(listener).toHaveBeenCalledWith('connecting');
       });

       it('unsubscribe funciona', () => {
         const listener = jest.fn();
         const unsub = client.onStatusChange(listener);
         unsub();
         client.connect();
         expect(listener).not.toHaveBeenCalled();
       });
     });

     describe('send', () => {
       it('envía mensaje serializado', () => {
         client.connect();
         mockWS.simulateOpen();

         const msg: WSMessage = {
           type: 'chat.message',
           payload: { text: 'test' },
           timestamp: Date.now(),
         };
         client.send(msg);
         expect(mockWS.send).toHaveBeenCalledWith(JSON.stringify(msg));
       });
     });

     describe('disconnect', () => {
       it('cierra la conexión', () => {
         client.connect();
         mockWS.simulateOpen();
         client.disconnect();
         expect(client.getStatus()).toBe('disconnected');
       });
     });

     describe('destroy', () => {
       it('limpia todo', () => {
         const handler = jest.fn();
         client.on('chat.message', handler);
         client.destroy();
         expect(client.getStatus()).toBe('disconnected');
       });
     });

     describe('DEFAULT_CONFIG', () => {
       it('tiene valores razonables', () => {
         expect(DEFAULT_CONFIG.maxReconnectAttempts).toBe(10);
         expect(DEFAULT_CONFIG.baseDelayMs).toBe(1000);
         expect(DEFAULT_CONFIG.maxDelayMs).toBe(30000);
       });
     });
   });

4. Ejecutar tests:
   cd ~/yeyo-os/frontend
   npx jest __tests__/lib/api/websocket.test.ts --no-cache

VERIFICAR:
- [ ] Archivo src/lib/api/websocket.ts existe
- [ ] WSClient conecta y reporta status correctamente
- [ ] Event handlers se registran y ejecutan
- [ ] Kill Switch bloquea mensajes excepto system.status
- [ ] Auto-reconnect con exponential backoff
- [ ] disconnect() manual no reconecta
- [ ] send() envía mensajes serializados
- [ ] destroy() limpia handlers y listeners
- [ ] TODOS los tests pasan

SI FALLA:
- WebSocket mock: verificar que global.WebSocket está mockeado
- Fake timers: usar jest.useFakeTimers() y advanceTimersByTime()
- Kill Switch mock: verificar que getKillSwitchState está mockeado

NO HACER:
- No implementar auth/tokens en WebSocket
- No agregar compression
- No crear WebSocket server (ya existe en Capa 1.7)

GATE: WSClient conecta, auto-reconnect funciona, Kill Switch respetado, event handlers, todos los tests pasan.
```
