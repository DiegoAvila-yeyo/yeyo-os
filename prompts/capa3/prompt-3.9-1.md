## ═══════════════════════════════════════
## MICRO-FASE 3.9 — Notification System
## Tipo: VSCODE | Prompts: 1 | Complejidad: Simple
## ═══════════════════════════════════════

### PROMPT 3.9-1 [VSCODE] — Sistema de notificaciones toast

```
Estamos construyendo YeyoOS, un OS AI-nativo con interfaz Neural Hub. Esta es la micro-fase 3.9 de Capa 3 (Cuerpo): crear el sistema de notificaciones toast.

CONTEXTO:
- Micro-fases 3.0-3.8 completadas: Canvas, nodos, chat, theme
- Toasts para eventos del sistema: info, success, warning, error
- Stack bottom-right, máximo 5 visibles
- Auto-dismiss después de 5 segundos
- Cierre manual con botón ✕
- Zustand store para gestión de notificaciones

Abre el directorio ~/yeyo-os/frontend en VS Code.

CREAR:

1. Crear estructura:
   mkdir -p src/components/common
   mkdir -p __tests__/components/common

2. Crear archivo src/lib/store/notification-store.ts:

   Ruta: ~/yeyo-os/frontend/src/lib/store/notification-store.ts
   Contenido:

   /**
    * YeyoOS — Notification Store
    * Micro-fase 3.9 — Capa 3: Cuerpo
    */

   import { create } from 'zustand';

   export type NotificationType = 'info' | 'success' | 'warning' | 'error';

   export interface Notification {
     id: string;
     type: NotificationType;
     message: string;
     createdAt: number;
     autoDismiss: boolean;
   }

   export interface NotificationState {
     notifications: Notification[];
     maxVisible: number;

     addNotification: (type: NotificationType, message: string, autoDismiss?: boolean) => string;
     removeNotification: (id: string) => void;
     clearAll: () => void;
   }

   const MAX_VISIBLE = 5;
   const AUTO_DISMISS_MS = 5000;

   function generateNotificationId(): string {
     return `notif-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
   }

   export const useNotificationStore = create<NotificationState>((set, get) => ({
     notifications: [],
     maxVisible: MAX_VISIBLE,

     addNotification: (type, message, autoDismiss = true) => {
       const id = generateNotificationId();
       const notification: Notification = {
         id,
         type,
         message,
         createdAt: Date.now(),
         autoDismiss,
       };

       set((state) => {
         const updated = [...state.notifications, notification];
         if (updated.length > MAX_VISIBLE) {
           return { notifications: updated.slice(-MAX_VISIBLE) };
         }
         return { notifications: updated };
       });

       if (autoDismiss) {
         setTimeout(() => {
           get().removeNotification(id);
         }, AUTO_DISMISS_MS);
       }

       return id;
     },

     removeNotification: (id) =>
       set((state) => ({
         notifications: state.notifications.filter((n) => n.id !== id),
       })),

     clearAll: () => set({ notifications: [] }),
   }));

   export { MAX_VISIBLE, AUTO_DISMISS_MS };

3. Crear archivo src/components/common/Notifications.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/common/Notifications.tsx
   Contenido:

   /**
    * YeyoOS — Notifications (Toast Stack)
    * Micro-fase 3.9 — Capa 3: Cuerpo
    *
    * Stack de notificaciones toast en la esquina bottom-right.
    */

   'use client';

   import { useNotificationStore, type NotificationType } from '@/lib/store/notification-store';

   const TYPE_STYLES: Record<NotificationType, { bg: string; border: string; icon: string }> = {
     info: {
       bg: 'bg-blue-900/80',
       border: 'border-blue-500',
       icon: 'ℹ️',
     },
     success: {
       bg: 'bg-green-900/80',
       border: 'border-green-500',
       icon: '✅',
     },
     warning: {
       bg: 'bg-yellow-900/80',
       border: 'border-yellow-500',
       icon: '⚠️',
     },
     error: {
       bg: 'bg-red-900/80',
       border: 'border-red-500',
       icon: '❌',
     },
   };

   export default function Notifications() {
     const { notifications, removeNotification } = useNotificationStore();

     if (notifications.length === 0) return null;

     return (
       <div
         data-testid="notification-stack"
         className="fixed bottom-4 right-4 z-[200] flex flex-col gap-2 max-w-sm"
       >
         {notifications.map((notif) => {
           const style = TYPE_STYLES[notif.type];
           return (
             <div
               key={notif.id}
               data-testid={`notification-${notif.id}`}
               data-type={notif.type}
               className={`${style.bg} ${style.border} border rounded-lg px-4 py-3 shadow-lg backdrop-blur-sm animate-fade-in flex items-start gap-2`}
             >
               <span className="text-sm flex-shrink-0">{style.icon}</span>
               <p className="text-sm text-gray-200 flex-1">{notif.message}</p>
               <button
                 data-testid={`close-${notif.id}`}
                 onClick={() => removeNotification(notif.id)}
                 className="text-gray-400 hover:text-white text-xs flex-shrink-0 ml-2"
               >
                 ✕
               </button>
             </div>
           );
         })}
       </div>
     );
   }

   export { TYPE_STYLES };

4. Crear archivo __tests__/components/common/Notifications.test.tsx:

   Ruta: ~/yeyo-os/frontend/__tests__/components/common/Notifications.test.tsx
   Contenido:

   /**
    * Tests para Notifications — Micro-fase 3.9
    */

   import { render, screen, fireEvent, act } from '@testing-library/react';
   import Notifications from '@/components/common/Notifications';
   import {
     useNotificationStore,
     MAX_VISIBLE,
     AUTO_DISMISS_MS,
   } from '@/lib/store/notification-store';

   describe('Notification System', () => {
     beforeEach(() => {
       jest.useFakeTimers();
       act(() => {
         useNotificationStore.setState({ notifications: [] });
       });
     });

     afterEach(() => {
       jest.useRealTimers();
     });

     describe('NotificationStore', () => {
       it('agrega una notificación', () => {
         act(() => {
           useNotificationStore.getState().addNotification('info', 'Test message');
         });
         expect(useNotificationStore.getState().notifications).toHaveLength(1);
       });

       it('retorna el id de la notificación', () => {
         let id: string = '';
         act(() => {
           id = useNotificationStore.getState().addNotification('success', 'Done');
         });
         expect(id).toMatch(/^notif-/);
       });

       it('limita a MAX_VISIBLE notificaciones', () => {
         act(() => {
           for (let i = 0; i < MAX_VISIBLE + 3; i++) {
             useNotificationStore.getState().addNotification('info', `msg ${i}`, false);
           }
         });
         expect(useNotificationStore.getState().notifications.length).toBeLessThanOrEqual(MAX_VISIBLE);
       });

       it('removeNotification elimina por id', () => {
         let id: string = '';
         act(() => {
           id = useNotificationStore.getState().addNotification('error', 'Error', false);
         });
         act(() => {
           useNotificationStore.getState().removeNotification(id);
         });
         expect(useNotificationStore.getState().notifications).toHaveLength(0);
       });

       it('auto-dismiss después de AUTO_DISMISS_MS', () => {
         act(() => {
           useNotificationStore.getState().addNotification('info', 'Auto dismiss');
         });
         expect(useNotificationStore.getState().notifications).toHaveLength(1);
         act(() => {
           jest.advanceTimersByTime(AUTO_DISMISS_MS + 100);
         });
         expect(useNotificationStore.getState().notifications).toHaveLength(0);
       });

       it('clearAll vacía todas las notificaciones', () => {
         act(() => {
           useNotificationStore.getState().addNotification('info', 'a', false);
           useNotificationStore.getState().addNotification('error', 'b', false);
           useNotificationStore.getState().clearAll();
         });
         expect(useNotificationStore.getState().notifications).toHaveLength(0);
       });
     });

     describe('Notifications Component', () => {
       it('no renderiza cuando no hay notificaciones', () => {
         render(<Notifications />);
         expect(screen.queryByTestId('notification-stack')).not.toBeInTheDocument();
       });

       it('renderiza notificaciones del store', () => {
         act(() => {
           useNotificationStore.getState().addNotification('info', 'Hello', false);
         });
         render(<Notifications />);
         expect(screen.getByTestId('notification-stack')).toBeInTheDocument();
         expect(screen.getByText('Hello')).toBeInTheDocument();
       });

       it('cada tipo tiene el data-type correcto', () => {
         let id: string = '';
         act(() => {
           id = useNotificationStore.getState().addNotification('error', 'Error msg', false);
         });
         render(<Notifications />);
         const notif = screen.getByTestId(`notification-${id}`);
         expect(notif.dataset.type).toBe('error');
       });

       it('botón cerrar remueve la notificación', () => {
         let id: string = '';
         act(() => {
           id = useNotificationStore.getState().addNotification('warning', 'Warn', false);
         });
         render(<Notifications />);
         fireEvent.click(screen.getByTestId(`close-${id}`));
         expect(useNotificationStore.getState().notifications).toHaveLength(0);
       });
     });

     describe('constantes', () => {
       it('MAX_VISIBLE es 5', () => {
         expect(MAX_VISIBLE).toBe(5);
       });

       it('AUTO_DISMISS_MS es 5000', () => {
         expect(AUTO_DISMISS_MS).toBe(5000);
       });
     });
   });

5. Ejecutar tests:
   cd ~/yeyo-os/frontend
   npx jest __tests__/components/common/Notifications.test.tsx --no-cache

VERIFICAR:
- [ ] Archivo src/lib/store/notification-store.ts existe
- [ ] Archivo src/components/common/Notifications.tsx existe
- [ ] 4 tipos: info (azul), success (verde), warning (amarillo), error (rojo)
- [ ] Auto-dismiss después de 5 segundos
- [ ] Máximo 5 visibles
- [ ] Cierre manual con botón ✕
- [ ] clearAll vacía todo
- [ ] TODOS los tests pasan

SI FALLA:
- Fake timers: usar jest.useFakeTimers() y jest.advanceTimersByTime()
- Zustand setState en tests: envolver en act()
- setTimeout en store: verificar que jest fake timers lo captura

NO HACER:
- No agregar sonidos a las notificaciones
- No persistir notificaciones en localStorage
- No crear notificaciones personalizadas con componentes custom

GATE: Notifications aparecen, auto-dismiss funciona, máximo 5, cierre manual, 4 tipos con colores correctos, todos los tests pasan.
```
