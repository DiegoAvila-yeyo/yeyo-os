/**
 * Tests para HubCanvas — Micro-fase 3.0
 */

import { render, screen, act } from '@testing-library/react';
import HubCanvas, { BACKGROUND_COLOR, TARGET_FPS } from '@/components/hub/HubCanvas';
import { useHubStore } from '@/lib/store/hub-store';
import { Application } from 'pixi.js';

const MockApplication = Application as jest.MockedClass<typeof Application>;

describe('HubCanvas', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useHubStore.setState({
      canvasSize: { width: 0, height: 0 },
      nodes: [],
    });
  });

  it('renderiza el contenedor del canvas', () => {
    render(<HubCanvas />);
    const container = screen.getByTestId('hub-canvas');
    expect(container).toBeInTheDocument();
  });

  it('el contenedor ocupa viewport completo por defecto', () => {
    render(<HubCanvas />);
    const container = screen.getByTestId('hub-canvas');
    expect(container.style.width).toBe('100vw');
    expect(container.style.height).toBe('100vh');
  });

  it('acepta dimensiones personalizadas', () => {
    render(<HubCanvas width={800} height={600} />);
    const container = screen.getByTestId('hub-canvas');
    expect(container.style.width).toBe('800px');
    expect(container.style.height).toBe('600px');
  });

  it('inicializa PixiJS Application al montar', async () => {
    await act(async () => {
      render(<HubCanvas />);
    });
    const instance = MockApplication.mock.results[0].value as any;
    expect(instance.init).toHaveBeenCalledWith(
      expect.objectContaining({
        background: BACKGROUND_COLOR,
        antialias: true,
        preferWebGLVersion: 2,
      })
    );
  });

  it('destruye la aplicación al desmontar', async () => {
    let unmount: () => void;
    await act(async () => {
      const result = render(<HubCanvas />);
      unmount = result.unmount;
    });
    act(() => {
      unmount!();
    });
    const instance = MockApplication.mock.results[0].value as any;
    expect(instance.destroy).toHaveBeenCalledWith(true);
  });

  it('actualiza el store con el tamaño del canvas', async () => {
    await act(async () => {
      render(<HubCanvas />);
    });
    const { canvasSize } = useHubStore.getState();
    expect(canvasSize.width).toBe(1920);
    expect(canvasSize.height).toBe(1080);
  });

  it('responde a eventos de resize', async () => {
    await act(async () => {
      render(<HubCanvas />);
    });
    act(() => {
      window.dispatchEvent(new Event('resize'));
    });
    const instance = MockApplication.mock.results[0].value as any;
    expect(instance.renderer.resize).toHaveBeenCalled();
  });

  it('exporta constante BACKGROUND_COLOR correcta', () => {
    expect(BACKGROUND_COLOR).toBe(0x0a0a0f);
  });

  it('exporta constante TARGET_FPS correcta', () => {
    expect(TARGET_FPS).toBe(60);
  });
});
