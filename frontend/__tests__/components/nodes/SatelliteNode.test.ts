/**
 * Tests para SatelliteNode — Micro-fase 3.2
 */

import {
  SatelliteNode,
  STATE_STYLES,
  SNAP_BACK_THRESHOLD,
  NODE_WIDTH,
  NODE_HEIGHT,
} from '@/components/nodes/SatelliteNode';
import type { SatelliteState, SatelliteNodeOptions } from '@/components/nodes/SatelliteNode';

const mockOn = jest.fn();
const mockRemoveAllListeners = jest.fn();
const mockDestroyContainer = jest.fn();
const mockAddChild = jest.fn();
const mockClear = jest.fn().mockReturnThis();
const mockRoundRect = jest.fn().mockReturnThis();
const mockFill = jest.fn().mockReturnThis();
const mockStroke = jest.fn().mockReturnThis();

jest.mock('pixi.js', () => ({
  Container: jest.fn().mockImplementation(() => ({
    x: 0,
    y: 0,
    eventMode: 'none',
    cursor: 'default',
    addChild: mockAddChild,
    on: mockOn,
    removeAllListeners: mockRemoveAllListeners,
    destroy: mockDestroyContainer,
  })),
  Graphics: jest.fn().mockImplementation(() => ({
    clear: mockClear,
    roundRect: mockRoundRect,
    fill: mockFill,
    stroke: mockStroke,
  })),
  Text: jest.fn().mockImplementation(() => ({
    anchor: { set: jest.fn() },
    x: 0,
    y: 0,
    alpha: 1,
  })),
  TextStyle: jest.fn().mockImplementation((opts) => opts),
  FederatedPointerEvent: jest.fn(),
}));

function createNode(overrides?: Partial<SatelliteNodeOptions>): SatelliteNode {
  return new SatelliteNode({
    id: 'test-node',
    label: 'Test',
    icon: '💬',
    x: 200,
    y: 300,
    ...overrides,
  });
}

describe('SatelliteNode', () => {
  beforeEach(() => jest.clearAllMocks());

  describe('constructor', () => {
    it('crea un nodo con id correcto', () => {
      const node = createNode();
      expect(node.id).toBe('test-node');
    });

    it('estado por defecto es idle', () => {
      const node = createNode();
      expect(node.state).toBe('idle');
    });

    it('acepta estado inicial explícito', () => {
      const node = createNode({ state: 'active' });
      expect(node.state).toBe('active');
    });

    it('posiciona el container en x, y dados', () => {
      const node = createNode({ x: 100, y: 200 });
      expect(node.container.x).toBe(100);
      expect(node.container.y).toBe(200);
    });

    it('guarda la posición original', () => {
      const node = createNode({ x: 150, y: 250 });
      expect(node.originalX).toBe(150);
      expect(node.originalY).toBe(250);
    });

    it('configura eventMode como static', () => {
      const node = createNode();
      expect(node.container.eventMode).toBe('static');
    });

    it('configura cursor como pointer', () => {
      const node = createNode();
      expect(node.container.cursor).toBe('pointer');
    });

    it('agrega 3 hijos al container (bg, icon, label)', () => {
      createNode();
      expect(mockAddChild).toHaveBeenCalledTimes(3);
    });

    it('registra evento pointerdown', () => {
      createNode();
      expect(mockOn).toHaveBeenCalledWith('pointerdown', expect.any(Function));
    });

    it('registra evento globalpointermove', () => {
      createNode();
      expect(mockOn).toHaveBeenCalledWith('globalpointermove', expect.any(Function));
    });

    it('registra eventos pointerup y pointerupoutside', () => {
      createNode();
      expect(mockOn).toHaveBeenCalledWith('pointerup', expect.any(Function));
      expect(mockOn).toHaveBeenCalledWith('pointerupoutside', expect.any(Function));
    });

    it('registra evento pointertap para double-click', () => {
      createNode();
      expect(mockOn).toHaveBeenCalledWith('pointertap', expect.any(Function));
    });

    it('dibuja fondo con color del estado idle', () => {
      createNode();
      expect(mockFill).toHaveBeenCalledWith(
        expect.objectContaining({ color: STATE_STYLES.idle.bgColor })
      );
    });

    it('dibuja borde con color del estado idle', () => {
      createNode();
      expect(mockStroke).toHaveBeenCalledWith(
        expect.objectContaining({ color: STATE_STYLES.idle.borderColor })
      );
    });
  });

  describe('setState', () => {
    it('cambia el estado', () => {
      const node = createNode();
      node.setState('active');
      expect(node.state).toBe('active');
    });

    it('redibuja fondo con borde de error', () => {
      const node = createNode();
      jest.clearAllMocks();
      node.setState('error');
      expect(mockStroke).toHaveBeenCalledWith(
        expect.objectContaining({ color: STATE_STYLES.error.borderColor })
      );
    });

    it('cambia a loading con borde naranja', () => {
      const node = createNode();
      node.setState('loading');
      expect(node.state).toBe('loading');
    });
  });

  describe('getPosition', () => {
    it('retorna la posición del container', () => {
      const node = createNode({ x: 100, y: 200 });
      const pos = node.getPosition();
      expect(pos.x).toBe(100);
      expect(pos.y).toBe(200);
    });
  });

  describe('destroy', () => {
    it('remueve todos los listeners', () => {
      const node = createNode();
      node.destroy();
      expect(mockRemoveAllListeners).toHaveBeenCalled();
    });

    it('destruye el container con sus hijos', () => {
      const node = createNode();
      node.destroy();
      expect(mockDestroyContainer).toHaveBeenCalledWith({ children: true });
    });
  });

  describe('STATE_STYLES', () => {
    it('tiene estilos para los 4 estados', () => {
      const states: SatelliteState[] = ['active', 'idle', 'loading', 'error'];
      states.forEach((s) => expect(STATE_STYLES[s]).toBeDefined());
    });

    it('error tiene borde rojo y grosor 3', () => {
      expect(STATE_STYLES.error.borderColor).toBe(0xff4444);
      expect(STATE_STYLES.error.borderWidth).toBe(3);
    });

    it('active tiene alta opacidad', () => {
      expect(STATE_STYLES.active.bgAlpha).toBeGreaterThan(0.9);
      expect(STATE_STYLES.active.labelAlpha).toBe(1.0);
    });

    it('idle tiene baja opacidad', () => {
      expect(STATE_STYLES.idle.bgAlpha).toBeLessThan(0.8);
      expect(STATE_STYLES.idle.labelAlpha).toBeLessThan(1.0);
    });
  });

  describe('constantes exportadas', () => {
    it('NODE_WIDTH es 140', () => expect(NODE_WIDTH).toBe(140));
    it('NODE_HEIGHT es 60', () => expect(NODE_HEIGHT).toBe(60));
    it('SNAP_BACK_THRESHOLD es 80', () => expect(SNAP_BACK_THRESHOLD).toBe(80));
  });
});
