/**
 * Mock de PixiJS para tests (jsdom no tiene WebGL)
 */

const mockCanvas = typeof document !== 'undefined'
  ? document.createElement('canvas')
  : {} as HTMLCanvasElement;

export const Application = jest.fn().mockImplementation(() => ({
  init: jest.fn().mockResolvedValue(undefined),
  destroy: jest.fn(),
  canvas: mockCanvas,
  screen: { width: 1920, height: 1080 },
  renderer: { resize: jest.fn() },
  ticker: { maxFPS: 0 },
}));
