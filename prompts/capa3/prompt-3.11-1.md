## ═══════════════════════════════════════
## MICRO-FASE 3.11 — Zustand State Architecture
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 3.11-1 [VSCODE] — Arquitectura completa de estado con Zustand

```
Estamos construyendo YeyoOS, un OS AI-nativo con interfaz Neural Hub. Esta es la micro-fase 3.11 de Capa 3 (Cuerpo): crear la arquitectura completa de estado con Zustand.

CONTEXTO:
- Micro-fases 3.0-3.10 completadas: Canvas, nodos, chat, theme, notifications, shortcuts
- Ya existen: hub-store.ts (3.0), chat-store.ts (3.5), notification-store.ts (3.9)
- Faltan: ui-store.ts y system-store.ts
- Middleware: persistencia en localStorage, devtools
- 4 stores independientes: hub, chat, ui, system

Abre el directorio ~/yeyo-os/frontend en VS Code.

CREAR:

1. Crear archivo src/lib/store/ui-store.ts:

   Ruta: ~/yeyo-os/frontend/src/lib/store/ui-store.ts
   Contenido:

   /**
    * YeyoOS — UI Store (Estado de la Interfaz)
    * Micro-fase 3.11 — Capa 3: Cuerpo
    */

   import { create } from 'zustand';
   import { persist, devtools } from 'zustand/middleware';

   export type ActivePanel = 'chat' | 'settings' | 'files' | null;
   export type ThemeMode = 'dark';

   export interface UIState {
     activePanel: ActivePanel;
     theme: ThemeMode;
     sidebarCollapsed: boolean;
     miniChatVisible: boolean;
     commandPaletteOpen: boolean;

     setActivePanel: (panel: ActivePanel) => void;
     closeActivePanel: () => void;
     toggleSidebar: () => void;
     setMiniChatVisible: (visible: boolean) => void;
     toggleMiniChat: () => void;
     setCommandPaletteOpen: (open: boolean) => void;
   }

   export const useUIStore = create<UIState>()(
     devtools(
       persist(
         (set) => ({
           activePanel: null,
           theme: 'dark',
           sidebarCollapsed: false,
           miniChatVisible: false,
           commandPaletteOpen: false,

           setActivePanel: (panel) => set({ activePanel: panel }),
           closeActivePanel: () => set({ activePanel: null }),
           toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
           setMiniChatVisible: (visible) => set({ miniChatVisible: visible }),
           toggleMiniChat: () => set((s) => ({ miniChatVisible: !s.miniChatVisible })),
           setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),
         }),
         {
           name: 'yeyo-ui-store',
           partialize: (state) => ({
             theme: state.theme,
             sidebarCollapsed: state.sidebarCollapsed,
           }),
         }
       ),
       { name: 'YeyoOS UI Store' }
     )
   );

2. Crear archivo src/lib/store/system-store.ts:

   Ruta: ~/yeyo-os/frontend/src/lib/store/system-store.ts
   Contenido:

   /**
    * YeyoOS — System Store (Estado del Sistema)
    * Micro-fase 3.11 — Capa 3: Cuerpo
    */

   import { create } from 'zustand';
   import { devtools } from 'zustand/middleware';

   export type ConnectionStatus = 'connected' | 'connecting' | 'disconnected' | 'error';

   export interface GPUStatus {
     available: boolean;
     vramUsedMB: number;
     vramTotalMB: number;
     temperature: number | null;
   }

   export interface ServiceHealth {
     ollama: boolean;
     postgres: boolean;
     redis: boolean;
     api: boolean;
   }

   export interface SystemState {
     connectionStatus: ConnectionStatus;
     gpuStatus: GPUStatus;
     serviceHealth: ServiceHealth;
     killSwitchActive: boolean;
     lastHealthCheck: number | null;

     setConnectionStatus: (status: ConnectionStatus) => void;
     updateGPUStatus: (status: Partial<GPUStatus>) => void;
     updateServiceHealth: (health: Partial<ServiceHealth>) => void;
     setKillSwitchActive: (active: boolean) => void;
     setLastHealthCheck: (timestamp: number) => void;
   }

   const DEFAULT_GPU: GPUStatus = {
     available: false,
     vramUsedMB: 0,
     vramTotalMB: 3072,
     temperature: null,
   };

   const DEFAULT_HEALTH: ServiceHealth = {
     ollama: false,
     postgres: false,
     redis: false,
     api: false,
   };

   export const useSystemStore = create<SystemState>()(
     devtools(
       (set) => ({
         connectionStatus: 'disconnected',
         gpuStatus: { ...DEFAULT_GPU },
         serviceHealth: { ...DEFAULT_HEALTH },
         killSwitchActive: false,
         lastHealthCheck: null,

         setConnectionStatus: (status) => set({ connectionStatus: status }),

         updateGPUStatus: (status) =>
           set((s) => ({
             gpuStatus: { ...s.gpuStatus, ...status },
           })),

         updateServiceHealth: (health) =>
           set((s) => ({
             serviceHealth: { ...s.serviceHealth, ...health },
           })),

         setKillSwitchActive: (active) => set({ killSwitchActive: active }),
         setLastHealthCheck: (timestamp) => set({ lastHealthCheck: timestamp }),
       }),
       { name: 'YeyoOS System Store' }
     )
   );

   export { DEFAULT_GPU, DEFAULT_HEALTH };

3. Crear archivo src/lib/store/index.ts:

   Ruta: ~/yeyo-os/frontend/src/lib/store/index.ts
   Contenido:

   /**
    * YeyoOS — Store Index
    * Micro-fase 3.11 — Capa 3: Cuerpo
    *
    * Re-exporta todos los stores para import centralizado.
    */

   export { useHubStore } from './hub-store';
   export type { HubState, CanvasSize, NodePosition } from './hub-store';

   export { useChatStore } from './chat-store';
   export type { ChatState, ChatMessage } from './chat-store';

   export { useUIStore } from './ui-store';
   export type { UIState, ActivePanel, ThemeMode } from './ui-store';

   export { useSystemStore } from './system-store';
   export type {
     SystemState,
     ConnectionStatus,
     GPUStatus,
     ServiceHealth,
   } from './system-store';

   export { useNotificationStore } from './notification-store';
   export type {
     NotificationState,
     NotificationType,
     Notification,
   } from './notification-store';

4. Crear archivo __tests__/lib/store/stores.test.ts:

   Ruta: ~/yeyo-os/frontend/__tests__/lib/store/stores.test.ts
   Contenido:

   /**
    * Tests para Zustand State Architecture — Micro-fase 3.11
    */

   import { act } from '@testing-library/react';
   import { useUIStore } from '@/lib/store/ui-store';
   import { useSystemStore, DEFAULT_GPU, DEFAULT_HEALTH } from '@/lib/store/system-store';

   describe('Zustand State Architecture', () => {
     describe('UIStore', () => {
       beforeEach(() => {
         act(() => {
           useUIStore.setState({
             activePanel: null,
             theme: 'dark',
             sidebarCollapsed: false,
             miniChatVisible: false,
             commandPaletteOpen: false,
           });
         });
       });

       it('estado inicial correcto', () => {
         const state = useUIStore.getState();
         expect(state.activePanel).toBeNull();
         expect(state.theme).toBe('dark');
         expect(state.sidebarCollapsed).toBe(false);
         expect(state.miniChatVisible).toBe(false);
       });

       it('setActivePanel cambia el panel activo', () => {
         act(() => {
           useUIStore.getState().setActivePanel('chat');
         });
         expect(useUIStore.getState().activePanel).toBe('chat');
       });

       it('closeActivePanel pone null', () => {
         act(() => {
           useUIStore.getState().setActivePanel('settings');
           useUIStore.getState().closeActivePanel();
         });
         expect(useUIStore.getState().activePanel).toBeNull();
       });

       it('toggleSidebar alterna collapsed', () => {
         act(() => {
           useUIStore.getState().toggleSidebar();
         });
         expect(useUIStore.getState().sidebarCollapsed).toBe(true);
         act(() => {
           useUIStore.getState().toggleSidebar();
         });
         expect(useUIStore.getState().sidebarCollapsed).toBe(false);
       });

       it('toggleMiniChat alterna visibilidad', () => {
         act(() => {
           useUIStore.getState().toggleMiniChat();
         });
         expect(useUIStore.getState().miniChatVisible).toBe(true);
       });

       it('setCommandPaletteOpen funciona', () => {
         act(() => {
           useUIStore.getState().setCommandPaletteOpen(true);
         });
         expect(useUIStore.getState().commandPaletteOpen).toBe(true);
       });
     });

     describe('SystemStore', () => {
       beforeEach(() => {
         act(() => {
           useSystemStore.setState({
             connectionStatus: 'disconnected',
             gpuStatus: { ...DEFAULT_GPU },
             serviceHealth: { ...DEFAULT_HEALTH },
             killSwitchActive: false,
             lastHealthCheck: null,
           });
         });
       });

       it('estado inicial con GPU GTX 1060 3GB', () => {
         const { gpuStatus } = useSystemStore.getState();
         expect(gpuStatus.vramTotalMB).toBe(3072);
         expect(gpuStatus.available).toBe(false);
       });

       it('estado inicial con servicios desconectados', () => {
         const { serviceHealth } = useSystemStore.getState();
         expect(serviceHealth.ollama).toBe(false);
         expect(serviceHealth.postgres).toBe(false);
         expect(serviceHealth.redis).toBe(false);
         expect(serviceHealth.api).toBe(false);
       });

       it('setConnectionStatus cambia el estado', () => {
         act(() => {
           useSystemStore.getState().setConnectionStatus('connected');
         });
         expect(useSystemStore.getState().connectionStatus).toBe('connected');
       });

       it('updateGPUStatus actualiza parcialmente', () => {
         act(() => {
           useSystemStore.getState().updateGPUStatus({
             available: true,
             vramUsedMB: 1500,
           });
         });
         const { gpuStatus } = useSystemStore.getState();
         expect(gpuStatus.available).toBe(true);
         expect(gpuStatus.vramUsedMB).toBe(1500);
         expect(gpuStatus.vramTotalMB).toBe(3072);
       });

       it('updateServiceHealth actualiza parcialmente', () => {
         act(() => {
           useSystemStore.getState().updateServiceHealth({
             ollama: true,
             postgres: true,
           });
         });
         const { serviceHealth } = useSystemStore.getState();
         expect(serviceHealth.ollama).toBe(true);
         expect(serviceHealth.postgres).toBe(true);
         expect(serviceHealth.redis).toBe(false);
       });

       it('setKillSwitchActive funciona', () => {
         act(() => {
           useSystemStore.getState().setKillSwitchActive(true);
         });
         expect(useSystemStore.getState().killSwitchActive).toBe(true);
       });

       it('setLastHealthCheck guarda timestamp', () => {
         const now = Date.now();
         act(() => {
           useSystemStore.getState().setLastHealthCheck(now);
         });
         expect(useSystemStore.getState().lastHealthCheck).toBe(now);
       });
     });
   });

5. Ejecutar tests:
   cd ~/yeyo-os/frontend
   npx jest __tests__/lib/store/stores.test.ts --no-cache

VERIFICAR:
- [ ] Archivo src/lib/store/ui-store.ts existe con persist + devtools middleware
- [ ] Archivo src/lib/store/system-store.ts existe con devtools middleware
- [ ] Archivo src/lib/store/index.ts re-exporta todos los stores
- [ ] UIStore: activePanel, theme, sidebar, miniChat, commandPalette
- [ ] SystemStore: connectionStatus, gpuStatus (3072MB), serviceHealth, killSwitchActive
- [ ] ui-store persiste solo theme y sidebarCollapsed en localStorage
- [ ] system-store NO persiste (es runtime state)
- [ ] TODOS los tests pasan

SI FALLA:
- Zustand middleware: verificar orden devtools(persist(...))
- Persist partialize: solo guarda los campos especificados
- Type errors: verificar que los types se exportan correctamente

NO HACER:
- No modificar hub-store.ts ni chat-store.ts ni notification-store.ts existentes
- No agregar middleware de logging (devtools es suficiente)
- No crear un store global monolítico (4 stores independientes)

GATE: 5 stores Zustand independientes (hub, chat, ui, system, notification), persist + devtools configurados, index re-exporta todo, todos los tests pasan.
```
