/**
 * Tests para ChatStore — Micro-fase 3.5
 */

import { useChatStore } from '@/lib/store/chat-store';
import type { ChatMessage } from '@/lib/store/chat-store';
import { act } from '@testing-library/react';

describe('ChatStore', () => {
  beforeEach(() => {
    act(() => {
      useChatStore.setState({ messages: [], isStreaming: false, isPanelOpen: false, error: null });
    });
  });

  describe('addMessage', () => {
    it('agrega un mensaje al array', () => {
      const msg: ChatMessage = { id: 'msg-1', role: 'user', content: 'Hola YeyoOS', timestamp: Date.now() };
      act(() => { useChatStore.getState().addMessage(msg); });
      expect(useChatStore.getState().messages).toHaveLength(1);
      expect(useChatStore.getState().messages[0].content).toBe('Hola YeyoOS');
    });

    it('mantiene el orden de los mensajes', () => {
      act(() => {
        useChatStore.getState().addMessage({ id: 'msg-1', role: 'user', content: 'Primero', timestamp: 1 });
        useChatStore.getState().addMessage({ id: 'msg-2', role: 'assistant', content: 'Segundo', timestamp: 2 });
      });
      const { messages } = useChatStore.getState();
      expect(messages[0].content).toBe('Primero');
      expect(messages[1].content).toBe('Segundo');
    });

    it('agrega múltiples mensajes independientes', () => {
      act(() => {
        for (let i = 0; i < 5; i++) {
          useChatStore.getState().addMessage({ id: `msg-${i}`, role: 'user', content: `msg ${i}`, timestamp: i });
        }
      });
      expect(useChatStore.getState().messages).toHaveLength(5);
    });
  });

  describe('updateStreamingMessage', () => {
    it('actualiza el contenido de un mensaje existente', () => {
      act(() => {
        useChatStore.getState().addMessage({ id: 'stream-1', role: 'assistant', content: 'Hola', timestamp: 1, isStreaming: true });
        useChatStore.getState().updateStreamingMessage('stream-1', 'Hola mundo');
      });
      expect(useChatStore.getState().messages[0].content).toBe('Hola mundo');
    });

    it('no modifica otros mensajes', () => {
      act(() => {
        useChatStore.getState().addMessage({ id: 'msg-1', role: 'user', content: 'Original', timestamp: 1 });
        useChatStore.getState().addMessage({ id: 'stream-1', role: 'assistant', content: '', timestamp: 2, isStreaming: true });
        useChatStore.getState().updateStreamingMessage('stream-1', 'Updated');
      });
      expect(useChatStore.getState().messages[0].content).toBe('Original');
      expect(useChatStore.getState().messages[1].content).toBe('Updated');
    });
  });

  describe('finalizeStreamingMessage', () => {
    it('marca el mensaje como no streaming', () => {
      act(() => {
        useChatStore.getState().addMessage({ id: 'stream-1', role: 'assistant', content: 'Respuesta', timestamp: 1, isStreaming: true });
        useChatStore.getState().finalizeStreamingMessage('stream-1');
      });
      expect(useChatStore.getState().messages[0].isStreaming).toBe(false);
    });

    it('pone isStreaming global en false', () => {
      act(() => {
        useChatStore.setState({ isStreaming: true });
        useChatStore.getState().addMessage({ id: 's1', role: 'assistant', content: '', timestamp: 1, isStreaming: true });
        useChatStore.getState().finalizeStreamingMessage('s1');
      });
      expect(useChatStore.getState().isStreaming).toBe(false);
    });
  });

  describe('panel state', () => {
    it('setPanelOpen(true) abre el panel', () => {
      act(() => { useChatStore.getState().setPanelOpen(true); });
      expect(useChatStore.getState().isPanelOpen).toBe(true);
    });

    it('setPanelOpen(false) cierra el panel', () => {
      act(() => {
        useChatStore.getState().setPanelOpen(true);
        useChatStore.getState().setPanelOpen(false);
      });
      expect(useChatStore.getState().isPanelOpen).toBe(false);
    });

    it('togglePanel alterna el estado', () => {
      act(() => { useChatStore.getState().togglePanel(); });
      expect(useChatStore.getState().isPanelOpen).toBe(true);
      act(() => { useChatStore.getState().togglePanel(); });
      expect(useChatStore.getState().isPanelOpen).toBe(false);
    });
  });

  describe('setStreaming', () => {
    it('setStreaming(true) activa el streaming', () => {
      act(() => { useChatStore.getState().setStreaming(true); });
      expect(useChatStore.getState().isStreaming).toBe(true);
    });
  });

  describe('error handling', () => {
    it('setError guarda el error', () => {
      act(() => { useChatStore.getState().setError('Connection failed'); });
      expect(useChatStore.getState().error).toBe('Connection failed');
    });

    it('setError(null) limpia el error', () => {
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
        useChatStore.getState().addMessage({ id: 'msg-1', role: 'user', content: 'test', timestamp: 1 });
        useChatStore.getState().clearMessages();
      });
      expect(useChatStore.getState().messages).toHaveLength(0);
    });
  });
});
