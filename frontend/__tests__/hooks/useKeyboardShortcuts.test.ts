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

    it('notifica con estado correcto al desactivar', () => {
      const listener = jest.fn();
      toggleKillSwitch();
      onKillSwitchChange(listener);
      toggleKillSwitch();
      expect(listener).toHaveBeenCalledWith(
        expect.objectContaining({ isActive: false })
      );
    });

    it('unsubscribe funciona', () => {
      const listener = jest.fn();
      const unsub = onKillSwitchChange(listener);
      unsub();
      toggleKillSwitch();
      expect(listener).not.toHaveBeenCalled();
    });

    it('multiples listeners son notificados', () => {
      const l1 = jest.fn();
      const l2 = jest.fn();
      onKillSwitchChange(l1);
      onKillSwitchChange(l2);
      toggleKillSwitch();
      expect(l1).toHaveBeenCalledTimes(1);
      expect(l2).toHaveBeenCalledTimes(1);
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

    it('getKillSwitchState retorna copia (no referencia)', () => {
      const state1 = getKillSwitchState();
      toggleKillSwitch();
      const state2 = getKillSwitchState();
      expect(state1.isActive).toBe(false);
      expect(state2.isActive).toBe(true);
    });
  });

  describe('matchesShortcut', () => {
    it('detecta Ctrl+K', () => {
      const event = new KeyboardEvent('keydown', { key: 'k', ctrlKey: true });
      expect(matchesShortcut(event, 'ctrl+k')).toBe(true);
    });

    it('detecta Escape', () => {
      const event = new KeyboardEvent('keydown', { key: 'escape' });
      expect(matchesShortcut(event, 'escape')).toBe(true);
    });

    it('detecta Ctrl+Alt+K', () => {
      const event = new KeyboardEvent('keydown', { key: 'k', ctrlKey: true, altKey: true });
      expect(matchesShortcut(event, 'ctrl+alt+k')).toBe(true);
    });

    it('no matchea si faltan modificadores', () => {
      const event = new KeyboardEvent('keydown', { key: 'k' });
      expect(matchesShortcut(event, 'ctrl+k')).toBe(false);
    });

    it('no matchea si hay modificadores extra', () => {
      const event = new KeyboardEvent('keydown', { key: 'k', ctrlKey: true, altKey: true });
      expect(matchesShortcut(event, 'ctrl+k')).toBe(false);
    });

    it('es case-insensitive para la tecla', () => {
      const event = new KeyboardEvent('keydown', { key: 'K', ctrlKey: true });
      expect(matchesShortcut(event, 'ctrl+k')).toBe(true);
    });

    it('no matchea tecla diferente', () => {
      const event = new KeyboardEvent('keydown', { key: 'j', ctrlKey: true });
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

    it('retorna false para button', () => {
      const btn = document.createElement('button');
      expect(isInputElement(btn)).toBe(false);
    });
  });
});
