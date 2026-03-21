/**
 * YeyoOS — ConnectionLine (Líneas de Conexión Neural)
 * Micro-fase 3.4 — Capa 3: Cuerpo
 *
 * Curvas bezier animadas entre nodos satélite y el nodo central.
 * Los puntos viajan por la línea simulando flujo de datos.
 */

import { Graphics, Container } from 'pixi.js';

export type DataType = 'chat' | 'image' | 'video' | 'code' | 'audio' | 'system';

export interface ConnectionLineOptions {
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
  dataType: DataType;
  active: boolean;
}

export const DATA_TYPE_COLORS: Record<DataType, number> = {
  chat: 0x1e90ff,
  image: 0x9b59b6,
  video: 0x2ecc71,
  code: 0xe67e22,
  audio: 0xe91e63,
  system: 0x95a5a6,
};

export const ACTIVE_ALPHA = 1.0;
export const IDLE_ALPHA = 0.3;
export const LINE_WIDTH = 2;
export const DOT_RADIUS = 3;
export const DOT_COUNT = 3;
export const DOT_SPEED = 0.008;

export class ConnectionLine {
  public container: Container;
  public dataType: DataType;
  public active: boolean;

  private line: Graphics;
  private dots: Graphics;
  private fromX: number;
  private fromY: number;
  private toX: number;
  private toY: number;
  private dotProgress: number[];

  constructor(options: ConnectionLineOptions) {
    this.fromX = options.fromX;
    this.fromY = options.fromY;
    this.toX = options.toX;
    this.toY = options.toY;
    this.dataType = options.dataType;
    this.active = options.active;

    this.container = new Container();

    this.line = new Graphics();
    this.container.addChild(this.line);

    this.dots = new Graphics();
    this.container.addChild(this.dots);

    this.dotProgress = Array.from({ length: DOT_COUNT }, (_, i) => i / DOT_COUNT);

    this.draw();
  }

  private getBezierControlPoints() {
    const dx = this.toX - this.fromX;
    const dy = this.toY - this.fromY;
    const dist = Math.sqrt(dx * dx + dy * dy);
    const curvature = dist * 0.3;

    return {
      cp1x: this.fromX + dx * 0.25 + (dy > 0 ? curvature : -curvature) * 0.3,
      cp1y: this.fromY + dy * 0.25,
      cp2x: this.toX - dx * 0.25,
      cp2y: this.toY - dy * 0.25 + (dx > 0 ? -curvature : curvature) * 0.3,
    };
  }

  private getBezierPoint(t: number): { x: number; y: number } {
    const cp = this.getBezierControlPoints();
    const u = 1 - t;
    return {
      x:
        u * u * u * this.fromX +
        3 * u * u * t * cp.cp1x +
        3 * u * t * t * cp.cp2x +
        t * t * t * this.toX,
      y:
        u * u * u * this.fromY +
        3 * u * u * t * cp.cp1y +
        3 * u * t * t * cp.cp2y +
        t * t * t * this.toY,
    };
  }

  private draw(): void {
    const color = DATA_TYPE_COLORS[this.dataType];
    const alpha = this.active ? ACTIVE_ALPHA : IDLE_ALPHA;
    const cp = this.getBezierControlPoints();

    this.line.clear();
    this.line.moveTo(this.fromX, this.fromY);
    this.line.bezierCurveTo(cp.cp1x, cp.cp1y, cp.cp2x, cp.cp2y, this.toX, this.toY);
    this.line.stroke({ color, width: LINE_WIDTH, alpha });
  }

  public update(): void {
    if (!this.active) return;

    const color = DATA_TYPE_COLORS[this.dataType];

    this.dots.clear();
    for (let i = 0; i < this.dotProgress.length; i++) {
      this.dotProgress[i] = (this.dotProgress[i] + DOT_SPEED) % 1;
      const point = this.getBezierPoint(this.dotProgress[i]);
      this.dots.circle(point.x, point.y, DOT_RADIUS);
      this.dots.fill({ color, alpha: 0.9 });
    }
  }

  public setEndpoints(fromX: number, fromY: number, toX: number, toY: number): void {
    this.fromX = fromX;
    this.fromY = fromY;
    this.toX = toX;
    this.toY = toY;
    this.draw();
  }

  public setActive(active: boolean): void {
    this.active = active;
    this.draw();
    if (!active) {
      this.dots.clear();
    }
  }

  public setDataType(dataType: DataType): void {
    this.dataType = dataType;
    this.draw();
  }

  public destroy(): void {
    this.container.destroy({ children: true });
  }
}
