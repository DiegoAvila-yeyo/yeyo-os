/**
 * Tests para ChatPanel — Micro-fase 3.5
 */

import { render, screen, fireEvent, act } from '@testing-library/react';
import ChatPanel, { PANEL_WIDTH, BATCH_FLUSH_MS } from '@/components/chat/ChatPanel';
import { useChatStore } from '@/lib/store/chat-store';

jest.mock('react-markdown', () => {
  return function MockReactMarkdown({ children }: { children: string }) {
    return <div data-testid="markdown-content">{children}</div>;
  };
});
jest.mock('remark-gfm', () => () => {});

describe('ChatPanel', () => {
  beforeEach(() => {
    act(() => {
      useChatStore.setState({ messages: [], isStreaming: false, isPanelOpen: true, error: null });
    });
  });

  describe('rendering', () => {
    it('renderiza cuando isPanelOpen es true', () => {
      render(<ChatPanel />);
      expect(screen.getByTestId('chat-panel')).toBeInTheDocument();
    });

    it('no renderiza cuando isPanelOpen es false', () => {
      act(() => { useChatStore.setState({ isPanelOpen: false }); });
      render(<ChatPanel />);
      expect(screen.queryByTestId('chat-panel')).not.toBeInTheDocument();
    });

    it('tiene el ancho correcto (400px)', () => {
      render(<ChatPanel />);
      expect(screen.getByTestId('chat-panel').style.width).toBe(`${PANEL_WIDTH}px`);
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

    it('muestra el botón de cerrar', () => {
      render(<ChatPanel />);
      expect(screen.getByTestId('close-panel')).toBeInTheDocument();
    });
  });

  describe('mensajes', () => {
    it('muestra mensajes del store', () => {
      act(() => {
        useChatStore.getState().addMessage({ id: 'msg-1', role: 'user', content: 'Hola YeyoOS', timestamp: Date.now() });
      });
      render(<ChatPanel />);
      expect(screen.getByText('Hola YeyoOS')).toBeInTheDocument();
    });

    it('muestra indicador de streaming', () => {
      act(() => {
        useChatStore.getState().addMessage({ id: 's1', role: 'assistant', content: 'Generando...', timestamp: Date.now(), isStreaming: true });
      });
      render(<ChatPanel />);
      expect(screen.getByTestId('streaming-indicator')).toBeInTheDocument();
    });

    it('renderiza markdown en mensajes del asistente', () => {
      act(() => {
        useChatStore.getState().addMessage({ id: 'msg-1', role: 'assistant', content: '**Hola** mundo', timestamp: Date.now() });
      });
      render(<ChatPanel />);
      expect(screen.getByTestId('markdown-content')).toBeInTheDocument();
    });

    it('muestra múltiples mensajes', () => {
      act(() => {
        useChatStore.getState().addMessage({ id: 'u1', role: 'user', content: 'Pregunta', timestamp: 1 });
        useChatStore.getState().addMessage({ id: 'a1', role: 'assistant', content: 'Respuesta', timestamp: 2 });
      });
      render(<ChatPanel />);
      expect(screen.getByText('Pregunta')).toBeInTheDocument();
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
      expect(screen.getByTestId('send-button')).toBeDisabled();
    });

    it('botón enviar se habilita con texto', () => {
      render(<ChatPanel />);
      fireEvent.change(screen.getByTestId('chat-input'), { target: { value: 'hola' } });
      expect(screen.getByTestId('send-button')).not.toBeDisabled();
    });

    it('input deshabilitado durante streaming', () => {
      act(() => { useChatStore.setState({ isStreaming: true }); });
      render(<ChatPanel />);
      expect(screen.getByTestId('chat-input')).toBeDisabled();
    });

    it('botón enviar deshabilitado durante streaming', () => {
      act(() => { useChatStore.setState({ isStreaming: true }); });
      render(<ChatPanel />);
      fireEvent.change(screen.getByTestId('chat-input'), { target: { value: 'test' } });
      expect(screen.getByTestId('send-button')).toBeDisabled();
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
      act(() => { useChatStore.setState({ error: 'Connection failed' }); });
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
    it('PANEL_WIDTH es 400', () => expect(PANEL_WIDTH).toBe(400));
    it('BATCH_FLUSH_MS es 50', () => expect(BATCH_FLUSH_MS).toBe(50));
  });
});
