## ═══════════════════════════════════════
## MICRO-FASE 3.10 — Keyboard Shortcuts
## Tipo: VSCODE | Prompts: 1 | Complejidad: Simple
## ═══════════════════════════════════════

### PROMPT 3.10-1 [VSCODE] — Sistema global de atajos de teclado con Kill Switch

```
Estamos construyendo YeyoOS, un OS AI-nativo con interfaz Neural Hub. Esta es la micro-fase 3.10 de Capa 3 (Cuerpo): crear el sistema global de atajos de teclado.

CONTEXTO:
- Micro-fases 3.0-3.9 completadas: Canvas, nodos, chat, theme, notifications
- ⚠️ CRÍTICO: Kill Switch (Ctrl+Alt+K) DEBE funcionar SIEMPRE, incluso si la UI está rota
- Ctrl+Space: toggle MiniChat
- Ctrl+K: command palette (preparar hook, implementar después)
- Escape: cerrar panel activo
- Los shortcuts NO deben disparar cuando se escribe en un input/textarea
- Sistema de registro para shortcuts específicos de nodos

Abre el directorio ~/yeyo-os/frontend en VS Code.

CREAR:

1. Crear estructura:
   mkdir -p src/hooks
   mkdir -p __tests__/hooks

2. Crear archivo src/hooks/useKeyboardShortcuts.ts:

   Ruta: ~/yeyo-os/frontend/src/hooks/useKeyboardShortcuts.ts
   Contenido:

   /**
    * YeyoOS — useKeyboardShortcuts (Atajos de Teclado Globales)
    * Micro-fase 3.10 — Capa 3: Cuerpo
    *
    * ⚠️ CRÍTICO: Kill Switch (Ctrl+Alt+K) se registra PRIMERO
    * y funciona SIEMPRE, incluso en inputs y con UI rota.
    */

   import { useEffect, useCallback, useRef } from 'react';

   export interface ShortcutHandler {
     id: string;
     keys: string;
     handler: () => void;
     description: string;
     allowInInput?: boolean;
   }

   export interface KillSwitchState {
     isActive: boolean;
     toggledAt: number | null;
   }

   let killSwitchState: KillSwitchState = {
     isActive: false,
     toggledAt: null,
   };

   let killSwitchListeners: Array<(state: KillSwitchState) => void> = [];

   export function getKillSwitchState(): KillSwitchState {
     return { ...killSwitchState };
   }

   export function onKillSwitchChange(listener: (state: KillSwitchState) => void): () => void {
     killSwitchListeners.push(listener);
     return () => {
       killSwitchListeners = killSwitchListeners.filter((l) => l !== listener);
     };
   }

   export function toggleKillSwitch(): void {
     killSwitchState = {
       isActive: !killSwitchState.isActive,
       toggledAt: Date.now(),
     };
     killSwitchListeners.forEach((l) => l(killSwitchState));
   }

   export function resetKillSwitch(): void {
     killSwitchState = { isActive: false, toggledAt: null };
     killSwitchListeners = [];
   }

   function isInputElement(target: EventTarget | null): boolean {
     if (!target || !(target instanceof HTMLElement)) return false;
     const tagName = target.tagName.toLowerCase();
     return (
       tagName === 'input' ||
       tagName === 'textarea' ||
       tagName === 'select' ||
       target.isContentEditable
     );
   }

   function matchesShortcut(e: KeyboardEvent, keys: string): boolean {
     const parts = keys.toLowerCase().split('+');
     const needCtrl = parts.includes('ctrl');
     const needAlt = parts.includes('alt');
     const needShift = parts.includes('shift');
     const key = parts.filter((p) => !['ctrl', 'alt', 'shift'].includes(p))[0];

     return (
       e.ctrlKey === needCtrl &&
       e.altKey === needAlt &&
       e.shiftKey === needShift &&
       e.key.toLowerCase() === key
     );
   }

   /**
    * ⚠️ KILL SWITCH — Se registra PRIMERO, funciona SIEMPRE.
    * Debe ejecutarse antes de cualquier componente visual.
    */
   export function initKillSwitch(): () => void {
     const handler = (e: KeyboardEvent) => {
       if (e.ctrlKey && e.altKey && e.key.toLowerCase() === 'k') {
         e.preventDefault();
         e.stopPropagation();
         toggleKillSwitch();
         const state = getKillSwitchState();
         console.warn(
           `[YeyoOS] Kill Switch ${state.isActive ? 'ACTIVADO' : 'DESACTIVADO'} — Toda actividad IA ${state.isActive ? 'PAUSADA' : 'REANUDADA'}`
         );
       }
     };

     window.addEventListener('keydown', handler, { capture: true });
     return () => window.removeEventListener('keydown', handler, { capture: true });
   }

   export function useKeyboardShortcuts(shortcuts: ShortcutHandler[]): void {
     const shortcutsRef = useRef(shortcuts);
     shortcutsRef.current = shortcuts;

     const handleKeyDown = useCallback((e: KeyboardEvent) => {
       if (getKillSwitchState().isActive) return;

       for (const shortcut of shortcutsRef.current) {
         if (matchesShortcut(e, shortcut.keys)) {
           if (!shortcut.allowInInput && isInputElement(e.target)) continue;
           e.preventDefault();
           shortcut.handler();
           return;
         }
       }
     }, []);

     useEffect(() => {
       window.addEventListener('keydown', handleKeyDown);
       return () => window.removeEventListener('keydown', handleKeyDown);
     }, [handleKeyDown]);
   }

   export { isInputElement, matchesShortcut };

3. Crear archivo __tests__/hooks/useKeyboardShortcuts.test.ts:

   Ruta: ~/yeyo-os/frontend/__tests__/hooks/useKeyboardShortcuts.test.ts
   Contenido:

   /**
    * Tests para useKeyboardShortcuts — Micro-fase 3.10
    */

   import {
     initKillSwitch,
     getKillSwitchState,
     toggleKillSwitch,
     resetKillSwitch,
     onKillSwitchChange,
     isInputElement,
     matchesShortcut,
   } from '@/hooks/useKeyboardShortcuts';

   describe('Keyboard Shortcuts', () => {
     beforeEach(() => {
       resetKillSwitch();
     });

     describe('Kill Switch', () => {
       it('estado inicial es inactivo', () => {
         const state = getKillSwitchState();
         expect(state.isActive).toBe(false);
         expect(state.toggledAt).toBeNull();
       });

       it('toggleKillSwitch activa el Kill Switch', () => {
         toggleKillSwitch();
         const state = getKillSwitchState();
         expect(state.isActive).toBe(true);
         expect(state.toggledAt).toBeGreaterThan(0);
       });

       it('segundo toggle lo desactiva', () => {
         toggleKillSwitch();
         toggleKillSwitch();
         expect(getKillSwitchState().isActive).toBe(false);
       });

       it('notifica a los listeners al cambiar', () => {
         const listener = jest.fn();
         onKillSwitchChange(listener);
         toggleKillSwitch();
         expect(listener).toHaveBeenCalledWith(
           expect.objectContaining({ isActive: true })
         );
       });

       it('unsubscribe funciona', () => {
         const listener = jest.fn();
         const unsub = onKillSwitchChange(listener);
         unsub();
         toggleKillSwitch();
         expect(listener).not.toHaveBeenCalled();
       });

       it('initKillSwitch escucha Ctrl+Alt+K en window', () => {
         const cleanup = initKillSwitch();
         const event = new KeyboardEvent('keydown', {
           key: 'k',
           ctrlKey: true,
           altKey: true,
           bubbles: true,
         });
         window.dispatchEvent(event);
         expect(getKillSwitchState().isActive).toBe(true);
         cleanup();
       });

       it('cleanup de initKillSwitch deja de escuchar', () => {
         const cleanup = initKillSwitch();
         cleanup();
         const event = new KeyboardEvent('keydown', {
           key: 'k',
           ctrlKey: true,
           altKey: true,
           bubbles: true,
         });
         window.dispatchEvent(event);
         expect(getKillSwitchState().isActive).toBe(false);
       });

       it('resetKillSwitch restaura estado inicial', () => {
         toggleKillSwitch();
         resetKillSwitch();
         expect(getKillSwitchState().isActive).toBe(false);
         expect(getKillSwitchState().toggledAt).toBeNull();
       });
     });

     describe('matchesShortcut', () => {
       it('detecta Ctrl+Space', () => {
         const event = new KeyboardEvent('keydown', {
           key: ' ',
           ctrlKey: true,
         });
         expect(matchesShortcut(event, 'ctrl+ ')).toBe(true);
       });

       it('detecta Ctrl+K', () => {
         const event = new KeyboardEvent('keydown', {
           key: 'k',
           ctrlKey: true,
         });
         expect(matchesShortcut(event, 'ctrl+k')).toBe(true);
       });

       it('detecta Escape', () => {
         const event = new KeyboardEvent('keydown', { key: 'escape' });
         expect(matchesShortcut(event, 'escape')).toBe(true);
       });

       it('no matchea si faltan modificadores', () => {
         const event = new KeyboardEvent('keydown', { key: 'k' });
         expect(matchesShortcut(event, 'ctrl+k')).toBe(false);
       });

       it('no matchea si hay modificadores extra', () => {
         const event = new KeyboardEvent('keydown', {
           key: 'k',
           ctrlKey: true,
           altKey: true,
         });
         expect(matchesShortcut(event, 'ctrl+k')).toBe(false);
       });
     });

     describe('isInputElement', () => {
       it('retorna true para input', () => {
         const input = document.createElement('input');
         expect(isInputElement(input)).toBe(true);
       });

       it('retorna true para textarea', () => {
         const textarea = document.createElement('textarea');
         expect(isInputElement(textarea)).toBe(true);
       });

       it('retorna true para select', () => {
         const select = document.createElement('select');
         expect(isInputElement(select)).toBe(true);
       });

       it('retorna true para contentEditable', () => {
         const div = document.createElement('div');
         div.contentEditable = 'true';
         expect(isInputElement(div)).toBe(true);
       });

       it('retorna false para div normal', () => {
         const div = document.createElement('div');
         expect(isInputElement(div)).toBe(false);
       });

       it('retorna false para null', () => {
         expect(isInputElement(null)).toBe(false);
       });
     });
   });

4. Ejecutar tests:
   cd ~/yeyo-os/frontend
   npx jest __tests__/hooks/useKeyboardShortcuts.test.ts --no-cache

VERIFICAR:
- [ ] Archivo src/hooks/useKeyboardShortcuts.ts existe
- [ ] ⚠️ Kill Switch (Ctrl+Alt+K) funciona con capture: true (se ejecuta PRIMERO)
- [ ] Kill Switch toggle activa/desactiva
- [ ] Kill Switch notifica a listeners
- [ ] matchesShortcut detecta combinaciones de teclas correctamente
- [ ] isInputElement detecta inputs/textarea/select/contentEditable
- [ ] Shortcuts NO disparan dentro de inputs (excepto allowInInput)
- [ ] initKillSwitch retorna función cleanup
- [ ] TODOS los tests pasan

SI FALLA:
- KeyboardEvent: verificar que ctrlKey/altKey se pasan correctamente
- capture: true: el Kill Switch se registra en fase de captura para ejecutarse primero
- listeners: verificar cleanup en resetKillSwitch

NO HACER:
- No implementar command palette (solo preparar el shortcut)
- No agregar shortcuts de aplicaciones externas
- No usar un framework de shortcuts (mantener ligero)

GATE: Kill Switch funciona SIEMPRE (capture:true), shortcuts detectados correctamente, no disparan en inputs, todos los tests pasan.
```
