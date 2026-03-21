## ═══════════════════════════════════════
## MICRO-FASE 3.1 — Central Node
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 3.1-1 [VSCODE] — Nodo central pulsante con shader GLSL de glow

```
Estamos construyendo YeyoOS, un OS AI-nativo con interfaz Neural Hub. Esta es la micro-fase 3.1 de Capa 3 (Cuerpo): crear el nodo central pulsante con efecto glow GLSL.

CONTEXTO:
- Micro-fase 3.0 completada: HubCanvas con PixiJS 8, WebGL2, store Zustand
- El nodo central representa la IA. Es el centro del universo del Neural Hub.
- Estados de la IA: idle (glow azul lento), thinking (pulso brillante rápido), error (rojo), offline (dim)
- Hardware: GTX 1060 3GB VRAM — shader debe ser ligero
- PixiJS 8 API: usa Filter, GlProgram, Shader (NO la API v7)
- El nodo central NO es draggable — siempre al centro del canvas

Abre el directorio ~/yeyo-os/frontend en VS Code.

CREAR:

1. Crear estructura de directorios:
   mkdir -p src/components/hub
   mkdir -p src/shaders
   mkdir -p __tests__/components/hub

2. Crear archivo src/shaders/glow.frag:

   Ruta: ~/yeyo-os/frontend/src/shaders/glow.frag
   Contenido:

   precision mediump float;

   varying vec2 vTextureCoord;
   uniform sampler2D uTexture;
   uniform float uTime;
   uniform float uPulseSpeed;
   uniform vec3 uGlowColor;
   uniform float uGlowIntensity;
   uniform float uRadius;

   void main() {
       vec2 uv = vTextureCoord;
       vec2 center = vec2(0.5, 0.5);
       float dist = distance(uv, center);

       float pulse = sin(uTime * uPulseSpeed) * 0.5 + 0.5;
       float glowRadius = uRadius * (1.0 + pulse * 0.3);

       float glow = smoothstep(glowRadius, glowRadius * 0.3, dist);
       glow *= uGlowIntensity * (0.7 + pulse * 0.3);

       vec4 texColor = texture2D(uTexture, uv);
       vec3 finalColor = mix(texColor.rgb, uGlowColor, glow * 0.6);
       float finalAlpha = max(texColor.a, glow * 0.8);

       gl_FragColor = vec4(finalColor, finalAlpha);
   }

3. Crear archivo src/shaders/glow.vert:

   Ruta: ~/yeyo-os/frontend/src/shaders/glow.vert
   Contenido:

   precision mediump float;

   attribute vec2 aPosition;
   attribute vec2 aTextureCoord;

   uniform mat3 uProjectionMatrix;
   uniform mat3 uWorldTransformMatrix;
   uniform mat3 uTransformMatrix;

   varying vec2 vTextureCoord;

   void main() {
       mat3 mvp = uProjectionMatrix * uWorldTransformMatrix * uTransformMatrix;
       vec3 pos = mvp * vec3(aPosition, 1.0);
       gl_Position = vec4(pos.xy, 0.0, 1.0);
       vTextureCoord = aTextureCoord;
   }

4. Crear archivo src/components/hub/CentralNode.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/hub/CentralNode.tsx
   Contenido:

   /**
    * YeyoOS — CentralNode (Nodo Central del Neural Hub)
    * Micro-fase 3.1 — Capa 3: Cuerpo
    *
    * Nodo central pulsante con shader GLSL de glow.
    * Representa la IA. Siempre al centro del canvas.
    * NO es draggable.
    */

   'use client';

   import { useEffect, useRef, useCallback } from 'react';
   import { Container, Graphics, Filter, GlProgram } from 'pixi.js';
   import { useHubStore } from '@/lib/store/hub-store';

   import glowVert from '@/shaders/glow.vert';
   import glowFrag from '@/shaders/glow.frag';

   export type AIState = 'idle' | 'thinking' | 'error' | 'offline';

   export interface CentralNodeConfig {
     radius: number;
     state: AIState;
   }

   const STATE_CONFIG: Record<AIState, { color: number; glowColor: [number, number, number]; pulseSpeed: number; intensity: number }> = {
     idle: {
       color: 0x1e90ff,
       glowColor: [0.12, 0.56, 1.0],
       pulseSpeed: 1.5,
       intensity: 0.8,
     },
     thinking: {
       color: 0x00bfff,
       glowColor: [0.0, 0.75, 1.0],
       pulseSpeed: 4.0,
       intensity: 1.2,
     },
     error: {
       color: 0xff4444,
       glowColor: [1.0, 0.27, 0.27],
       pulseSpeed: 6.0,
       intensity: 1.0,
     },
     offline: {
       color: 0x444466,
       glowColor: [0.27, 0.27, 0.4],
       pulseSpeed: 0.5,
       intensity: 0.3,
     },
   };

   export function createGlowFilter(): Filter {
     const glProgram = GlProgram.from({
       vertex: glowVert,
       fragment: glowFrag,
     });

     return new Filter({
       glProgram,
       resources: {
         uniforms: {
           uTime: { value: 0, type: 'f32' },
           uPulseSpeed: { value: 1.5, type: 'f32' },
           uGlowColor: { value: new Float32Array([0.12, 0.56, 1.0]), type: 'vec3<f32>' },
           uGlowIntensity: { value: 0.8, type: 'f32' },
           uRadius: { value: 0.35, type: 'f32' },
         },
       },
     });
   }

   export function createCentralNodeGraphics(radius: number, color: number): Graphics {
     const g = new Graphics();
     g.circle(0, 0, radius);
     g.fill({ color });
     return g;
   }

   export function updateGlowUniforms(
     filter: Filter,
     state: AIState,
     time: number
   ): void {
     const config = STATE_CONFIG[state];
     const uniforms = filter.resources.uniforms.uniforms;
     uniforms.uTime = time;
     uniforms.uPulseSpeed = config.pulseSpeed;
     uniforms.uGlowColor = new Float32Array(config.glowColor);
     uniforms.uGlowIntensity = config.intensity;
   }

   export function getCenterPosition(canvasWidth: number, canvasHeight: number) {
     return {
       x: canvasWidth / 2,
       y: canvasHeight / 2,
     };
   }

   export { STATE_CONFIG };

5. Crear archivo __tests__/components/hub/CentralNode.test.ts:

   Ruta: ~/yeyo-os/frontend/__tests__/components/hub/CentralNode.test.ts
   Contenido:

   /**
    * Tests para CentralNode — Micro-fase 3.1
    */

   import {
     STATE_CONFIG,
     getCenterPosition,
     createCentralNodeGraphics,
     updateGlowUniforms,
     createGlowFilter,
   } from '@/components/hub/CentralNode';
   import type { AIState } from '@/components/hub/CentralNode';

   // Mock PixiJS
   jest.mock('pixi.js', () => {
     const mockGraphics = {
       circle: jest.fn().mockReturnThis(),
       fill: jest.fn().mockReturnThis(),
     };
     const mockFilter = {
       resources: {
         uniforms: {
           uniforms: {
             uTime: 0,
             uPulseSpeed: 1.5,
             uGlowColor: new Float32Array([0, 0, 0]),
             uGlowIntensity: 0.8,
             uRadius: 0.35,
           },
         },
       },
     };
     return {
       Container: jest.fn(),
       Graphics: jest.fn(() => mockGraphics),
       Filter: jest.fn(() => mockFilter),
       GlProgram: {
         from: jest.fn(() => ({})),
       },
     };
   });

   jest.mock('@/shaders/glow.vert', () => 'mock-vertex-shader', { virtual: true });
   jest.mock('@/shaders/glow.frag', () => 'mock-fragment-shader', { virtual: true });

   describe('CentralNode', () => {
     describe('STATE_CONFIG', () => {
       it('tiene configuración para los 4 estados', () => {
         expect(STATE_CONFIG).toHaveProperty('idle');
         expect(STATE_CONFIG).toHaveProperty('thinking');
         expect(STATE_CONFIG).toHaveProperty('error');
         expect(STATE_CONFIG).toHaveProperty('offline');
       });

       it('idle tiene glow azul con pulso lento', () => {
         expect(STATE_CONFIG.idle.color).toBe(0x1e90ff);
         expect(STATE_CONFIG.idle.pulseSpeed).toBe(1.5);
       });

       it('thinking tiene pulso rápido y alta intensidad', () => {
         expect(STATE_CONFIG.thinking.pulseSpeed).toBe(4.0);
         expect(STATE_CONFIG.thinking.intensity).toBe(1.2);
       });

       it('error tiene color rojo y pulso muy rápido', () => {
         expect(STATE_CONFIG.error.color).toBe(0xff4444);
         expect(STATE_CONFIG.error.pulseSpeed).toBe(6.0);
       });

       it('offline tiene baja intensidad', () => {
         expect(STATE_CONFIG.offline.intensity).toBe(0.3);
         expect(STATE_CONFIG.offline.pulseSpeed).toBe(0.5);
       });
     });

     describe('getCenterPosition', () => {
       it('calcula el centro del canvas', () => {
         const pos = getCenterPosition(1920, 1080);
         expect(pos.x).toBe(960);
         expect(pos.y).toBe(540);
       });

       it('maneja dimensiones impares', () => {
         const pos = getCenterPosition(1921, 1081);
         expect(pos.x).toBe(960.5);
         expect(pos.y).toBe(540.5);
       });
     });

     describe('createCentralNodeGraphics', () => {
       it('crea un gráfico circular', () => {
         const g = createCentralNodeGraphics(50, 0x1e90ff);
         expect(g.circle).toHaveBeenCalledWith(0, 0, 50);
         expect(g.fill).toHaveBeenCalledWith({ color: 0x1e90ff });
       });
     });

     describe('createGlowFilter', () => {
       it('crea un filtro sin errores', () => {
         const filter = createGlowFilter();
         expect(filter).toBeDefined();
       });
     });

     describe('updateGlowUniforms', () => {
       it('actualiza uniforms para estado idle', () => {
         const filter = createGlowFilter();
         updateGlowUniforms(filter, 'idle', 1.0);
         const uniforms = filter.resources.uniforms.uniforms;
         expect(uniforms.uTime).toBe(1.0);
         expect(uniforms.uPulseSpeed).toBe(1.5);
         expect(uniforms.uGlowIntensity).toBe(0.8);
       });

       it('actualiza uniforms para estado thinking', () => {
         const filter = createGlowFilter();
         updateGlowUniforms(filter, 'thinking', 2.0);
         const uniforms = filter.resources.uniforms.uniforms;
         expect(uniforms.uPulseSpeed).toBe(4.0);
         expect(uniforms.uGlowIntensity).toBe(1.2);
       });

       it('actualiza uniforms para estado error', () => {
         const filter = createGlowFilter();
         updateGlowUniforms(filter, 'error', 3.0);
         const uniforms = filter.resources.uniforms.uniforms;
         expect(uniforms.uPulseSpeed).toBe(6.0);
       });

       it('cambia entre todos los estados', () => {
         const filter = createGlowFilter();
         const states: AIState[] = ['idle', 'thinking', 'error', 'offline'];
         states.forEach((state, i) => {
           updateGlowUniforms(filter, state, i);
           const uniforms = filter.resources.uniforms.uniforms;
           expect(uniforms.uPulseSpeed).toBe(STATE_CONFIG[state].pulseSpeed);
         });
       });
     });
   });

6. Ejecutar tests:
   cd ~/yeyo-os/frontend
   npx jest __tests__/components/hub/CentralNode.test.ts --no-cache

VERIFICAR:
- [ ] Archivo src/components/hub/CentralNode.tsx existe
- [ ] Archivos src/shaders/glow.vert y glow.frag existen
- [ ] STATE_CONFIG tiene los 4 estados: idle, thinking, error, offline
- [ ] idle = azul, thinking = brillante rápido, error = rojo, offline = dim
- [ ] getCenterPosition calcula el centro correctamente
- [ ] createCentralNodeGraphics crea un círculo con el radio y color dados
- [ ] updateGlowUniforms cambia los uniforms según el estado
- [ ] TODOS los tests pasan

SI FALLA:
- Shader imports: configurar raw-loader o asset modules en Next.js config
- PixiJS Filter API: verificar que se usa la API v8 (no v7)
- Mock issues: verificar que los mocks reflejan la estructura de PixiJS 8

NO HACER:
- No renderizar el nodo central directamente en el DOM (vive dentro del canvas PixiJS)
- No hacer el nodo draggable (es el centro del universo)
- No conectar al WebSocket aún
- No optimizar el shader prematuramente

GATE: CentralNode tiene 4 estados visuales, shader GLSL funciona, posición siempre al centro, todos los tests pasan.
```
