## ═══════════════════════════════════════
## MICRO-FASE 3.3 — Node Layout Engine
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 3.3-1 [VSCODE] — Motor de layout orbital para nodos satélite

```
Estamos construyendo YeyoOS, un OS AI-nativo con interfaz Neural Hub. Esta es la micro-fase 3.3 de Capa 3 (Cuerpo): crear el motor de layout orbital que posiciona nodos automáticamente.

CONTEXTO:
- Micro-fases 3.0-3.2 completadas: HubCanvas, CentralNode, SatelliteNode
- Los nodos satélite se posicionan en círculos concéntricos alrededor del nodo central
- Al agregar/quitar nodos, se re-organizan automáticamente con animación suave
- Detección de colisiones para que los nodos no se superpongan
- Spring physics para transiciones (~300ms)
- Las posiciones se guardan/restauran desde el Zustand store

Abre el directorio ~/yeyo-os/frontend en VS Code.

CREAR:

1. Crear estructura de directorios:
   mkdir -p src/lib/layout
   mkdir -p __tests__/lib/layout

2. Crear archivo src/lib/layout/orbital.ts:

   Ruta: ~/yeyo-os/frontend/src/lib/layout/orbital.ts
   Contenido:

   /**
    * YeyoOS — Orbital Layout Engine
    * Micro-fase 3.3 — Capa 3: Cuerpo
    *
    * Posiciona nodos satélite en círculos concéntricos alrededor
    * del nodo central. Detección de colisiones y animación spring.
    */

   export interface LayoutNode {
     id: string;
     x: number;
     y: number;
     width: number;
     height: number;
   }

   export interface LayoutResult {
     id: string;
     targetX: number;
     targetY: number;
     ring: number;
   }

   export interface OrbitalConfig {
     centerX: number;
     centerY: number;
     firstRingRadius: number;
     ringSpacing: number;
     maxNodesPerRing: number;
     nodeMinSpacing: number;
   }

   const DEFAULT_CONFIG: OrbitalConfig = {
     centerX: 960,
     centerY: 540,
     firstRingRadius: 180,
     ringSpacing: 120,
     maxNodesPerRing: 8,
     nodeMinSpacing: 20,
   };

   export function calculateOrbitalPositions(
     nodeIds: string[],
     config: Partial<OrbitalConfig> = {}
   ): LayoutResult[] {
     const cfg = { ...DEFAULT_CONFIG, ...config };
     const results: LayoutResult[] = [];

     if (nodeIds.length === 0) return results;

     let nodeIndex = 0;
     let ring = 0;

     while (nodeIndex < nodeIds.length) {
       const radius = cfg.firstRingRadius + ring * cfg.ringSpacing;
       const circumference = 2 * Math.PI * radius;
       const maxForRing = Math.min(
         cfg.maxNodesPerRing + ring * 2,
         Math.floor(circumference / (cfg.nodeMinSpacing + 140))
       );
       const nodesInRing = Math.min(maxForRing, nodeIds.length - nodeIndex);
       const angleStep = (2 * Math.PI) / nodesInRing;
       const startAngle = -Math.PI / 2;

       for (let i = 0; i < nodesInRing; i++) {
         const angle = startAngle + i * angleStep;
         results.push({
           id: nodeIds[nodeIndex],
           targetX: cfg.centerX + Math.cos(angle) * radius,
           targetY: cfg.centerY + Math.sin(angle) * radius,
           ring,
         });
         nodeIndex++;
       }
       ring++;
     }

     return results;
   }

   export function detectCollisions(
     nodes: LayoutNode[],
     minSpacing: number = 20
   ): Array<[string, string]> {
     const collisions: Array<[string, string]> = [];

     for (let i = 0; i < nodes.length; i++) {
       for (let j = i + 1; j < nodes.length; j++) {
         const a = nodes[i];
         const b = nodes[j];

         const overlapX =
           Math.abs(a.x - b.x) < (a.width + b.width) / 2 + minSpacing;
         const overlapY =
           Math.abs(a.y - b.y) < (a.height + b.height) / 2 + minSpacing;

         if (overlapX && overlapY) {
           collisions.push([a.id, b.id]);
         }
       }
     }

     return collisions;
   }

   export function resolveCollisions(nodes: LayoutNode[], minSpacing: number = 20): LayoutNode[] {
     const resolved = nodes.map((n) => ({ ...n }));
     const maxIterations = 50;

     for (let iter = 0; iter < maxIterations; iter++) {
       let hasCollision = false;

       for (let i = 0; i < resolved.length; i++) {
         for (let j = i + 1; j < resolved.length; j++) {
           const a = resolved[i];
           const b = resolved[j];

           const dx = b.x - a.x;
           const dy = b.y - a.y;
           const minDistX = (a.width + b.width) / 2 + minSpacing;
           const minDistY = (a.height + b.height) / 2 + minSpacing;

           if (Math.abs(dx) < minDistX && Math.abs(dy) < minDistY) {
             hasCollision = true;
             const pushX = (minDistX - Math.abs(dx)) / 2 * Math.sign(dx || 1);
             const pushY = (minDistY - Math.abs(dy)) / 2 * Math.sign(dy || 1);

             a.x -= pushX * 0.5;
             a.y -= pushY * 0.5;
             b.x += pushX * 0.5;
             b.y += pushY * 0.5;
           }
         }
       }

       if (!hasCollision) break;
     }

     return resolved;
   }

   export interface SpringState {
     x: number;
     y: number;
     vx: number;
     vy: number;
     targetX: number;
     targetY: number;
     done: boolean;
   }

   const SPRING_STIFFNESS = 0.12;
   const SPRING_DAMPING = 0.75;
   const SETTLE_THRESHOLD = 0.5;

   export function createSpringState(
     currentX: number,
     currentY: number,
     targetX: number,
     targetY: number
   ): SpringState {
     return {
       x: currentX,
       y: currentY,
       vx: 0,
       vy: 0,
       targetX,
       targetY,
       done: false,
     };
   }

   export function updateSpring(state: SpringState): SpringState {
     if (state.done) return state;

     const dx = state.targetX - state.x;
     const dy = state.targetY - state.y;

     const ax = dx * SPRING_STIFFNESS;
     const ay = dy * SPRING_STIFFNESS;

     const vx = (state.vx + ax) * SPRING_DAMPING;
     const vy = (state.vy + ay) * SPRING_DAMPING;

     const x = state.x + vx;
     const y = state.y + vy;

     const done =
       Math.abs(dx) < SETTLE_THRESHOLD &&
       Math.abs(dy) < SETTLE_THRESHOLD &&
       Math.abs(vx) < SETTLE_THRESHOLD &&
       Math.abs(vy) < SETTLE_THRESHOLD;

     return {
       x: done ? state.targetX : x,
       y: done ? state.targetY : y,
       vx: done ? 0 : vx,
       vy: done ? 0 : vy,
       targetX: state.targetX,
       targetY: state.targetY,
       done,
     };
   }

   export { DEFAULT_CONFIG, SPRING_STIFFNESS, SPRING_DAMPING };

3. Crear archivo __tests__/lib/layout/orbital.test.ts:

   Ruta: ~/yeyo-os/frontend/__tests__/lib/layout/orbital.test.ts
   Contenido:

   /**
    * Tests para Orbital Layout Engine — Micro-fase 3.3
    */

   import {
     calculateOrbitalPositions,
     detectCollisions,
     resolveCollisions,
     createSpringState,
     updateSpring,
     DEFAULT_CONFIG,
   } from '@/lib/layout/orbital';
   import type { LayoutNode, SpringState } from '@/lib/layout/orbital';

   describe('Orbital Layout Engine', () => {
     describe('calculateOrbitalPositions', () => {
       it('retorna array vacío para 0 nodos', () => {
         const result = calculateOrbitalPositions([]);
         expect(result).toEqual([]);
       });

       it('posiciona 1 nodo en el primer anillo', () => {
         const result = calculateOrbitalPositions(['node-1']);
         expect(result).toHaveLength(1);
         expect(result[0].id).toBe('node-1');
         expect(result[0].ring).toBe(0);
       });

       it('posiciona nodos en el radio correcto del primer anillo', () => {
         const result = calculateOrbitalPositions(['node-1'], {
           centerX: 500,
           centerY: 500,
           firstRingRadius: 200,
         });
         const dx = result[0].targetX - 500;
         const dy = result[0].targetY - 500;
         const dist = Math.sqrt(dx * dx + dy * dy);
         expect(dist).toBeCloseTo(200, 0);
       });

       it('distribuye múltiples nodos uniformemente', () => {
         const result = calculateOrbitalPositions(
           ['a', 'b', 'c', 'd'],
           { centerX: 0, centerY: 0, firstRingRadius: 100 }
         );
         expect(result).toHaveLength(4);
         result.forEach((r) => {
           const dist = Math.sqrt(r.targetX ** 2 + r.targetY ** 2);
           expect(dist).toBeCloseTo(100, 0);
         });
       });

       it('usa segundo anillo cuando el primero está lleno', () => {
         const ids = Array.from({ length: 20 }, (_, i) => `node-${i}`);
         const result = calculateOrbitalPositions(ids);
         const rings = new Set(result.map((r) => r.ring));
         expect(rings.size).toBeGreaterThan(1);
       });

       it('los nodos no se superponen en posición', () => {
         const ids = Array.from({ length: 6 }, (_, i) => `node-${i}`);
         const result = calculateOrbitalPositions(ids);
         for (let i = 0; i < result.length; i++) {
           for (let j = i + 1; j < result.length; j++) {
             const dx = result[i].targetX - result[j].targetX;
             const dy = result[i].targetY - result[j].targetY;
             const dist = Math.sqrt(dx * dx + dy * dy);
             expect(dist).toBeGreaterThan(50);
           }
         }
       });
     });

     describe('detectCollisions', () => {
       it('no detecta colisiones cuando los nodos están separados', () => {
         const nodes: LayoutNode[] = [
           { id: 'a', x: 0, y: 0, width: 100, height: 50 },
           { id: 'b', x: 300, y: 300, width: 100, height: 50 },
         ];
         expect(detectCollisions(nodes)).toEqual([]);
       });

       it('detecta colisiones cuando los nodos se superponen', () => {
         const nodes: LayoutNode[] = [
           { id: 'a', x: 0, y: 0, width: 100, height: 50 },
           { id: 'b', x: 50, y: 20, width: 100, height: 50 },
         ];
         const collisions = detectCollisions(nodes);
         expect(collisions).toHaveLength(1);
         expect(collisions[0]).toEqual(['a', 'b']);
       });

       it('retorna vacío para array vacío', () => {
         expect(detectCollisions([])).toEqual([]);
       });
     });

     describe('resolveCollisions', () => {
       it('separa nodos que colisionan', () => {
         const nodes: LayoutNode[] = [
           { id: 'a', x: 0, y: 0, width: 100, height: 50 },
           { id: 'b', x: 10, y: 5, width: 100, height: 50 },
         ];
         const resolved = resolveCollisions(nodes);
         const collisions = detectCollisions(resolved);
         expect(collisions).toHaveLength(0);
       });

       it('no modifica nodos que ya están separados', () => {
         const nodes: LayoutNode[] = [
           { id: 'a', x: 0, y: 0, width: 100, height: 50 },
           { id: 'b', x: 500, y: 500, width: 100, height: 50 },
         ];
         const resolved = resolveCollisions(nodes);
         expect(resolved[0].x).toBe(0);
         expect(resolved[1].x).toBe(500);
       });
     });

     describe('Spring Animation', () => {
       it('crea estado spring con posición actual y target', () => {
         const spring = createSpringState(0, 0, 100, 100);
         expect(spring.x).toBe(0);
         expect(spring.y).toBe(0);
         expect(spring.targetX).toBe(100);
         expect(spring.targetY).toBe(100);
         expect(spring.done).toBe(false);
       });

       it('se mueve hacia el target en cada update', () => {
         let spring = createSpringState(0, 0, 100, 100);
         spring = updateSpring(spring);
         expect(spring.x).toBeGreaterThan(0);
         expect(spring.y).toBeGreaterThan(0);
       });

       it('converge al target después de múltiples updates', () => {
         let spring = createSpringState(0, 0, 100, 100);
         for (let i = 0; i < 100; i++) {
           spring = updateSpring(spring);
           if (spring.done) break;
         }
         expect(spring.done).toBe(true);
         expect(spring.x).toBe(100);
         expect(spring.y).toBe(100);
       });

       it('no modifica un spring ya completado', () => {
         let spring = createSpringState(100, 100, 100, 100);
         spring = { ...spring, done: true };
         const updated = updateSpring(spring);
         expect(updated.x).toBe(100);
         expect(updated.y).toBe(100);
         expect(updated.done).toBe(true);
       });
     });

     describe('DEFAULT_CONFIG', () => {
       it('tiene valores por defecto razonables', () => {
         expect(DEFAULT_CONFIG.firstRingRadius).toBeGreaterThan(100);
         expect(DEFAULT_CONFIG.ringSpacing).toBeGreaterThan(50);
         expect(DEFAULT_CONFIG.maxNodesPerRing).toBeGreaterThan(4);
       });
     });
   });

4. Ejecutar tests:
   cd ~/yeyo-os/frontend
   npx jest __tests__/lib/layout/orbital.test.ts --no-cache

VERIFICAR:
- [ ] Archivo src/lib/layout/orbital.ts existe
- [ ] calculateOrbitalPositions posiciona nodos en círculos concéntricos
- [ ] Los nodos no se superponen en las posiciones calculadas
- [ ] detectCollisions encuentra pares de nodos que colisionan
- [ ] resolveCollisions separa los nodos colisionados
- [ ] Spring animation converge al target en ~300ms (múltiples frames)
- [ ] createSpringState + updateSpring trabajan juntos
- [ ] TODOS los tests pasan

SI FALLA:
- Math errors: verificar cálculos de ángulos y distancias
- Infinite loop en resolveCollisions: maxIterations lo previene
- Spring no converge: ajustar SETTLE_THRESHOLD

NO HACER:
- No integrar con PixiJS todavía (eso se hace al componer el hub completo)
- No persistir posiciones a localStorage aún (micro-fase 3.11)
- No agregar animaciones de entrada/salida aún

GATE: Layout engine posiciona nodos en órbitas, no se superponen, spring animation funciona, todos los tests pasan.
```
