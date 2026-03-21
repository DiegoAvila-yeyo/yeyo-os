/**
 * YeyoOS — SatelliteNode (Nodo Satélite Base)
 * Micro-fase 3.2 — Capa 3: Cuerpo
 *
 * Componente base para todos los nodos satélite del Neural Hub.
 * Draggable con snap-back physics y conexión al nodo central.
 */

import { Container, Graphics, Text, TextStyle, FederatedPointerEvent } from 'pixi.js';

export type SatelliteState = 'active' | 'idle' | 'loading' | 'error';

export interface SatelliteNodeOptions {
  id: string;
  label: string;
  icon: string;
  x: number;
  y: number;
  width?: number;
  height?: number;
  state?: SatelliteState;
  onDragEnd?: (id: string, x: number, y: number) => void;
  onDoubleClick?: (id: string) => void;
}

export const STATE_STYLES: Record<
  SatelliteState,
  { bgColor: number; bgAlpha: number; borderColor: number; borderWidth: number; labelAlpha: number }
> = {
  active: {
    bgColor: 0x1a1a2e,
    bgAlpha: 0.95,
    borderColor: 0x1e90ff,
    borderWidth: 2,
    labelAlpha: 1.0,
  },
  idle: {
    bgColor: 0x12121a,
    bgAlpha: 0.7,
    borderColor: 0x333355,
    borderWidth: 1,
    labelAlpha: 0.6,
  },
  loading: {
    bgColor: 0x1a1a2e,
    bgAlpha: 0.85,
    borderColor: 0xffa500,
    borderWidth: 2,
    labelAlpha: 0.8,
  },
  error: {
    bgColor: 0x1a1a2e,
    bgAlpha: 0.9,
    borderColor: 0xff4444,
    borderWidth: 3,
    labelAlpha: 1.0,
  },
};

export const SNAP_BACK_THRESHOLD = 80;
export const SPRING_STIFFNESS = 0.15;
export const SPRING_DAMPING = 0.7;
export const NODE_WIDTH = 140;
export const NODE_HEIGHT = 60;
export const CORNER_RADIUS = 12;

export class SatelliteNode {
  public container: Container;
  public id: string;
  public state: SatelliteState;
  public originalX: number;
  public originalY: number;

  private bg: Graphics;
  private label: Text;
  private iconText: Text;
  private isDragging: boolean;
  private dragOffset: { x: number; y: number };
  private nodeWidth: number;
  private nodeHeight: number;
  private onDragEnd?: (id: string, x: number, y: number) => void;
  private onDoubleClick?: (id: string) => void;
  private velocityX: number;
  private velocityY: number;
  private isSnappingBack: boolean;
  private snapTargetX: number;
  private snapTargetY: number;

  constructor(options: SatelliteNodeOptions) {
    this.id = options.id;
    this.state = options.state ?? 'idle';
    this.originalX = options.x;
    this.originalY = options.y;
    this.nodeWidth = options.width ?? NODE_WIDTH;
    this.nodeHeight = options.height ?? NODE_HEIGHT;
    this.onDragEnd = options.onDragEnd;
    this.onDoubleClick = options.onDoubleClick;
    this.isDragging = false;
    this.dragOffset = { x: 0, y: 0 };
    this.velocityX = 0;
    this.velocityY = 0;
    this.isSnappingBack = false;
    this.snapTargetX = options.x;
    this.snapTargetY = options.y;

    this.container = new Container();
    this.container.x = options.x;
    this.container.y = options.y;
    this.container.eventMode = 'static';
    this.container.cursor = 'pointer';

    this.bg = new Graphics();
    this.container.addChild(this.bg);

    const iconStyle = new TextStyle({ fontSize: 20, fill: 0xffffff });
    this.iconText = new Text({ text: options.icon, style: iconStyle });
    this.iconText.anchor.set(0.5);
    this.iconText.x = -this.nodeWidth / 2 + 24;
    this.iconText.y = 0;
    this.container.addChild(this.iconText);

    const labelStyle = new TextStyle({
      fontSize: 13,
      fill: 0xccccdd,
      fontFamily: 'Inter, sans-serif',
    });
    this.label = new Text({ text: options.label, style: labelStyle });
    this.label.anchor.set(0, 0.5);
    this.label.x = -this.nodeWidth / 2 + 44;
    this.label.y = 0;
    this.container.addChild(this.label);

    this.drawBackground();
    this.setupDragEvents();
  }

  private drawBackground(): void {
    const style = STATE_STYLES[this.state];
    this.bg.clear();
    this.bg.roundRect(
      -this.nodeWidth / 2,
      -this.nodeHeight / 2,
      this.nodeWidth,
      this.nodeHeight,
      CORNER_RADIUS
    );
    this.bg.fill({ color: style.bgColor, alpha: style.bgAlpha });
    this.bg.stroke({ color: style.borderColor, width: style.borderWidth });
    this.label.alpha = style.labelAlpha;
  }

  private setupDragEvents(): void {
    this.container.on('pointerdown', this.onPointerDown.bind(this));
    this.container.on('globalpointermove', this.onPointerMove.bind(this));
    this.container.on('pointerup', this.onPointerUp.bind(this));
    this.container.on('pointerupoutside', this.onPointerUp.bind(this));

    let lastClickTime = 0;
    this.container.on('pointertap', () => {
      const now = Date.now();
      if (now - lastClickTime < 300) {
        this.onDoubleClick?.(this.id);
      }
      lastClickTime = now;
    });
  }

  private onPointerDown(event: FederatedPointerEvent): void {
    this.isDragging = true;
    this.isSnappingBack = false;
    const pos = event.getLocalPosition(this.container.parent!);
    this.dragOffset.x = pos.x - this.container.x;
    this.dragOffset.y = pos.y - this.container.y;
  }

  private onPointerMove(event: FederatedPointerEvent): void {
    if (!this.isDragging) return;
    const pos = event.getLocalPosition(this.container.parent!);
    this.container.x = pos.x - this.dragOffset.x;
    this.container.y = pos.y - this.dragOffset.y;
  }

  private onPointerUp(): void {
    if (!this.isDragging) return;
    this.isDragging = false;

    const dx = this.container.x - this.originalX;
    const dy = this.container.y - this.originalY;
    const dist = Math.sqrt(dx * dx + dy * dy);

    if (dist < SNAP_BACK_THRESHOLD) {
      this.startSnapBack(this.originalX, this.originalY);
    } else {
      this.originalX = this.container.x;
      this.originalY = this.container.y;
      this.onDragEnd?.(this.id, this.container.x, this.container.y);
    }
  }

  private startSnapBack(targetX: number, targetY: number): void {
    this.isSnappingBack = true;
    this.snapTargetX = targetX;
    this.snapTargetY = targetY;
    this.velocityX = 0;
    this.velocityY = 0;
  }

  public update(): void {
    if (!this.isSnappingBack) return;

    const dx = this.snapTargetX - this.container.x;
    const dy = this.snapTargetY - this.container.y;

    this.velocityX = (this.velocityX + dx * SPRING_STIFFNESS) * SPRING_DAMPING;
    this.velocityY = (this.velocityY + dy * SPRING_STIFFNESS) * SPRING_DAMPING;

    this.container.x += this.velocityX;
    this.container.y += this.velocityY;

    if (
      Math.abs(dx) < 0.5 &&
      Math.abs(dy) < 0.5 &&
      Math.abs(this.velocityX) < 0.1 &&
      Math.abs(this.velocityY) < 0.1
    ) {
      this.container.x = this.snapTargetX;
      this.container.y = this.snapTargetY;
      this.isSnappingBack = false;
    }
  }

  public setState(newState: SatelliteState): void {
    this.state = newState;
    this.drawBackground();
  }

  public getPosition(): { x: number; y: number } {
    return { x: this.container.x, y: this.container.y };
  }

  public destroy(): void {
    this.container.removeAllListeners();
    this.container.destroy({ children: true });
  }
}
