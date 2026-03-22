## ═══════════════════════════════════════
## MICRO-FASE 3.17 — NodeExpandedWithGraph
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 3.17-1 [VSCODE] — Integrar GraphExecutionView en SatelliteNode expandido

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 3.17 de Capa 3 (Cuerpo): integrar GraphExecutionView dentro del SatelliteNode expandido. Cuando un nodo del Hub ejecuta un grafo, aparece automáticamente un overlay semitransparente con el mini-grafo animado.

CONTEXTO:
- Micro-fase 3.16 completada: GraphExecutionView y graphStore funcionando con tests
- Micro-fase 3.2 completada: SatelliteNode base existe en frontend/src/components/hub/
- Micro-fase 3.11 completada: Zustand stores existentes (hubStore, chatStore, uiStore, systemStore)
- graphStore en frontend/src/stores/graphStore.ts con useGraphStore
- El overlay aparece dentro del nodo expandido en la esquina inferior
- El overlay se cierra: automáticamente al completar el grafo (2s de delay) o con click del usuario
- El overlay NO bloquea la interacción con el resto del nodo expandido

Comportamiento:
  1. Nodo expandido recibe prop grafoActivo?: string (ID del grafo)
  2. Si grafoActivo tiene valor, muestra GraphExecutionView como overlay
  3. Overlay es semitransparente (background rgba(0,0,0,0.85))
  4. Posición: esquina inferior del nodo expandido (bottom-left)
  5. Al completar el grafo → espera 2 segundos → se cierra automáticamente
  6. Click en el overlay (fuera del GraphExecutionView) → cierra inmediatamente
  7. hubStore tiene nuevo campo: nodoGrafoActivo: Record<nodeId, grafoId>

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Actualizar frontend/src/stores/hubStore.ts — agregar nodoGrafoActivo:

   Ruta: ~/yeyo-os/frontend/src/stores/hubStore.ts
   MODIFICAR (agregar al store existente, no reemplazar todo):

   Agregar al interface del store:
     nodoGrafoActivo: Record<string, string>  // { nodeId: grafoId }
     setNodoGrafoActivo: (nodeId: string, grafoId: string | null) => void
     obtenerGrafoDeNodo: (nodeId: string) => string | undefined

   Agregar a la implementación del create():
     nodoGrafoActivo: {},
     setNodoGrafoActivo: (nodeId, grafoId) =>
       set((state) => ({
         nodoGrafoActivo: grafoId
           ? { ...state.nodoGrafoActivo, [nodeId]: grafoId }
           : Object.fromEntries(
               Object.entries(state.nodoGrafoActivo).filter(([k]) => k !== nodeId)
             ),
       })),
     obtenerGrafoDeNodo: (nodeId) => get().nodoGrafoActivo[nodeId],

   Si hubStore.ts no existe aún, crearlo completo:

   Ruta: ~/yeyo-os/frontend/src/stores/hubStore.ts
   Contenido:

   /**
    * YeyoOS — Hub Store
    * Zustand store para el estado del Neural Hub.
    * Actualizado en micro-fase 3.17 para soportar grafos en ejecución por nodo.
    */

   import { create } from 'zustand'

   export interface NodoHubInfo {
     id: string
     tipo: string
     label: string
     x: number
     y: number
     expandido: boolean
     activo: boolean
   }

   interface HubStore {
     nodos: NodoHubInfo[]
     nodoSeleccionado: string | null
     nodoGrafoActivo: Record<string, string>  // { nodeId: grafoId }

     // Acciones nodos
     setNodos: (nodos: NodoHubInfo[]) => void
     seleccionarNodo: (id: string | null) => void
     expandirNodo: (id: string, expandido: boolean) => void

     // Acciones grafos
     setNodoGrafoActivo: (nodeId: string, grafoId: string | null) => void
     obtenerGrafoDeNodo: (nodeId: string) => string | undefined
   }

   export const useHubStore = create<HubStore>((set, get) => ({
     nodos: [],
     nodoSeleccionado: null,
     nodoGrafoActivo: {},

     setNodos: (nodos) => set({ nodos }),
     seleccionarNodo: (id) => set({ nodoSeleccionado: id }),
     expandirNodo: (id, expandido) =>
       set((state) => ({
         nodos: state.nodos.map((n) => (n.id === id ? { ...n, expandido } : n)),
       })),

     setNodoGrafoActivo: (nodeId, grafoId) =>
       set((state) => ({
         nodoGrafoActivo: grafoId
           ? { ...state.nodoGrafoActivo, [nodeId]: grafoId }
           : Object.fromEntries(
               Object.entries(state.nodoGrafoActivo).filter(([k]) => k !== nodeId)
             ),
       })),

     obtenerGrafoDeNodo: (nodeId) => get().nodoGrafoActivo[nodeId],
   }))

2. Crear archivo frontend/src/components/hub/GraphOverlay.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/hub/GraphOverlay.tsx
   Contenido:

   /**
    * YeyoOS — GraphOverlay
    * Micro-fase 3.17 — Capa 3: Cuerpo
    *
    * Overlay semitransparente que muestra GraphExecutionView dentro
    * de un SatelliteNode expandido. Se auto-cierra al completar el grafo.
    */

   import React, { useEffect, useRef, useCallback } from 'react'
   import { GraphExecutionView } from './GraphExecutionView'
   import { useGraphStore } from '../../stores/graphStore'

   export interface GraphOverlayProps {
     grafoId: string
     onCerrar: () => void
     /** Si true, se cierra automáticamente al completar (default: true) */
     autoCerrar?: boolean
     /** Delay en ms antes de cerrar automáticamente (default: 2000) */
     autoCerrarDelay?: number
   }

   export function GraphOverlay({
     grafoId,
     onCerrar,
     autoCerrar = true,
     autoCerrarDelay = 2000,
   }: GraphOverlayProps) {
     const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
     const grafo = useGraphStore((state) => state.grafosActivos[grafoId])

     // Auto-cerrar al completar
     const handleCompletar = useCallback(
       (_grafoId: string) => {
         if (!autoCerrar) return
         timerRef.current = setTimeout(() => {
           onCerrar()
         }, autoCerrarDelay)
       },
       [autoCerrar, autoCerrarDelay, onCerrar]
     )

     useEffect(() => {
       return () => {
         if (timerRef.current) clearTimeout(timerRef.current)
       }
     }, [])

     // Click en el backdrop cierra el overlay
     const handleBackdropClick = useCallback(
       (e: React.MouseEvent) => {
         if (e.target === e.currentTarget) {
           onCerrar()
         }
       },
       [onCerrar]
     )

     return (
       <div
         data-testid="graph-overlay"
         data-grafo-id={grafoId}
         onClick={handleBackdropClick}
         style={{
           position: 'absolute',
           bottom: 0,
           left: 0,
           right: 0,
           padding: '8px',
           backgroundColor: 'rgba(0, 0, 0, 0.85)',
           borderTop: '1px solid #333333',
           borderRadius: '0 0 8px 8px',
           zIndex: 10,
           cursor: 'default',
         }}
       >
         <GraphExecutionView
           grafoId={grafoId}
           onCompletar={handleCompletar}
           style={{
             backgroundColor: 'transparent',
             border: 'none',
             padding: '4px 0',
           }}
         />
       </div>
     )
   }

3. Crear archivo frontend/src/components/hub/NodeExpandedWithGraph.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/hub/NodeExpandedWithGraph.tsx
   Contenido:

   /**
    * YeyoOS — NodeExpandedWithGraph
    * Micro-fase 3.17 — Capa 3: Cuerpo
    *
    * Wrapper para SatelliteNode expandido que integra GraphOverlay.
    * Cuando el hubStore registra un grafo activo para este nodo,
    * muestra el GraphOverlay en la parte inferior.
    */

   import React, { useCallback } from 'react'
   import { GraphOverlay } from './GraphOverlay'
   import { useHubStore } from '../../stores/hubStore'
   import { useGraphStore } from '../../stores/graphStore'

   export interface NodeExpandedWithGraphProps {
     nodeId: string
     width?: number
     height?: number
     children: React.ReactNode
     className?: string
     style?: React.CSSProperties
   }

   export function NodeExpandedWithGraph({
     nodeId,
     width = 320,
     height = 400,
     children,
     className,
     style,
   }: NodeExpandedWithGraphProps) {
     const grafoActivo = useHubStore((state) => state.nodoGrafoActivo[nodeId])
     const setNodoGrafoActivo = useHubStore((state) => state.setNodoGrafoActivo)
     const limpiarGrafo = useGraphStore((state) => state.limpiarGrafo)

     const handleCerrarOverlay = useCallback(() => {
       if (grafoActivo) {
         limpiarGrafo(grafoActivo)
       }
       setNodoGrafoActivo(nodeId, null)
     }, [grafoActivo, nodeId, setNodoGrafoActivo, limpiarGrafo])

     return (
       <div
         data-testid={`node-expanded-${nodeId}`}
         data-node-id={nodeId}
         data-tiene-grafo={!!grafoActivo}
         className={className}
         style={{
           position: 'relative',
           width,
           height,
           backgroundColor: '#111111',
           border: '1px solid #444444',
           borderRadius: '8px',
           overflow: 'hidden',
           ...style,
         }}
       >
         {/* Contenido principal del nodo */}
         <div
           style={{
             width: '100%',
             height: '100%',
             overflow: 'auto',
           }}
         >
           {children}
         </div>

         {/* Overlay del grafo — aparece solo si hay un grafo activo */}
         {grafoActivo && (
           <GraphOverlay
             grafoId={grafoActivo}
             onCerrar={handleCerrarOverlay}
             autoCerrar={true}
             autoCerrarDelay={2000}
           />
         )}
       </div>
     )
   }

4. Crear archivo frontend/src/__tests__/hub/NodeExpandedWithGraph.test.tsx:

   Ruta: ~/yeyo-os/frontend/src/__tests__/hub/NodeExpandedWithGraph.test.tsx
   Contenido:

   /**
    * Tests para NodeExpandedWithGraph y GraphOverlay — Micro-fase 3.17
    */

   import React from 'react'
   import { render, screen, act, fireEvent, waitFor } from '@testing-library/react'
   import { NodeExpandedWithGraph } from '../../components/hub/NodeExpandedWithGraph'
   import { GraphOverlay } from '../../components/hub/GraphOverlay'
   import { useHubStore } from '../../stores/hubStore'
   import { useGraphStore, GraphEventPayload } from '../../stores/graphStore'

   // Limpiar stores antes de cada test
   beforeEach(() => {
     useHubStore.getState().setNodoGrafoActivo('test-node', null)
     useGraphStore.getState().limpiarTodo()
   })

   afterEach(() => {
     jest.clearAllTimers()
   })

   const eventoBase: GraphEventPayload = {
     type: 'graph_event',
     grafo_id: 'grafo_test',
     nodo_id: 'nodo_a',
     estado: 'activo',
     progreso: 0.5,
     mensaje: 'Ejecutando...',
     timestamp: '2025-01-01T00:00:00Z',
     nodos_totales: 2,
   }

   describe('hubStore — nodoGrafoActivo', () => {
     it('inicialmente no hay grafos activos en nodos', () => {
       expect(useHubStore.getState().obtenerGrafoDeNodo('test-node')).toBeUndefined()
     })

     it('setNodoGrafoActivo asigna grafo a nodo', () => {
       act(() => {
         useHubStore.getState().setNodoGrafoActivo('test-node', 'grafo_test')
       })
       expect(useHubStore.getState().obtenerGrafoDeNodo('test-node')).toBe('grafo_test')
     })

     it('setNodoGrafoActivo con null elimina la asignación', () => {
       act(() => {
         useHubStore.getState().setNodoGrafoActivo('test-node', 'grafo_test')
         useHubStore.getState().setNodoGrafoActivo('test-node', null)
       })
       expect(useHubStore.getState().obtenerGrafoDeNodo('test-node')).toBeUndefined()
     })

     it('múltiples nodos pueden tener grafos activos simultáneamente', () => {
       act(() => {
         useHubStore.getState().setNodoGrafoActivo('node-1', 'grafo_a')
         useHubStore.getState().setNodoGrafoActivo('node-2', 'grafo_b')
       })
       expect(useHubStore.getState().obtenerGrafoDeNodo('node-1')).toBe('grafo_a')
       expect(useHubStore.getState().obtenerGrafoDeNodo('node-2')).toBe('grafo_b')
     })
   })

   describe('NodeExpandedWithGraph', () => {
     it('renderiza el contenido hijo correctamente', () => {
       render(
         <NodeExpandedWithGraph nodeId="test-node">
           <div data-testid="contenido-hijo">Contenido del nodo</div>
         </NodeExpandedWithGraph>
       )
       expect(screen.getByTestId('contenido-hijo')).toBeInTheDocument()
     })

     it('no muestra overlay cuando no hay grafo activo', () => {
       render(
         <NodeExpandedWithGraph nodeId="test-node">
           <div>Contenido</div>
         </NodeExpandedWithGraph>
       )
       expect(screen.queryByTestId('graph-overlay')).not.toBeInTheDocument()
     })

     it('muestra overlay cuando hubStore tiene grafo activo para el nodo', () => {
       act(() => {
         useGraphStore.getState().procesarEvento(eventoBase)
         useHubStore.getState().setNodoGrafoActivo('test-node', 'grafo_test')
       })
       render(
         <NodeExpandedWithGraph nodeId="test-node">
           <div>Contenido</div>
         </NodeExpandedWithGraph>
       )
       expect(screen.getByTestId('graph-overlay')).toBeInTheDocument()
     })

     it('data-tiene-grafo es true cuando hay overlay activo', () => {
       act(() => {
         useGraphStore.getState().procesarEvento(eventoBase)
         useHubStore.getState().setNodoGrafoActivo('test-node', 'grafo_test')
       })
       render(
         <NodeExpandedWithGraph nodeId="test-node">
           <div>Contenido</div>
         </NodeExpandedWithGraph>
       )
       expect(screen.getByTestId('node-expanded-test-node')).toHaveAttribute('data-tiene-grafo', 'true')
     })

     it('data-tiene-grafo es false cuando no hay overlay', () => {
       render(
         <NodeExpandedWithGraph nodeId="test-node">
           <div>Contenido</div>
         </NodeExpandedWithGraph>
       )
       expect(screen.getByTestId('node-expanded-test-node')).toHaveAttribute('data-tiene-grafo', 'false')
     })

     it('el overlay tiene el grafo-id correcto', () => {
       act(() => {
         useGraphStore.getState().procesarEvento(eventoBase)
         useHubStore.getState().setNodoGrafoActivo('test-node', 'grafo_test')
       })
       render(
         <NodeExpandedWithGraph nodeId="test-node">
           <div>Contenido</div>
         </NodeExpandedWithGraph>
       )
       expect(screen.getByTestId('graph-overlay')).toHaveAttribute('data-grafo-id', 'grafo_test')
     })
   })

   describe('GraphOverlay', () => {
     it('renderiza GraphExecutionView dentro del overlay', () => {
       act(() => {
         useGraphStore.getState().procesarEvento(eventoBase)
       })
       render(<GraphOverlay grafoId="grafo_test" onCerrar={jest.fn()} />)
       expect(screen.getByTestId('graph-overlay')).toBeInTheDocument()
     })

     it('llama onCerrar al hacer click en el backdrop', () => {
       act(() => {
         useGraphStore.getState().procesarEvento(eventoBase)
       })
       const onCerrar = jest.fn()
       render(<GraphOverlay grafoId="grafo_test" onCerrar={onCerrar} />)
       fireEvent.click(screen.getByTestId('graph-overlay'))
       expect(onCerrar).toHaveBeenCalledTimes(1)
     })

     it('auto-cierra después de delay cuando autoCerrar=true', async () => {
       jest.useFakeTimers()
       act(() => {
         useGraphStore.getState().procesarEvento({
           ...eventoBase,
           nodo_id: 'nodo_a',
           estado: 'completado',
           nodos_totales: 1,
         })
       })
       const onCerrar = jest.fn()
       render(<GraphOverlay grafoId="grafo_test" onCerrar={onCerrar} autoCerrarDelay={500} />)
       act(() => {
         jest.advanceTimersByTime(600)
       })
       expect(onCerrar).toHaveBeenCalledTimes(1)
       jest.useRealTimers()
     })

     it('NO auto-cierra cuando autoCerrar=false', async () => {
       jest.useFakeTimers()
       act(() => {
         useGraphStore.getState().procesarEvento({
           ...eventoBase,
           nodo_id: 'nodo_a',
           estado: 'completado',
           nodos_totales: 1,
         })
       })
       const onCerrar = jest.fn()
       render(<GraphOverlay grafoId="grafo_test" onCerrar={onCerrar} autoCerrar={false} />)
       act(() => {
         jest.advanceTimersByTime(5000)
       })
       expect(onCerrar).not.toHaveBeenCalled()
       jest.useRealTimers()
     })
   })

5. Ejecutar tests:
   cd ~/yeyo-os/frontend
   npm test -- --testPathPattern="NodeExpandedWithGraph|GraphOverlay" --watchAll=false

VERIFICAR:
- [ ] hubStore tiene campo nodoGrafoActivo y métodos setNodoGrafoActivo/obtenerGrafoDeNodo
- [ ] NodeExpandedWithGraph renderiza hijos correctamente
- [ ] Overlay NO aparece cuando no hay grafo activo en el nodo
- [ ] Overlay aparece cuando hubStore.nodoGrafoActivo[nodeId] tiene valor
- [ ] Click en backdrop del overlay llama onCerrar
- [ ] Auto-cierre funciona con el delay configurado
- [ ] data-tiene-grafo refleja correctamente si hay overlay activo
- [ ] GraphOverlay pasa grafo-id correcto al data-attribute
- [ ] TODOS los tests pasan

SI FALLA:
- hubStore no existe: crear el archivo completo como se describe en el paso 1
- Error de import: verificar que GraphOverlay importa de ../../stores correctamente
- Timers en tests: usar jest.useFakeTimers() y jest.advanceTimersByTime()
- useHubStore ya existe con otra estructura: solo AGREGAR los campos nuevos, no reemplazar

NO HACER:
- No modificar SatelliteNode.tsx real si es complejo — NodeExpandedWithGraph es un wrapper independiente
- No conectar con WebSocket real — usar graphStore mock via procesarEvento()
- No implementar animaciones de entrada/salida del overlay (eso es un nice-to-have futuro)
- No crear layout de grafo tipo DAG complejo — el LinearFlow de 3.16 es suficiente

GATE: Al recibir evento de grafo activo (setNodoGrafoActivo + procesarEvento), el NodeExpandedWithGraph muestra GraphOverlay con el mini-grafo animado. Click en backdrop cierra el overlay. Auto-cierre funciona. Todos los tests pasan.
```
