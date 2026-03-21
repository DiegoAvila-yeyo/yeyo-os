/**
 * Tests para ConnectionLine — Micro-fase 3.4
 */

import {
  ConnectionLine,
  DATA_TYPE_COLORS,
  ACTIVE_ALPHA,
  IDLE_ALPHA,
  DOT_COUNT,
} from '@/components/hub/ConnectionLine';
import type { DataType } from '@/components/hub/ConnectionLine';

const mockClear = jest.fn().mockReturnThis();
const mockMoveTo = jest.fn().mockReturnThis();
const mockBezierCurveTo = jest.fn().mockReturnThis();
const mockStroke = jest.fn().mockReturnThis();
const mockCircle = jest.fn().mockReturnThis();
const mockFill = jest.fn().mockReturnThis();
const mockDestroy = jest.fn();
const mockAddChild = jest.fn();

jest.mock('pixi.js', () => ({
  Container: jest.fn().mockImplementation(() => ({
    addChild: mockAddChild,
    destroy: mockDestroy,
  })),
  Graphics: jest.fn().mockImplementation(() => ({
    clear: mockClear,
    moveTo: mockMoveTo,
    bezierCurveTo: mockBezierCurveTo,
    stroke: mockStroke,
    circle: mockCircle,
    fill: mockFill,
  })),
}));

const defaultOpts = { fromX: 0, fromY: 0, toX: 200, toY: 200, dataType: 'chat' as DataType, active: true };

describe('ConnectionLine', () => {
  beforeEach(() => jest.clearAllMocks());

  it('crea una línea con dataType correcto', () => {
    const line = new ConnectionLine(defaultOpts);
    expect(line.dataType).toBe('chat');
  });

  it('crea una línea con active correcto', () => {
    const line = new ConnectionLine(defaultOpts);
    expect(line.active).toBe(true);
  });

  it('dibuja curva bezier al construirse (moveTo)', () => {
    new ConnectionLine(defaultOpts);
    expect(mockMoveTo).toHaveBeenCalled();
  });

  it('dibuja curva bezier al construirse (bezierCurveTo)', () => {
    new ConnectionLine(defaultOpts);
    expect(mockBezierCurveTo).toHaveBeenCalled();
  });

  it('aplica stroke con color y alpha al dibujar', () => {
    new ConnectionLine(defaultOpts);
    expect(mockStroke).toHaveBeenCalledWith(
      expect.objectContaining({ color: DATA_TYPE_COLORS.chat, alpha: ACTIVE_ALPHA })
    );
  });

  it('aplica idle alpha cuando está inactivo', () => {
    new ConnectionLine({ ...defaultOpts, active: false });
    expect(mockStroke).toHaveBeenCalledWith(
      expect.objectContaining({ alpha: IDLE_ALPHA })
    );
  });

  it('agrega line y dots al container (2 hijos)', () => {
    new ConnectionLine(defaultOpts);
    expect(mockAddChild).toHaveBeenCalledTimes(2);
  });

  it('update dibuja DOT_COUNT dots cuando activo', () => {
    const line = new ConnectionLine(defaultOpts);
    mockCircle.mockClear();
    line.update();
    expect(mockCircle).toHaveBeenCalledTimes(DOT_COUNT);
  });

  it('update no dibuja dots cuando inactivo', () => {
    const line = new ConnectionLine({ ...defaultOpts, active: false });
    mockCircle.mockClear();
    line.update();
    expect(mockCircle).not.toHaveBeenCalled();
  });

  it('setActive false cambia active y limpia dots', () => {
    const line = new ConnectionLine(defaultOpts);
    line.setActive(false);
    expect(line.active).toBe(false);
  });

  it('setActive true cambia active', () => {
    const line = new ConnectionLine({ ...defaultOpts, active: false });
    line.setActive(true);
    expect(line.active).toBe(true);
  });

  it('setDataType cambia el tipo', () => {
    const line = new ConnectionLine(defaultOpts);
    line.setDataType('video');
    expect(line.dataType).toBe('video');
  });

  it('setDataType redibuja la línea con nuevo color', () => {
    const line = new ConnectionLine(defaultOpts);
    mockStroke.mockClear();
    line.setDataType('video');
    expect(mockStroke).toHaveBeenCalledWith(
      expect.objectContaining({ color: DATA_TYPE_COLORS.video })
    );
  });

  it('setEndpoints actualiza coordenadas y redibuja', () => {
    const line = new ConnectionLine(defaultOpts);
    mockMoveTo.mockClear();
    line.setEndpoints(50, 50, 300, 300);
    expect(mockMoveTo).toHaveBeenCalled();
  });

  it('destroy destruye el container con hijos', () => {
    const line = new ConnectionLine(defaultOpts);
    line.destroy();
    expect(mockDestroy).toHaveBeenCalledWith({ children: true });
  });

  describe('DATA_TYPE_COLORS', () => {
    it('tiene colores para los 6 tipos de dato', () => {
      const types: DataType[] = ['chat', 'image', 'video', 'code', 'audio', 'system'];
      types.forEach((t) => expect(DATA_TYPE_COLORS[t]).toBeDefined());
    });

    it('chat es azul (0x1e90ff)', () => expect(DATA_TYPE_COLORS.chat).toBe(0x1e90ff));
    it('image es púrpura (0x9b59b6)', () => expect(DATA_TYPE_COLORS.image).toBe(0x9b59b6));
    it('video es verde (0x2ecc71)', () => expect(DATA_TYPE_COLORS.video).toBe(0x2ecc71));
    it('code es naranja (0xe67e22)', () => expect(DATA_TYPE_COLORS.code).toBe(0xe67e22));
  });

  describe('constantes', () => {
    it('ACTIVE_ALPHA es 1.0', () => expect(ACTIVE_ALPHA).toBe(1.0));
    it('IDLE_ALPHA es 0.3', () => expect(IDLE_ALPHA).toBe(0.3));
    it('DOT_COUNT es 3', () => expect(DOT_COUNT).toBe(3));
  });
});
