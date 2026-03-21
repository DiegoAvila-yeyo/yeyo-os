/**
 * Tests para AppLayout — Micro-fase 3.14
 */

import { render, screen, act } from '@testing-library/react';
import AppLayout, { MIN_WIDTH, MIN_HEIGHT } from '@/components/layout/AppLayout';

// Mock UIStore
jest.mock('@/lib/store/ui-store', () => ({
  useUIStore: jest.fn(() => ({
    sidebarCollapsed: false,
    activePanel: null,
  })),
}));

function setWindowSize(width: number, height: number) {
  Object.defineProperty(window, 'innerWidth', { value: width, writable: true, configurable: true });
  Object.defineProperty(window, 'innerHeight', { value: height, writable: true, configurable: true });
  window.dispatchEvent(new Event('resize'));
}

describe('AppLayout', () => {
  beforeEach(() => {
    setWindowSize(1920, 1080);
  });

  describe('rendering', () => {
    it('renderiza el layout principal', () => {
      render(
        <AppLayout canvas={<div data-testid="mock-canvas">Canvas</div>} />
      );
      expect(screen.getByTestId('app-layout')).toBeInTheDocument();
    });

    it('renderiza el canvas area', () => {
      render(
        <AppLayout canvas={<div data-testid="mock-canvas">Canvas</div>} />
      );
      expect(screen.getByTestId('canvas-area')).toBeInTheDocument();
      expect(screen.getByTestId('mock-canvas')).toBeInTheDocument();
    });

    it('canvas area tiene clase flex-1', () => {
      render(<AppLayout canvas={<div>Canvas</div>} />);
      const canvasArea = screen.getByTestId('canvas-area');
      expect(canvasArea.className).toContain('flex-1');
    });

    it('layout root es flex', () => {
      render(<AppLayout canvas={<div>Canvas</div>} />);
      const layout = screen.getByTestId('app-layout');
      expect(layout.className).toContain('flex');
    });

    it('renderiza children opcionales', () => {
      render(
        <AppLayout
          canvas={<div>Canvas</div>}
          chatPanel={<div data-testid="chat">Chat</div>}
          miniChat={<div data-testid="mini">Mini</div>}
          notifications={<div data-testid="notifs">Notifs</div>}
        />
      );
      expect(screen.getByTestId('chat')).toBeInTheDocument();
      expect(screen.getByTestId('mini')).toBeInTheDocument();
      expect(screen.getByTestId('notifs')).toBeInTheDocument();
    });

    it('funciona sin paneles opcionales', () => {
      render(<AppLayout canvas={<div data-testid="c">C</div>} />);
      expect(screen.getByTestId('app-layout')).toBeInTheDocument();
    });

    it('background es el color oscuro del tema', () => {
      render(<AppLayout canvas={<div>C</div>} />);
      const layout = screen.getByTestId('app-layout');
      expect(layout.className).toContain('#0a0a0f');
    });
  });

  describe('minimum size warning', () => {
    it('muestra warning cuando ancho es menor al minimo', () => {
      render(<AppLayout canvas={<div>Canvas</div>} />);
      act(() => { setWindowSize(800, 1080); });
      expect(screen.getByTestId('minimum-size-warning')).toBeInTheDocument();
    });

    it('muestra warning cuando alto es menor al minimo', () => {
      render(<AppLayout canvas={<div>Canvas</div>} />);
      act(() => { setWindowSize(1920, 500); });
      expect(screen.getByTestId('minimum-size-warning')).toBeInTheDocument();
    });

    it('muestra warning cuando ambos son menores', () => {
      render(<AppLayout canvas={<div>Canvas</div>} />);
      act(() => { setWindowSize(800, 600); });
      expect(screen.getByTestId('minimum-size-warning')).toBeInTheDocument();
    });

    it('muestra dimension actual en el warning', () => {
      render(<AppLayout canvas={<div>Canvas</div>} />);
      act(() => { setWindowSize(800, 600); });
      expect(screen.getByText(/800x600/)).toBeInTheDocument();
    });

    it('no muestra warning en tamaño adecuado', () => {
      render(<AppLayout canvas={<div>Canvas</div>} />);
      expect(screen.queryByTestId('minimum-size-warning')).not.toBeInTheDocument();
    });

    it('no muestra warning justo en el minimo (1024x768)', () => {
      render(<AppLayout canvas={<div>Canvas</div>} />);
      act(() => { setWindowSize(1024, 768); });
      expect(screen.queryByTestId('minimum-size-warning')).not.toBeInTheDocument();
      expect(screen.getByTestId('app-layout')).toBeInTheDocument();
    });

    it('warning menciona las dimensiones minimas requeridas', () => {
      render(<AppLayout canvas={<div>Canvas</div>} />);
      act(() => { setWindowSize(800, 600); });
      expect(screen.getByText(/1024x768/)).toBeInTheDocument();
    });
  });

  describe('constantes', () => {
    it('MIN_WIDTH es 1024', () => {
      expect(MIN_WIDTH).toBe(1024);
    });

    it('MIN_HEIGHT es 768', () => {
      expect(MIN_HEIGHT).toBe(768);
    });
  });
});
