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

export function isInputElement(target: EventTarget | null): boolean {
  if (!target || !(target instanceof HTMLElement)) return false;
  const tagName = target.tagName.toLowerCase();
  return (
    tagName === 'input' ||
    tagName === 'textarea' ||
    tagName === 'select' ||
    target.contentEditable === 'true'
  );
}

export function matchesShortcut(e: KeyboardEvent, keys: string): boolean {
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
