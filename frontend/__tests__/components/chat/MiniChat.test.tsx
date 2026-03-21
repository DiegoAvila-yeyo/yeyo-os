/**
 * Tests para MiniChat — Micro-fase 3.6
 */

import { render, screen, fireEvent, act } from '@testing-library/react';
import MiniChat, { DEFAULT_WIDTH, DEFAULT_HEIGHT, MAX_VISIBLE_MESSAGES } from '@/components/chat/MiniChat';
import { useChatStore } from '@/lib/store/chat-store';

describe('MiniChat', () => {
  beforeEach(() => {
    act(() => {
      useChatStore.setState({ messages: [], isStreaming: false, isPanelOpen: false, error: null });
    });
  });

  describe('visibility', () => {
    it('no es visible por defecto', () => {
      render(<MiniChat />);
      expect(screen.queryByTestId('minichat')).not.toBeInTheDocument();
    });

    it('Ctrl+Space lo hace visible', () => {
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
    it('muestra "Sin mensajes aún" cuando está vacío', () => {
      render(<MiniChat />);
      fireEvent.keyDown(window, { key: ' ', code: 'Space', ctrlKey: true });
      expect(screen.getByText('Sin mensajes aún')).toBeInTheDocument();
    });

    it(`muestra solo los últimos ${MAX_VISIBLE_MESSAGES} mensajes`, () => {
      act(() => {
        for (let i = 0; i < 5; i++) {
          useChatStore.getState().addMessage({ id: `msg-${i}`, role: 'user', content: `Mensaje ${i}`, timestamp: i });
        }
      });
      render(<MiniChat />);
      fireEvent.keyDown(window, { key: ' ', code: 'Space', ctrlKey: true });
      expect(screen.getAllByTestId(/^minichat-msg-/)).toHaveLength(MAX_VISIBLE_MESSAGES);
    });

    it('muestra los últimos (no los primeros)', () => {
      act(() => {
        for (let i = 0; i < 5; i++) {
          useChatStore.getState().addMessage({ id: `msg-${i}`, role: 'user', content: `Mensaje ${i}`, timestamp: i });
        }
      });
      render(<MiniChat />);
      fireEvent.keyDown(window, { key: ' ', code: 'Space', ctrlKey: true });
      expect(screen.getByText('Mensaje 4')).toBeInTheDocument();
      expect(screen.queryByText('Mensaje 0')).not.toBeInTheDocument();
    });
  });

  describe('expand', () => {
    it('botón expandir abre ChatPanel', () => {
      render(<MiniChat />);
      fireEvent.keyDown(window, { key: ' ', code: 'Space', ctrlKey: true });
      fireEvent.click(screen.getByTestId('minichat-expand'));
      expect(useChatStore.getState().isPanelOpen).toBe(true);
    });

    it('botón expandir cierra MiniChat', () => {
      render(<MiniChat />);
      fireEvent.keyDown(window, { key: ' ', code: 'Space', ctrlKey: true });
      fireEvent.click(screen.getByTestId('minichat-expand'));
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
      fireEvent.change(screen.getByTestId('minichat-input'), { target: { value: 'Hola' } });
      fireEvent.click(screen.getByTestId('minichat-send'));
      expect(useChatStore.getState().messages).toHaveLength(1);
      expect(useChatStore.getState().messages[0].content).toBe('Hola');
    });

    it('limpiar input después de enviar', () => {
      render(<MiniChat />);
      fireEvent.keyDown(window, { key: ' ', code: 'Space', ctrlKey: true });
      const input = screen.getByTestId('minichat-input') as HTMLInputElement;
      fireEvent.change(input, { target: { value: 'Hola' } });
      fireEvent.click(screen.getByTestId('minichat-send'));
      expect(input.value).toBe('');
    });

    it('botón enviar deshabilitado con input vacío', () => {
      render(<MiniChat />);
      fireEvent.keyDown(window, { key: ' ', code: 'Space', ctrlKey: true });
      expect(screen.getByTestId('minichat-send')).toBeDisabled();
    });

    it('input deshabilitado durante streaming', () => {
      act(() => { useChatStore.setState({ isStreaming: true }); });
      render(<MiniChat />);
      fireEvent.keyDown(window, { key: ' ', code: 'Space', ctrlKey: true });
      expect(screen.getByTestId('minichat-input')).toBeDisabled();
    });
  });

  describe('dimensiones y layout', () => {
    it('tiene dimensiones por defecto correctas', () => {
      render(<MiniChat />);
      fireEvent.keyDown(window, { key: ' ', code: 'Space', ctrlKey: true });
      const mc = screen.getByTestId('minichat');
      expect(mc.style.width).toBe(`${DEFAULT_WIDTH}px`);
      expect(mc.style.height).toBe(`${DEFAULT_HEIGHT}px`);
    });

    it('tiene handle de resize', () => {
      render(<MiniChat />);
      fireEvent.keyDown(window, { key: ' ', code: 'Space', ctrlKey: true });
      expect(screen.getByTestId('minichat-resize')).toBeInTheDocument();
    });

    it('header tiene clase cursor-move para drag', () => {
      render(<MiniChat />);
      fireEvent.keyDown(window, { key: ' ', code: 'Space', ctrlKey: true });
      expect(screen.getByTestId('minichat-header').className).toContain('cursor-move');
    });

    it('posición inicial personalizable', () => {
      render(<MiniChat initialX={100} initialY={200} />);
      fireEvent.keyDown(window, { key: ' ', code: 'Space', ctrlKey: true });
      const mc = screen.getByTestId('minichat');
      expect(mc.style.left).toBe('100px');
      expect(mc.style.top).toBe('200px');
    });
  });
});
