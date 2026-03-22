/**
 * Mock de PixiJS para tests (jsdom no tiene WebGL)
 */

const mockCanvas = typeof document !== 'undefined'
  ? document.createElement('canvas')
  : {} as HTMLCanvasElement;

const mockGeometry = {
  addAttribute: jest.fn(),
  attributes: {},
  indexBuffer: null,
};

const mockShader = {
  uniforms: {},
};

const mockMesh = {
  geometry: mockGeometry,
  shader: mockShader,
  position: { x: 0, y: 0 },
  scale: { x: 1, y: 1 },
  visible: true,
};

export const Application = jest.fn().mockImplementation(() => ({
  init: jest.fn().mockResolvedValue(undefined),
  destroy: jest.fn(),
  canvas: mockCanvas,
  screen: { width: 1920, height: 1080 },
  renderer: { resize: jest.fn() },
  ticker: { maxFPS: 0, add: jest.fn(), deltaTime: 16 },
  stage: { addChild: jest.fn(), removeChild: jest.fn() },
}));

export const Geometry = jest.fn().mockImplementation((options?: any) => ({
  ...mockGeometry,
  attributes: options?.attributes || {},
  indexBuffer: options?.indexBuffer || null,
}));

export const Shader = {
  from: jest.fn((options?: any) => ({
    ...mockShader,
    ...options,
  })),
};

export const Mesh = jest.fn().mockImplementation((options?: any) => ({
  ...mockMesh,
  ...options,
}));

export const Container = jest.fn().mockImplementation(() => ({
  addChild: jest.fn(),
  removeChild: jest.fn(),
  children: [],
}));

export const Graphics = jest.fn().mockImplementation(() => ({
  rect: jest.fn().mockReturnThis(),
  fill: jest.fn().mockReturnThis(),
  stroke: jest.fn().mockReturnThis(),
  clear: jest.fn().mockReturnThis(),
}));

export const Color = jest.fn();

export const Matrix = jest.fn().mockImplementation(() => ({
  identity: jest.fn().mockReturnThis(),
  translate: jest.fn().mockReturnThis(),
  scale: jest.fn().mockReturnThis(),
}));

export const Texture = {
  from: jest.fn(() => ({})),
  WHITE: {},
};

export default {
  Application,
  Geometry,
  Shader,
  Mesh,
  Container,
  Graphics,
  Color,
  Matrix,
  Texture,
};

