---
## ═══════════════════════════════════════
## MICRO-FASE 3.19 — Hub Activo: Nodos Libres + Energía
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 3.19-1 [VSCODE] — Canvas libre con pan/zoom, energy lines y vignette durante pipelines

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 3.19 de Capa 3 (Cuerpo): transformar el Hub de órbita fija a nodos libres en canvas con pan/zoom, y agregar energy lines con partículas y vignette overlay durante la ejecución de pipelines.

CONTEXTO:
- Micro-fase 3.18 completada: Double Grid Background y Onboarding funcionando
- Micro-fase 3.0–3.17 completadas: Hub Canvas con PixiJS 8, nodos, grafos, stores
- hubStore existente en frontend/src/stores/hubStore.ts — MODIFICAR, no reemplazar
- Stack: React + TypeScript + PixiJS 8 + Zustand
- Los nodos ahora flotan libremente (no en órbita fija) — posiciones en localStorage
- Solo aparecen nodos INSTALADOS (no los disponibles en Store)
- Hardware: GTX 1060 3GB — las partículas de energía deben ser ligeras (<50 por línea)

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Actualizar frontend/src/stores/hubStore.ts — agregar posiciones libres y nodos instalados:

   Ruta: ~/yeyo-os/frontend/src/stores/hubStore.ts
   MODIFICAR (agregar al store existente):

   Agregar a la interface HubStore:
     // Posiciones libres
     posicionesNodos: Record<string, { x: number; y: number }>
     setPosicionNodo: (nodeId: string, x: number, y: number) => void
     cargarPosicionesDesdeStorage: (userId: string) => void
     guardarPosicionesEnStorage: (userId: string) => void

     // Nodos instalados
     nodosInstalados: string[]  // IDs de nodos instalados
     setNodosInstalados: (ids: string[]) => void
     esNodoInstalado: (id: string) => boolean

     // Estado de pipeline activo
     pipelineActivo: boolean
     nodosEnPipeline: string[]  // IDs de nodos participando en el pipeline activo
     setPipelineActivo: (activo: boolean, nodos?: string[]) => void

   Agregar a la implementación:
     posicionesNodos: {},
     setPosicionNodo: (nodeId, x, y) => {
       set((state) => ({
         posicionesNodos: { ...state.posicionesNodos, [nodeId]: { x, y } },
       }))
     },
     cargarPosicionesDesdeStorage: (userId) => {
       try {
         const key = `yeyo_hub_positions_${userId}`
         const raw = localStorage.getItem(key)
         if (raw) set({ posicionesNodos: JSON.parse(raw) })
       } catch { /* ignorar errores de storage */ }
     },
     guardarPosicionesEnStorage: (userId) => {
       try {
         const key = `yeyo_hub_positions_${userId}`
         localStorage.setItem(key, JSON.stringify(get().posicionesNodos))
       } catch { /* ignorar errores de storage */ }
     },

     nodosInstalados: [],
     setNodosInstalados: (ids) => set({ nodosInstalados: ids }),
     esNodoInstalado: (id) => get().nodosInstalados.includes(id),

     pipelineActivo: false,
     nodosEnPipeline: [],
     setPipelineActivo: (activo, nodos = []) =>
       set({ pipelineActivo: activo, nodosEnPipeline: nodos }),

2. Crear archivo frontend/src/components/hub/FreeCanvas.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/hub/FreeCanvas.tsx
   Contenido:

   /**
    * YeyoOS — FreeCanvas
    * Micro-fase 3.19 — Capa 3: Cuerpo
    *
    * Canvas PixiJS con pan/zoom y nodos libres.
    * - Nodos flotan en posiciones libres (no órbita)
    * - Solo muestra nodos INSTALADOS
    * - Posiciones guardadas en localStorage por usuario
    * - Drag para mover nodos, doble-click para abrir
    * - Canvas draggable (pan) con mouse drag
    * - Zoom con scroll de ratón (0.3x — 3.0x)
    */

   import React, { useEffect, useRef, useCallback } from 'react'
   import * as PIXI from 'pixi.js'
   import { useHubStore } from '../../stores/hubStore'
   import { GridBackground } from './GridBackground'

   export interface NodoLibreInfo {
     id: string
     label: string
     tipo: string
     icono?: string
     colorAcento?: string
     estado?: 'idle' | 'activo' | 'error'
   }

   export interface FreeCanvasProps {
     nodos: NodoLibreInfo[]
     userId: string
     onNodoClick?: (nodeId: string) => void
     onNodoDoubleClick?: (nodeId: string) => void
     width?: number
     height?: number
     style?: React.CSSProperties
   }

   const DEFAULT_COLORS: Record<string, number> = {
     idle: 0x1565C0,
     activo: 0x4FC3F7,
     error: 0xF44336,
   }

   const NODE_RADIUS = 36

   export function FreeCanvas({
     nodos,
     userId,
     onNodoClick,
     onNodoDoubleClick,
     width = 800,
     height = 600,
     style,
   }: FreeCanvasProps) {
     const containerRef = useRef<HTMLDivElement>(null)
     const appRef = useRef<PIXI.Application | null>(null)
     const worldRef = useRef<PIXI.Container | null>(null)
     const nodeContainersRef = useRef<Map<string, PIXI.Container>>(new Map())

     const {
       posicionesNodos,
       setPosicionNodo,
       cargarPosicionesDesdeStorage,
       guardarPosicionesEnStorage,
       nodosInstalados,
       pipelineActivo,
       nodosEnPipeline,
     } = useHubStore()

     useEffect(() => {
       cargarPosicionesDesdeStorage(userId)
     }, [userId])

     useEffect(() => {
       if (!containerRef.current) return

       const app = new PIXI.Application()
       appRef.current = app

       app.init({
         width,
         height,
         backgroundColor: 0x050A14,
         antialias: true,
         resolution: window.devicePixelRatio || 1,
       }).then(() => {
         if (!containerRef.current) return
         containerRef.current.appendChild(app.canvas as HTMLCanvasElement)

         // World container — se mueve con pan/zoom
         const world = new PIXI.Container()
         worldRef.current = world
         app.stage.addChild(world)

         // Estado de pan
         let isPanning = false
         let panStart = { x: 0, y: 0 }
         let worldStart = { x: 0, y: 0 }

         app.canvas.addEventListener('mousedown', (e: MouseEvent) => {
           isPanning = true
           panStart = { x: e.clientX, y: e.clientY }
           worldStart = { x: world.x, y: world.y }
         })

         app.canvas.addEventListener('mousemove', (e: MouseEvent) => {
           if (!isPanning) return
           world.x = worldStart.x + (e.clientX - panStart.x)
           world.y = worldStart.y + (e.clientY - panStart.y)
         })

         app.canvas.addEventListener('mouseup', () => { isPanning = false })
         app.canvas.addEventListener('mouseleave', () => { isPanning = false })

         // Zoom con scroll
         app.canvas.addEventListener('wheel', (e: WheelEvent) => {
           e.preventDefault()
           const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1
           const newScale = Math.max(0.3, Math.min(3.0, world.scale.x * zoomFactor))
           world.scale.set(newScale)
         })

         renderNodos()
       })

       return () => {
         guardarPosicionesEnStorage(userId)
         app.destroy(true, { children: true })
         appRef.current = null
       }
     }, [width, height])

     const renderNodos = useCallback(() => {
       const world = worldRef.current
       if (!world) return

       world.removeChildren()
       nodeContainersRef.current.clear()

       nodos.filter(n => nodosInstalados.includes(n.id) || nodos.length <= 1).forEach((nodo, i) => {
         const pos = posicionesNodos[nodo.id] ?? {
           x: 150 + (i % 4) * 180,
           y: 150 + Math.floor(i / 4) * 180,
         }

         const container = new PIXI.Container()
         container.x = pos.x
         container.y = pos.y
         container.eventMode = 'static'
         container.cursor = 'pointer'

         // Círculo base
         const circle = new PIXI.Graphics()
         const estado = nodo.estado ?? 'idle'
         const color = DEFAULT_COLORS[estado]
         circle.circle(0, 0, NODE_RADIUS)
         circle.fill({ color, alpha: estado === 'activo' ? 0.9 : 0.7 })
         circle.stroke({ width: 2, color: estado === 'activo' ? 0x4FC3F7 : 0x1E3A5F })
         container.addChild(circle)

         // Etiqueta
         const label = new PIXI.Text({
           text: nodo.label,
           style: new PIXI.TextStyle({ fill: 0xE0F7FA, fontSize: 11, fontFamily: 'Inter, sans-serif' }),
         })
         label.anchor.set(0.5, 0)
         label.y = NODE_RADIUS + 6
         container.addChild(label)

         // Drag behavior
         let dragStart: { x: number; y: number } | null = null
         let containerStart: { x: number; y: number } | null = null
         let isDragging = false

         container.on('pointerdown', (e: PIXI.FederatedPointerEvent) => {
           dragStart = { x: e.globalX, y: e.globalY }
           containerStart = { x: container.x, y: container.y }
           isDragging = false
         })

         container.on('pointermove', (e: PIXI.FederatedPointerEvent) => {
           if (!dragStart || !containerStart) return
           const dx = e.globalX - dragStart.x
           const dy = e.globalY - dragStart.y
           if (Math.abs(dx) > 4 || Math.abs(dy) > 4) {
             isDragging = true
             container.x = containerStart.x + dx
             container.y = containerStart.y + dy
           }
         })

         container.on('pointerup', () => {
           if (isDragging) {
             setPosicionNodo(nodo.id, container.x, container.y)
             guardarPosicionesEnStorage(userId)
           } else {
             onNodoClick?.(nodo.id)
           }
           dragStart = null
           containerStart = null
         })

         container.on('pointerdblclick', () => {
           onNodoDoubleClick?.(nodo.id)
         })

         world.addChild(container)
         nodeContainersRef.current.set(nodo.id, container)
       })
     }, [nodos, nodosInstalados, posicionesNodos])

     useEffect(() => {
       renderNodos()
     }, [nodos, posicionesNodos, nodosInstalados])

     return (
       <div
         ref={containerRef}
         data-testid="free-canvas"
         data-pipeline-activo={pipelineActivo}
         style={{
           position: 'relative',
           width,
           height,
           overflow: 'hidden',
           cursor: 'grab',
           ...style,
         }}
       />
     )
   }

3. Crear archivo frontend/src/components/hub/EnergyLine.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/hub/EnergyLine.tsx
   Contenido:

   /**
    * YeyoOS — EnergyLine
    * Micro-fase 3.19 — Capa 3: Cuerpo
    *
    * Línea de energía con partículas que fluyen desde un punto origen
    * a un punto destino. Renderizado con PixiJS Graphics + Ticker.
    * Máximo 50 partículas por línea para no sobrecargar la GPU.
    *
    * Props:
    *   fromX, fromY — punto de origen (nodo central YEYO)
    *   toX, toY     — punto de destino (nodo activo del pipeline)
    *   active       — si false, no renderiza partículas
    *   intensity    — 0.0-1.0, controla velocidad y brillo de partículas
    *   container    — PIXI.Container donde dibujar (del FreeCanvas)
    */

   import { useEffect, useRef } from 'react'
   import * as PIXI from 'pixi.js'

   interface Particle {
     progress: number  // 0.0 → 1.0 a lo largo de la línea
     speed: number
     size: number
     alpha: number
   }

   export interface EnergyLineProps {
     fromX: number
     fromY: number
     toX: number
     toY: number
     active?: boolean
     intensity?: number       // 0.0-1.0
     maxParticles?: number    // default: 30
     container: PIXI.Container
     app: PIXI.Application
   }

   const LINE_COLOR = 0x4FC3F7
   const PARTICLE_COLOR = 0xB3E5FC
   const LINE_ALPHA = 0.25
   const PARTICLE_ALPHA_MAX = 0.9

   export function useEnergyLine({
     fromX,
     fromY,
     toX,
     toY,
     active = true,
     intensity = 0.5,
     maxParticles = 30,
     container,
     app,
   }: EnergyLineProps): void {
     const graphicsRef = useRef<PIXI.Graphics | null>(null)
     const particlesRef = useRef<Particle[]>([])
     const tickerCallbackRef = useRef<((ticker: PIXI.Ticker) => void) | null>(null)

     useEffect(() => {
       if (!active) {
         if (graphicsRef.current) {
           container.removeChild(graphicsRef.current)
           graphicsRef.current.destroy()
           graphicsRef.current = null
         }
         if (tickerCallbackRef.current) {
           app.ticker.remove(tickerCallbackRef.current)
           tickerCallbackRef.current = null
         }
         return
       }

       const gfx = new PIXI.Graphics()
       graphicsRef.current = gfx
       container.addChild(gfx)

       // Inicializar partículas escalonadas
       particlesRef.current = Array.from({ length: maxParticles }, (_, i) => ({
         progress: i / maxParticles,
         speed: 0.004 + intensity * 0.006 + Math.random() * 0.002,
         size: 2 + Math.random() * 2,
         alpha: 0.5 + Math.random() * 0.5,
       }))

       const onTick = (_ticker: PIXI.Ticker) => {
         gfx.clear()

         // Línea base
         gfx.moveTo(fromX, fromY)
         gfx.lineTo(toX, toY)
         gfx.stroke({ width: 1, color: LINE_COLOR, alpha: LINE_ALPHA })

         // Actualizar y dibujar partículas
         particlesRef.current.forEach((p) => {
           p.progress += p.speed * (1 + intensity)
           if (p.progress > 1) p.progress -= 1

           const x = fromX + (toX - fromX) * p.progress
           const y = fromY + (toY - fromY) * p.progress

           gfx.circle(x, y, p.size)
           gfx.fill({ color: PARTICLE_COLOR, alpha: p.alpha * PARTICLE_ALPHA_MAX })
         })
       }

       tickerCallbackRef.current = onTick
       app.ticker.add(onTick)

       return () => {
         if (tickerCallbackRef.current) {
           app.ticker.remove(tickerCallbackRef.current)
           tickerCallbackRef.current = null
         }
         if (graphicsRef.current) {
           container.removeChild(graphicsRef.current)
           graphicsRef.current.destroy()
           graphicsRef.current = null
         }
       }
     }, [fromX, fromY, toX, toY, active, intensity, maxParticles])
   }

4. Crear archivo frontend/src/components/hub/VignetteOverlay.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/hub/VignetteOverlay.tsx
   Contenido:

   /**
    * YeyoOS — VignetteOverlay
    * Micro-fase 3.19 — Capa 3: Cuerpo
    *
    * Overlay con radial gradient negro en los bordes.
    * Aparece (fade-in 500ms) cuando un pipeline corre.
    * Desaparece (fade-out 1000ms) al terminar el pipeline.
    * ~30% opacidad máxima.
    */

   import React, { useEffect, useState } from 'react'

   export interface VignetteOverlayProps {
     visible: boolean
     maxOpacity?: number    // default: 0.30
     fadeInMs?: number      // default: 500
     fadeOutMs?: number     // default: 1000
     style?: React.CSSProperties
   }

   export function VignetteOverlay({
     visible,
     maxOpacity = 0.30,
     fadeInMs = 500,
     fadeOutMs = 1000,
     style,
   }: VignetteOverlayProps) {
     const [opacity, setOpacity] = useState(0)

     useEffect(() => {
       if (visible) {
         setOpacity(maxOpacity)
       } else {
         setOpacity(0)
       }
     }, [visible, maxOpacity])

     return (
       <div
         data-testid="vignette-overlay"
         data-visible={visible}
         style={{
           position: 'absolute',
           inset: 0,
           pointerEvents: 'none',
           background: 'radial-gradient(ellipse at center, transparent 40%, rgba(0,0,0,1) 100%)',
           opacity,
           transition: visible
             ? `opacity ${fadeInMs}ms ease-in`
             : `opacity ${fadeOutMs}ms ease-out`,
           zIndex: 5,
           ...style,
         }}
       />
     )
   }

5. Crear archivo frontend/src/__tests__/hub/FreeCanvas.test.tsx:

   Ruta: ~/yeyo-os/frontend/src/__tests__/hub/FreeCanvas.test.tsx
   Contenido:

   /**
    * Tests para FreeCanvas, EnergyLine, VignetteOverlay — Micro-fase 3.19
    */

   import React from 'react'
   import { render, screen, act } from '@testing-library/react'
   import { VignetteOverlay } from '../../components/hub/VignetteOverlay'
   import { useHubStore } from '../../stores/hubStore'

   // Mock PixiJS
   jest.mock('pixi.js', () => ({
     Application: jest.fn().mockImplementation(() => ({
       init: jest.fn().mockResolvedValue(undefined),
       destroy: jest.fn(),
       screen: { width: 800, height: 600 },
       stage: { addChild: jest.fn(), removeChildren: jest.fn() },
       ticker: { add: jest.fn(), remove: jest.fn() },
       canvas: document.createElement('canvas'),
     })),
     Container: jest.fn().mockImplementation(() => ({
       addChild: jest.fn(),
       removeChildren: jest.fn(),
       removeChild: jest.fn(),
       x: 0,
       y: 0,
       scale: { set: jest.fn(), x: 1 },
       eventMode: 'static',
       cursor: 'pointer',
       on: jest.fn(),
     })),
     Graphics: jest.fn().mockImplementation(() => ({
       circle: jest.fn().mockReturnThis(),
       fill: jest.fn().mockReturnThis(),
       stroke: jest.fn().mockReturnThis(),
       moveTo: jest.fn().mockReturnThis(),
       lineTo: jest.fn().mockReturnThis(),
       clear: jest.fn().mockReturnThis(),
       destroy: jest.fn(),
     })),
     Text: jest.fn().mockImplementation(() => ({
       anchor: { set: jest.fn() },
       y: 0,
     })),
     TextStyle: jest.fn(),
   }))

   // Mock localStorage
   const localStorageMock = (() => {
     let store: Record<string, string> = {}
     return {
       getItem: (key: string) => store[key] || null,
       setItem: (key: string, val: string) => { store[key] = val },
       clear: () => { store = {} },
     }
   })()
   Object.defineProperty(window, 'localStorage', { value: localStorageMock })

   beforeEach(() => {
     localStorageMock.clear()
     useHubStore.setState({
       posicionesNodos: {},
       nodosInstalados: [],
       pipelineActivo: false,
       nodosEnPipeline: [],
     })
   })

   describe('hubStore — posiciones y pipeline', () => {
     it('setPosicionNodo guarda posición', () => {
       act(() => {
         useHubStore.getState().setPosicionNodo('node-1', 100, 200)
       })
       expect(useHubStore.getState().posicionesNodos['node-1']).toEqual({ x: 100, y: 200 })
     })

     it('guardarPosicionesEnStorage persiste en localStorage', () => {
       act(() => {
         useHubStore.getState().setPosicionNodo('node-1', 50, 75)
         useHubStore.getState().guardarPosicionesEnStorage('user-1')
       })
       const stored = JSON.parse(localStorageMock.getItem('yeyo_hub_positions_user-1') || '{}')
       expect(stored['node-1']).toEqual({ x: 50, y: 75 })
     })

     it('cargarPosicionesDesdeStorage restaura posiciones', () => {
       localStorageMock.setItem('yeyo_hub_positions_user-1', JSON.stringify({ 'node-2': { x: 300, y: 400 } }))
       act(() => {
         useHubStore.getState().cargarPosicionesDesdeStorage('user-1')
       })
       expect(useHubStore.getState().posicionesNodos['node-2']).toEqual({ x: 300, y: 400 })
     })

     it('setNodosInstalados actualiza lista', () => {
       act(() => {
         useHubStore.getState().setNodosInstalados(['img', 'code'])
       })
       expect(useHubStore.getState().esNodoInstalado('img')).toBe(true)
       expect(useHubStore.getState().esNodoInstalado('video')).toBe(false)
     })

     it('setPipelineActivo activa el pipeline con nodos', () => {
       act(() => {
         useHubStore.getState().setPipelineActivo(true, ['yeyo', 'img'])
       })
       expect(useHubStore.getState().pipelineActivo).toBe(true)
       expect(useHubStore.getState().nodosEnPipeline).toContain('img')
     })

     it('setPipelineActivo desactiva el pipeline', () => {
       act(() => {
         useHubStore.getState().setPipelineActivo(true, ['yeyo'])
         useHubStore.getState().setPipelineActivo(false)
       })
       expect(useHubStore.getState().pipelineActivo).toBe(false)
       expect(useHubStore.getState().nodosEnPipeline).toHaveLength(0)
     })
   })

   describe('VignetteOverlay', () => {
     it('renderiza con data-visible=false por defecto', () => {
       render(<VignetteOverlay visible={false} />)
       expect(screen.getByTestId('vignette-overlay')).toHaveAttribute('data-visible', 'false')
     })

     it('renderiza con data-visible=true cuando visible=true', () => {
       render(<VignetteOverlay visible={true} />)
       expect(screen.getByTestId('vignette-overlay')).toHaveAttribute('data-visible', 'true')
     })

     it('tiene pointer-events none (no bloquea interacción)', () => {
       render(<VignetteOverlay visible={true} />)
       const el = screen.getByTestId('vignette-overlay')
       expect(el).toHaveStyle('pointer-events: none')
     })

     it('opacity 0 cuando visible=false', () => {
       render(<VignetteOverlay visible={false} maxOpacity={0.3} />)
       const el = screen.getByTestId('vignette-overlay')
       expect(el).toHaveStyle('opacity: 0')
     })

     it('opacity maxOpacity cuando visible=true', () => {
       render(<VignetteOverlay visible={true} maxOpacity={0.3} />)
       const el = screen.getByTestId('vignette-overlay')
       expect(el).toHaveStyle('opacity: 0.3')
     })
   })

VERIFICAR:
- [ ] hubStore tiene posicionesNodos, setPosicionNodo, cargarPosicionesDesdeStorage, guardarPosicionesEnStorage
- [ ] hubStore tiene nodosInstalados, setNodosInstalados, esNodoInstalado
- [ ] hubStore tiene pipelineActivo, nodosEnPipeline, setPipelineActivo
- [ ] FreeCanvas.tsx renderiza solo nodos instalados (filtro por nodosInstalados)
- [ ] FreeCanvas soporta drag de nodos (posición guardada con setPosicionNodo)
- [ ] FreeCanvas soporta pan (arrastrar canvas) y zoom (scroll)
- [ ] EnergyLine muestra línea base + partículas cuando active=true
- [ ] EnergyLine no renderiza cuando active=false
- [ ] VignetteOverlay fade-in/fade-out por prop visible
- [ ] Tests pasan: hubStore (6), VignetteOverlay (5)

SI FALLA:
- hubStore ya tiene campos en conflicto: agregar solo los campos nuevos que falten
- PixiJS error en tests: verificar que el mock cubre Container, Graphics, Text, TextStyle
- localStorage undefined: asegurarse de usar el mock de localStorage en tests
- Drag no funciona en tests: los tests de drag son de integración — solo testear el store
- Partículas lentas: reducir maxParticles a 20 si la GPU lo necesita

NO HACER:
- No implementar conexiones WebSocket para eventos de pipeline en esta micro-fase (eso es Capa 4)
- No implementar el grafo de React Flow en esta micro-fase (eso es el Automation Node de 3.20)
- No usar CSS transforms para el pan/zoom — usar PIXI.Container.x/y y scale
- No persistir el estado del pipeline en localStorage — es efímero (session only)
- No mostrar todos los nodos disponibles — SOLO los instalados

GATE: Nodos flotan libres en el canvas, se pueden mover con drag, sus posiciones se guardan en localStorage por usuario, el canvas soporta pan y zoom. Al activar pipelineActivo en el store, VignetteOverlay aparece con fade-in y EnergyLine dibuja partículas desde YEYO hacia nodos activos. Al desactivar, todo hace fade-out. Todos los tests pasan.
```
---
