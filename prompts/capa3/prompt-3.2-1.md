## ═══════════════════════════════════════
## MICRO-FASE 3.2 — Satellite Node Base
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 3.2-1 [VSCODE] — Componente base para nodos satélite draggable

```
Estamos construyendo YeyoOS, un OS AI-nativo con interfaz Neural Hub. Esta es la micro-fase 3.2 de Capa 3 (Cuerpo): crear el componente base para nodos satélite con drag & drop.

CONTEXTO:
- Micro-fase 3.0 completada: HubCanvas con PixiJS 8
- Micro-fase 3.1 completada: CentralNode con shader GLSL
- Los nodos satélite orbitan alrededor del nodo central
- Cada nodo: rectángulo redondeado + icono + label
- Draggable con pointer events de PixiJS 8
- Snap-back physics: spring animation al soltar cerca del centro
- Línea de conexión al nodo central (bezier curve)
- Estados: active (bright), idle (dim), loading (pulsing), error (red border)

Abre el directorio ~/yeyo-os/frontend en VS Code.

CREAR:

1. Crear estructura de directorios:
   mkdir -p src/components/nodes
   mkdir -p __tests__/components/nodes

2. Crear archivo src/components/nodes/SatelliteNode.ts:

   Ruta: ~/yeyo-os/frontend/src/components/nodes/SatelliteNode.ts
   Contenido:

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

   const STATE_STYLES: Record<SatelliteState, { bgColor: number; bgAlpha: number; borderColor: number; borderWidth: number; labelAlpha: number }> = {
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

   const SNAP_BACK_THRESHOLD = 80;
   const SPRING_STIFFNESS = 0.15;
   const SPRING_DAMPING = 0.7;
   const NODE_WIDTH = 140;
   const NODE_HEIGHT = 60;
   const CORNER_RADIUS = 12;

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

       const iconStyle = new TextStyle({
         fontSize: 20,
         fill: 0xffffff,
       });
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

       if (Math.abs(dx) < 0.5 && Math.abs(dy) < 0.5 && Math.abs(this.velocityX) < 0.1 && Math.abs(this.velocityY) < 0.1) {
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

   export { STATE_STYLES, SNAP_BACK_THRESHOLD, NODE_WIDTH, NODE_HEIGHT };

3. Crear archivo __tests__/components/nodes/SatelliteNode.test.ts:

   Ruta: ~/yeyo-os/frontend/__tests__/components/nodes/SatelliteNode.test.ts
   Contenido:

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

   // Mock PixiJS
   const mockOn = jest.fn();
   const mockRemoveAllListeners = jest.fn();
   const mockDestroyContainer = jest.fn();
   const mockAddChild = jest.fn();
   const mockClear = jest.fn().mockReturnThis();
   const mockRoundRect = jest.fn().mockReturnThis();
   const mockFill = jest.fn().mockReturnThis();
   const mockStroke = jest.fn().mockReturnThis();
   const mockCircle = jest.fn().mockReturnThis();

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
       circle: mockCircle,
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
     beforeEach(() => {
       jest.clearAllMocks();
     });

     describe('constructor', () => {
       it('crea un nodo con id y label', () => {
         const node = createNode();
         expect(node.id).toBe('test-node');
         expect(node.state).toBe('idle');
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

       it('configura eventMode como static para interacciones', () => {
         const node = createNode();
         expect(node.container.eventMode).toBe('static');
       });

       it('configura cursor como pointer', () => {
         const node = createNode();
         expect(node.container.cursor).toBe('pointer');
       });

       it('agrega hijos al container (bg, icon, label)', () => {
         createNode();
         expect(mockAddChild).toHaveBeenCalledTimes(3);
       });

       it('registra eventos de pointer', () => {
         createNode();
         expect(mockOn).toHaveBeenCalledWith('pointerdown', expect.any(Function));
         expect(mockOn).toHaveBeenCalledWith('globalpointermove', expect.any(Function));
         expect(mockOn).toHaveBeenCalledWith('pointerup', expect.any(Function));
         expect(mockOn).toHaveBeenCalledWith('pointerupoutside', expect.any(Function));
         expect(mockOn).toHaveBeenCalledWith('pointertap', expect.any(Function));
       });

       it('dibuja el fondo con el estilo del estado idle', () => {
         createNode();
         expect(mockRoundRect).toHaveBeenCalled();
         expect(mockFill).toHaveBeenCalledWith(
           expect.objectContaining({
             color: STATE_STYLES.idle.bgColor,
             alpha: STATE_STYLES.idle.bgAlpha,
           })
         );
       });
     });

     describe('setState', () => {
       it('cambia el estado del nodo', () => {
         const node = createNode();
         node.setState('active');
         expect(node.state).toBe('active');
       });

       it('redibuja el fondo al cambiar estado', () => {
         const node = createNode();
         mockClear.mockClear();
         mockRoundRect.mockClear();
         node.setState('error');
         expect(mockClear).toHaveBeenCalled();
         expect(mockStroke).toHaveBeenCalledWith(
           expect.objectContaining({
             color: STATE_STYLES.error.borderColor,
           })
         );
       });
     });

     describe('getPosition', () => {
       it('retorna la posición actual del container', () => {
         const node = createNode({ x: 100, y: 200 });
         const pos = node.getPosition();
         expect(pos.x).toBe(100);
         expect(pos.y).toBe(200);
       });
     });

     describe('destroy', () => {
       it('remueve listeners y destruye el container', () => {
         const node = createNode();
         node.destroy();
         expect(mockRemoveAllListeners).toHaveBeenCalled();
         expect(mockDestroyContainer).toHaveBeenCalledWith({ children: true });
       });
     });

     describe('STATE_STYLES', () => {
       it('tiene estilos para los 4 estados', () => {
         const states: SatelliteState[] = ['active', 'idle', 'loading', 'error'];
         states.forEach((s) => {
           expect(STATE_STYLES[s]).toBeDefined();
           expect(STATE_STYLES[s].bgColor).toBeDefined();
           expect(STATE_STYLES[s].borderColor).toBeDefined();
         });
       });

       it('error tiene borde rojo grueso', () => {
         expect(STATE_STYLES.error.borderColor).toBe(0xff4444);
         expect(STATE_STYLES.error.borderWidth).toBe(3);
       });
     });

     describe('constantes', () => {
       it('exporta dimensiones del nodo', () => {
         expect(NODE_WIDTH).toBe(140);
         expect(NODE_HEIGHT).toBe(60);
       });

       it('exporta threshold de snap-back', () => {
         expect(SNAP_BACK_THRESHOLD).toBe(80);
       });
     });
   });

4. Ejecutar tests:
   cd ~/yeyo-os/frontend
   npx jest __tests__/components/nodes/SatelliteNode.test.ts --no-cache

VERIFICAR:
- [ ] Archivo src/components/nodes/SatelliteNode.ts existe
- [ ] SatelliteNode tiene rectángulo redondeado + icono + label
- [ ] Drag & drop funciona con pointer events de PixiJS 8
- [ ] Snap-back physics con spring animation
- [ ] 4 estados visuales: active, idle, loading, error
- [ ] Double-click emite evento
- [ ] destroy() limpia listeners y children
- [ ] TODOS los tests pasan

SI FALLA:
- PixiJS mock: verificar que la estructura refleja PixiJS 8 (Container, Graphics, Text)
- FederatedPointerEvent: es el tipo correcto en PixiJS 8 (no InteractionEvent de v7)
- getLocalPosition: verificar que parent está disponible

NO HACER:
- No crear nodos específicos (ChatNode, ImageNode) aún — eso viene después
- No implementar la línea de conexión aquí (eso es micro-fase 3.4)
- No conectar al layout engine aún (micro-fase 3.3)

GATE: SatelliteNode es draggable, tiene 4 estados visuales, snap-back physics, double-click event, todos los tests pasan.
```
