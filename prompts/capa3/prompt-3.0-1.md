## ═══════════════════════════════════════
## MICRO-FASE 3.0 — Hub Canvas Setup
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 3.0-1 [VSCODE] — Inicializar canvas PixiJS 8 como viewport principal del Neural Hub

```
Estamos construyendo YeyoOS, un OS AI-nativo con interfaz Neural Hub. Esta es la micro-fase 3.0 de Capa 3 (Cuerpo): inicializar el canvas PixiJS 8 como viewport principal.

CONTEXTO:
- Capa 0 completada: infraestructura Docker, PostgreSQL, Redis, Ollama
- Capa 0.5 completada: scaffold Next.js 14 + Tailwind CSS + Zustand
- Capa 1 completada: interfaces hexagonales, API REST, WebSocket
- Capa 2 completada: Flash Memory, chat contextual, RAG pipeline
- Frontend stack: Next.js 14 (App Router), PixiJS 8, Tailwind CSS, Zustand
- Hardware: GTX 1060 3GB VRAM, compositor reserva ~200MB
- Target: 60fps estable en el canvas

Abre el directorio ~/yeyo-os/frontend en VS Code.

CREAR:

1. Instalar dependencias si no existen:
   cd ~/yeyo-os/frontend
   npm install pixi.js@^8.0.0

2. Crear estructura de directorios:
   mkdir -p src/components/hub
   mkdir -p src/lib/store
   mkdir -p __tests__/components/hub

3. Crear archivo src/components/hub/HubCanvas.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/hub/HubCanvas.tsx
   Contenido:

   /**
    * YeyoOS — HubCanvas (Viewport Principal del Neural Hub)
    * Micro-fase 3.0 — Capa 3: Cuerpo
    *
    * Canvas PixiJS 8 a pantalla completa que sirve como viewport
    * principal del Neural Hub. Todos los nodos viven aquí.
    */

   'use client';

   import { useEffect, useRef, useCallback } from 'react';
   import { Application } from 'pixi.js';
   import { useHubStore } from '@/lib/store/hub-store';

   const BACKGROUND_COLOR = 0x0a0a0f;
   const TARGET_FPS = 60;

   export interface HubCanvasProps {
     width?: number;
     height?: number;
   }

   export default function HubCanvas({ width, height }: HubCanvasProps) {
     const canvasRef = useRef<HTMLDivElement>(null);
     const appRef = useRef<Application | null>(null);
     const setCanvasSize = useHubStore((s) => s.setCanvasSize);

     const initApp = useCallback(async () => {
       if (!canvasRef.current || appRef.current) return;

       const app = new Application();

       await app.init({
         background: BACKGROUND_COLOR,
         resizeTo: width && height ? undefined : window,
         width: width ?? window.innerWidth,
         height: height ?? window.innerHeight,
         antialias: true,
         resolution: window.devicePixelRatio || 1,
         autoDensity: true,
         preferWebGLVersion: 2,
       });

       canvasRef.current.appendChild(app.canvas as HTMLCanvasElement);
       appRef.current = app;

       setCanvasSize({
         width: app.screen.width,
         height: app.screen.height,
       });

       app.ticker.maxFPS = TARGET_FPS;
     }, [width, height, setCanvasSize]);

     const handleResize = useCallback(() => {
       const app = appRef.current;
       if (!app) return;

       if (!width && !height) {
         app.renderer.resize(window.innerWidth, window.innerHeight);
       }

       setCanvasSize({
         width: app.screen.width,
         height: app.screen.height,
       });
     }, [width, height, setCanvasSize]);

     useEffect(() => {
       initApp();

       return () => {
         if (appRef.current) {
           appRef.current.destroy(true);
           appRef.current = null;
         }
       };
     }, [initApp]);

     useEffect(() => {
       window.addEventListener('resize', handleResize);
       return () => window.removeEventListener('resize', handleResize);
     }, [handleResize]);

     return (
       <div
         ref={canvasRef}
         data-testid="hub-canvas"
         style={{
           width: width ? `${width}px` : '100vw',
           height: height ? `${height}px` : '100vh',
           overflow: 'hidden',
           position: 'relative',
         }}
       />
     );
   }

   export { BACKGROUND_COLOR, TARGET_FPS };

4. Crear archivo src/lib/store/hub-store.ts (store básico para canvas):

   Ruta: ~/yeyo-os/frontend/src/lib/store/hub-store.ts
   Contenido:

   /**
    * YeyoOS — Hub Store (Estado del Neural Hub)
    * Micro-fase 3.0 — Capa 3: Cuerpo
    */

   import { create } from 'zustand';

   export interface CanvasSize {
     width: number;
     height: number;
   }

   export interface NodePosition {
     id: string;
     x: number;
     y: number;
   }

   export interface HubState {
     canvasSize: CanvasSize;
     nodes: NodePosition[];
     setCanvasSize: (size: CanvasSize) => void;
     addNode: (node: NodePosition) => void;
     updateNodePosition: (id: string, x: number, y: number) => void;
     removeNode: (id: string) => void;
   }

   export const useHubStore = create<HubState>((set) => ({
     canvasSize: { width: 0, height: 0 },
     nodes: [],

     setCanvasSize: (size) => set({ canvasSize: size }),

     addNode: (node) =>
       set((state) => ({
         nodes: [...state.nodes, node],
       })),

     updateNodePosition: (id, x, y) =>
       set((state) => ({
         nodes: state.nodes.map((n) => (n.id === id ? { ...n, x, y } : n)),
       })),

     removeNode: (id) =>
       set((state) => ({
         nodes: state.nodes.filter((n) => n.id !== id),
       })),
   }));

5. Crear archivo __tests__/components/hub/HubCanvas.test.tsx:

   Ruta: ~/yeyo-os/frontend/__tests__/components/hub/HubCanvas.test.tsx
   Contenido:

   /**
    * Tests para HubCanvas — Micro-fase 3.0
    */

   import { render, screen, act } from '@testing-library/react';
   import HubCanvas, { BACKGROUND_COLOR, TARGET_FPS } from '@/components/hub/HubCanvas';
   import { useHubStore } from '@/lib/store/hub-store';

   // Mock PixiJS Application
   const mockInit = jest.fn().mockResolvedValue(undefined);
   const mockDestroy = jest.fn();
   const mockResize = jest.fn();
   const mockCanvas = document.createElement('canvas');

   jest.mock('pixi.js', () => ({
     Application: jest.fn().mockImplementation(() => ({
       init: mockInit,
       destroy: mockDestroy,
       canvas: mockCanvas,
       screen: { width: 1920, height: 1080 },
       renderer: { resize: mockResize },
       ticker: { maxFPS: 0 },
     })),
   }));

   describe('HubCanvas', () => {
     beforeEach(() => {
       jest.clearAllMocks();
       useHubStore.setState({
         canvasSize: { width: 0, height: 0 },
         nodes: [],
       });
     });

     it('renderiza el contenedor del canvas', () => {
       render(<HubCanvas />);
       const container = screen.getByTestId('hub-canvas');
       expect(container).toBeInTheDocument();
     });

     it('el contenedor ocupa viewport completo por defecto', () => {
       render(<HubCanvas />);
       const container = screen.getByTestId('hub-canvas');
       expect(container.style.width).toBe('100vw');
       expect(container.style.height).toBe('100vh');
     });

     it('acepta dimensiones personalizadas', () => {
       render(<HubCanvas width={800} height={600} />);
       const container = screen.getByTestId('hub-canvas');
       expect(container.style.width).toBe('800px');
       expect(container.style.height).toBe('600px');
     });

     it('inicializa PixiJS Application al montar', async () => {
       await act(async () => {
         render(<HubCanvas />);
       });
       expect(mockInit).toHaveBeenCalledWith(
         expect.objectContaining({
           background: BACKGROUND_COLOR,
           antialias: true,
           preferWebGLVersion: 2,
         })
       );
     });

     it('destruye la aplicación al desmontar', async () => {
       let unmount: () => void;
       await act(async () => {
         const result = render(<HubCanvas />);
         unmount = result.unmount;
       });
       act(() => {
         unmount!();
       });
       expect(mockDestroy).toHaveBeenCalledWith(true);
     });

     it('actualiza el store con el tamaño del canvas', async () => {
       await act(async () => {
         render(<HubCanvas />);
       });
       const { canvasSize } = useHubStore.getState();
       expect(canvasSize.width).toBe(1920);
       expect(canvasSize.height).toBe(1080);
     });

     it('responde a eventos de resize', async () => {
       await act(async () => {
         render(<HubCanvas />);
       });
       act(() => {
         window.dispatchEvent(new Event('resize'));
       });
       expect(mockResize).toHaveBeenCalled();
     });

     it('exporta constantes correctas', () => {
       expect(BACKGROUND_COLOR).toBe(0x0a0a0f);
       expect(TARGET_FPS).toBe(60);
     });
   });

6. Ejecutar tests:
   cd ~/yeyo-os/frontend
   npx jest __tests__/components/hub/HubCanvas.test.tsx --no-cache

VERIFICAR:
- [ ] Archivo src/components/hub/HubCanvas.tsx existe
- [ ] Archivo src/lib/store/hub-store.ts existe
- [ ] HubCanvas renderiza un div con data-testid="hub-canvas"
- [ ] Canvas ocupa 100vw x 100vh por defecto
- [ ] PixiJS 8 se inicializa con WebGL2 y fondo #0a0a0f
- [ ] Resize handler actualiza el canvas y el store
- [ ] Se destruye correctamente al desmontar
- [ ] TODOS los tests pasan

SI FALLA:
- PixiJS no instalado: npm install pixi.js@^8.0.0
- Error de import @/: verificar tsconfig.json tiene paths configurados
- Jest no soporta ESM: verificar jest.config con transformIgnorePatterns para pixi.js
- Canvas no existe en jsdom: el mock lo maneja

NO HACER:
- No agregar nodos todavía (eso es micro-fase 3.1+)
- No implementar drag & drop aún
- No conectar WebSocket aún
- No agregar UI elements al canvas

GATE: HubCanvas renderiza a pantalla completa, PixiJS 8 inicializado con WebGL2, resize funciona, store actualizado, todos los tests pasan.
```
