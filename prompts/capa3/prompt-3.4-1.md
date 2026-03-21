## ═══════════════════════════════════════
## MICRO-FASE 3.4 — Connection Lines
## Tipo: VSCODE | Prompts: 1 | Complejidad: Simple
## ═══════════════════════════════════════

### PROMPT 3.4-1 [VSCODE] — Líneas de conexión con curvas bezier y animación de datos

```
Estamos construyendo YeyoOS, un OS AI-nativo con interfaz Neural Hub. Esta es la micro-fase 3.4 de Capa 3 (Cuerpo): crear las líneas de conexión visual entre nodos satélite y el nodo central.

CONTEXTO:
- Micro-fases 3.0-3.3 completadas: Canvas, CentralNode, SatelliteNode, Layout Engine
- Las líneas van de cada nodo satélite al nodo central
- Curvas bezier para un aspecto orgánico
- Animación de flujo de datos: puntos que viajan por la línea
- Color según tipo de dato: chat=azul, image=púrpura, video=verde
- Opacidad según actividad: active=1.0, idle=0.3

Abre el directorio ~/yeyo-os/frontend en VS Code.

CREAR:

1. Crear archivo src/components/hub/ConnectionLine.ts:

   Ruta: ~/yeyo-os/frontend/src/components/hub/ConnectionLine.ts
   Contenido:

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

   const DATA_TYPE_COLORS: Record<DataType, number> = {
     chat: 0x1e90ff,
     image: 0x9b59b6,
     video: 0x2ecc71,
     code: 0xe67e22,
     audio: 0xe91e63,
     system: 0x95a5a6,
   };

   const ACTIVE_ALPHA = 1.0;
   const IDLE_ALPHA = 0.3;
   const LINE_WIDTH = 2;
   const DOT_RADIUS = 3;
   const DOT_COUNT = 3;
   const DOT_SPEED = 0.008;

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

       this.dotProgress = Array.from(
         { length: DOT_COUNT },
         (_, i) => i / DOT_COUNT
       );

       this.draw();
     }

     private getBezierControlPoints(): { cp1x: number; cp1y: number; cp2x: number; cp2y: number } {
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
         x: u * u * u * this.fromX + 3 * u * u * t * cp.cp1x + 3 * u * t * t * cp.cp2x + t * t * t * this.toX,
         y: u * u * u * this.fromY + 3 * u * u * t * cp.cp1y + 3 * u * t * t * cp.cp2y + t * t * t * this.toY,
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

   export { DATA_TYPE_COLORS, ACTIVE_ALPHA, IDLE_ALPHA, DOT_COUNT, DOT_SPEED };

2. Crear archivo __tests__/components/hub/ConnectionLine.test.ts:

   Ruta: ~/yeyo-os/frontend/__tests__/components/hub/ConnectionLine.test.ts
   Contenido:

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

   // Mock PixiJS
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

   describe('ConnectionLine', () => {
     beforeEach(() => {
       jest.clearAllMocks();
     });

     it('crea una línea de conexión', () => {
       const line = new ConnectionLine({
         fromX: 0,
         fromY: 0,
         toX: 100,
         toY: 100,
         dataType: 'chat',
         active: true,
       });
       expect(line.dataType).toBe('chat');
       expect(line.active).toBe(true);
     });

     it('dibuja una curva bezier al construirse', () => {
       new ConnectionLine({
         fromX: 0,
         fromY: 0,
         toX: 200,
         toY: 200,
         dataType: 'image',
         active: false,
       });
       expect(mockMoveTo).toHaveBeenCalled();
       expect(mockBezierCurveTo).toHaveBeenCalled();
       expect(mockStroke).toHaveBeenCalled();
     });

     it('agrega line y dots al container', () => {
       new ConnectionLine({
         fromX: 0,
         fromY: 0,
         toX: 100,
         toY: 100,
         dataType: 'chat',
         active: true,
       });
       expect(mockAddChild).toHaveBeenCalledTimes(2);
     });

     it('update dibuja dots cuando está activo', () => {
       const line = new ConnectionLine({
         fromX: 0,
         fromY: 0,
         toX: 200,
         toY: 200,
         dataType: 'chat',
         active: true,
       });
       mockCircle.mockClear();
       line.update();
       expect(mockCircle).toHaveBeenCalledTimes(DOT_COUNT);
     });

     it('update no dibuja dots cuando está inactivo', () => {
       const line = new ConnectionLine({
         fromX: 0,
         fromY: 0,
         toX: 200,
         toY: 200,
         dataType: 'chat',
         active: false,
       });
       mockCircle.mockClear();
       line.update();
       expect(mockCircle).not.toHaveBeenCalled();
     });

     it('setActive cambia la opacidad', () => {
       const line = new ConnectionLine({
         fromX: 0,
         fromY: 0,
         toX: 200,
         toY: 200,
         dataType: 'chat',
         active: true,
       });
       line.setActive(false);
       expect(line.active).toBe(false);
       expect(mockClear).toHaveBeenCalled();
     });

     it('setDataType cambia el tipo de dato', () => {
       const line = new ConnectionLine({
         fromX: 0,
         fromY: 0,
         toX: 200,
         toY: 200,
         dataType: 'chat',
         active: true,
       });
       line.setDataType('video');
       expect(line.dataType).toBe('video');
     });

     it('setEndpoints actualiza las coordenadas y redibuja', () => {
       const line = new ConnectionLine({
         fromX: 0,
         fromY: 0,
         toX: 100,
         toY: 100,
         dataType: 'chat',
         active: true,
       });
       mockMoveTo.mockClear();
       line.setEndpoints(50, 50, 200, 200);
       expect(mockMoveTo).toHaveBeenCalled();
     });

     it('destroy destruye el container con hijos', () => {
       const line = new ConnectionLine({
         fromX: 0,
         fromY: 0,
         toX: 100,
         toY: 100,
         dataType: 'chat',
         active: true,
       });
       line.destroy();
       expect(mockDestroy).toHaveBeenCalledWith({ children: true });
     });

     describe('DATA_TYPE_COLORS', () => {
       it('tiene colores para todos los tipos de dato', () => {
         const types: DataType[] = ['chat', 'image', 'video', 'code', 'audio', 'system'];
         types.forEach((t) => {
           expect(DATA_TYPE_COLORS[t]).toBeDefined();
         });
       });

       it('chat es azul', () => {
         expect(DATA_TYPE_COLORS.chat).toBe(0x1e90ff);
       });

       it('image es púrpura', () => {
         expect(DATA_TYPE_COLORS.image).toBe(0x9b59b6);
       });

       it('video es verde', () => {
         expect(DATA_TYPE_COLORS.video).toBe(0x2ecc71);
       });
     });

     describe('constantes', () => {
       it('active alpha es 1.0', () => {
         expect(ACTIVE_ALPHA).toBe(1.0);
       });

       it('idle alpha es 0.3', () => {
         expect(IDLE_ALPHA).toBe(0.3);
       });
     });
   });

3. Ejecutar tests:
   cd ~/yeyo-os/frontend
   npx jest __tests__/components/hub/ConnectionLine.test.ts --no-cache

VERIFICAR:
- [ ] Archivo src/components/hub/ConnectionLine.ts existe
- [ ] Curva bezier se dibuja entre dos puntos
- [ ] Animación de dots cuando está activo
- [ ] Color cambia según dataType (chat=azul, image=púrpura, video=verde)
- [ ] Opacidad: active=1.0, idle=0.3
- [ ] setEndpoints redibuja la línea
- [ ] destroy limpia el container
- [ ] TODOS los tests pasan

SI FALLA:
- PixiJS Graphics API v8: bezierCurveTo existe en Graphics de PixiJS 8
- Mock order: verificar que clear/moveTo/bezierCurveTo se llaman en orden

NO HACER:
- No crear líneas entre nodos satélite (solo satélite → central)
- No agregar interactividad a las líneas
- No optimizar el rendering de dots prematuramente

GATE: ConnectionLine dibuja bezier curves, dots animados viajan por la línea, colores correctos por tipo, todos los tests pasan.
```
