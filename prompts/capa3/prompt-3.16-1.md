## ═══════════════════════════════════════
## MICRO-FASE 3.16 — GraphExecutionView
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 3.16-1 [VSCODE] — Componente React/PixiJS para mini-grafo animado en tiempo real

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 3.16 de Capa 3 (Cuerpo): crear el componente GraphExecutionView que muestra un mini-grafo animado con los estados de ejecución de un YeyoGrafo dentro del Hub.

CONTEXTO:
- Capas 0-3 completadas hasta micro-fase 3.15 (Integration Test Capa 3)
- El backend (Capa 4) tiene un YeyoOrquestador propio que emite eventos WebSocket cuando ejecuta grafos
- Evento WebSocket: {type: "graph_event", grafo_id, nodo_id, estado, progreso, mensaje, timestamp}
- Esta micro-fase es UI pura — puede mockearse antes de que el backend esté listo
- Store Zustand existente en frontend/src/stores/ (hubStore, chatStore, uiStore, systemStore)
- WebSocket existente en frontend/src/stores/wsStore.ts conectado al backend

Estados de nodo del grafo:
  - pendiente: #555555 — sin animación
  - activo: #F5A623 — pulso continuo (scala de 1.0 a 1.15 y vuelve, 800ms)
  - completado: #4CAF50 — flash verde breve al completar, luego estático
  - error: #F44336 — shake lateral (±3px, 400ms)
  - saltado: #777777 — sin animación, opacidad 0.6

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear directorio si no existe:
   mkdir -p frontend/src/stores
   mkdir -p frontend/src/components/hub
   mkdir -p frontend/src/__tests__/hub

2. Crear archivo frontend/src/stores/graphStore.ts:

   Ruta: ~/yeyo-os/frontend/src/stores/graphStore.ts
   Contenido:

   /**
    * YeyoOS — Graph Execution Store
    * Micro-fase 3.16 — Capa 3: Cuerpo
    *
    * Estado Zustand para visualización de grafos en ejecución.
    * Consume eventos WebSocket {type: "graph_event"} del backend.
    */

   import { create } from 'zustand'

   export type EstadoNodoGrafo = 'pendiente' | 'activo' | 'completado' | 'error' | 'saltado'

   export interface NodoGrafoVisual {
     id: string
     etiqueta: string
     estado: EstadoNodoGrafo
     progreso: number      // 0.0 - 1.0
     mensaje: string
     timestamp: string | null
   }

   export interface ConexionGrafo {
     desde: string
     hasta: string
   }

   export interface GrafoEnEjecucion {
     grafoId: string
     nodos: NodoGrafoVisual[]
     conexiones: ConexionGrafo[]
     progreso: number       // progreso global 0.0 - 1.0
     activo: boolean
     completado: boolean
     iniciadoEn: string
   }

   export interface GraphEventPayload {
     type: 'graph_event'
     grafo_id: string
     nodo_id: string
     estado: EstadoNodoGrafo
     progreso: number
     mensaje: string
     timestamp: string
     nodos_totales?: number
     conexiones?: Array<{ desde: string; hasta: string }>
   }

   interface GraphStore {
     grafosActivos: Record<string, GrafoEnEjecucion>
     grafoSeleccionado: string | null

     // Acciones
     procesarEvento: (evento: GraphEventPayload) => void
     seleccionarGrafo: (grafoId: string | null) => void
     limpiarGrafo: (grafoId: string) => void
     limpiarTodo: () => void

     // Getters
     obtenerGrafo: (grafoId: string) => GrafoEnEjecucion | undefined
     hayGrafosActivos: () => boolean
   }

   export const useGraphStore = create<GraphStore>((set, get) => ({
     grafosActivos: {},
     grafoSeleccionado: null,

     procesarEvento: (evento: GraphEventPayload) => {
       set((state) => {
         const { grafo_id, nodo_id, estado, progreso, mensaje, timestamp, conexiones } = evento
         const grafosActivos = { ...state.grafosActivos }

         if (!grafosActivos[grafo_id]) {
           // Inicializar nuevo grafo
           grafosActivos[grafo_id] = {
             grafoId: grafo_id,
             nodos: [],
             conexiones: conexiones ?? [],
             progreso: 0,
             activo: true,
             completado: false,
             iniciadoEn: timestamp,
           }
         }

         const grafo = { ...grafosActivos[grafo_id] }
         const nodos = [...grafo.nodos]

         // Si llegaron conexiones, actualizarlas
         if (conexiones && conexiones.length > 0) {
           grafo.conexiones = conexiones
         }

         // Buscar o crear el nodo visual
         const idxNodo = nodos.findIndex((n) => n.id === nodo_id)
         const nodoActualizado: NodoGrafoVisual = {
           id: nodo_id,
           etiqueta: nodo_id.replace(/_/g, ' '),
           estado,
           progreso,
           mensaje,
           timestamp,
         }

         if (idxNodo >= 0) {
           nodos[idxNodo] = nodoActualizado
         } else {
           nodos.push(nodoActualizado)
         }

         // Calcular progreso global
         const nodosCompletados = nodos.filter(
           (n) => n.estado === 'completado' || n.estado === 'saltado'
         ).length
         const totalNodos = Math.max(nodos.length, evento.nodos_totales ?? nodos.length)
         const progresoGlobal = totalNodos > 0 ? nodosCompletados / totalNodos : progreso

         const hayError = nodos.some((n) => n.estado === 'error')
         const todosTerminados =
           nodos.length >= (evento.nodos_totales ?? nodos.length) &&
           nodos.every(
             (n) => n.estado === 'completado' || n.estado === 'saltado' || n.estado === 'error'
           )

         grafo.nodos = nodos
         grafo.progreso = progresoGlobal
         grafo.activo = !todosTerminados && !hayError
         grafo.completado = todosTerminados

         grafosActivos[grafo_id] = grafo

         return { grafosActivos }
       })
     },

     seleccionarGrafo: (grafoId) => set({ grafoSeleccionado: grafoId }),

     limpiarGrafo: (grafoId) =>
       set((state) => {
         const grafosActivos = { ...state.grafosActivos }
         delete grafosActivos[grafoId]
         return {
           grafosActivos,
           grafoSeleccionado:
             state.grafoSeleccionado === grafoId ? null : state.grafoSeleccionado,
         }
       }),

     limpiarTodo: () => set({ grafosActivos: {}, grafoSeleccionado: null }),

     obtenerGrafo: (grafoId) => get().grafosActivos[grafoId],

     hayGrafosActivos: () =>
       Object.values(get().grafosActivos).some((g) => g.activo),
   }))

3. Crear archivo frontend/src/components/hub/GraphExecutionView.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/hub/GraphExecutionView.tsx
   Contenido:

   /**
    * YeyoOS — GraphExecutionView
    * Micro-fase 3.16 — Capa 3: Cuerpo
    *
    * Mini-grafo animado que muestra el estado de ejecución de un YeyoGrafo.
    * Renderiza nodos con estados visuales animados y conexiones entre ellos.
    */

   import React, { useEffect, useRef, useCallback } from 'react'
   import { useGraphStore, GrafoEnEjecucion, EstadoNodoGrafo, NodoGrafoVisual } from '../../stores/graphStore'

   // ─── Constantes de color por estado ───────────────────────────────────────
   export const COLORES_ESTADO: Record<EstadoNodoGrafo, string> = {
     pendiente: '#555555',
     activo: '#F5A623',
     completado: '#4CAF50',
     error: '#F44336',
     saltado: '#777777',
   }

   const OPACIDAD_ESTADO: Record<EstadoNodoGrafo, number> = {
     pendiente: 1,
     activo: 1,
     completado: 1,
     error: 1,
     saltado: 0.6,
   }

   // ─── Subcomponente: nodo individual ───────────────────────────────────────
   interface NodoVisualProps {
     nodo: NodoGrafoVisual
   }

   function NodoVisual({ nodo }: NodoVisualProps) {
     const nodeRef = useRef<HTMLDivElement>(null)
     const animFrameRef = useRef<number | null>(null)
     const startTimeRef = useRef<number>(Date.now())

     const color = COLORES_ESTADO[nodo.estado]
     const opacidad = OPACIDAD_ESTADO[nodo.estado]

     // Animación de pulso para nodo activo
     useEffect(() => {
       if (nodo.estado !== 'activo') {
         if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current)
         if (nodeRef.current) {
           nodeRef.current.style.transform = 'scale(1)'
           nodeRef.current.style.boxShadow = `0 0 6px ${color}55`
         }
         return
       }

       startTimeRef.current = Date.now()
       const animate = () => {
         if (!nodeRef.current) return
         const elapsed = Date.now() - startTimeRef.current
         const t = (Math.sin((elapsed / 800) * Math.PI * 2) + 1) / 2 // 0-1
         const scale = 1 + t * 0.15
         const glowSize = 6 + t * 12
         nodeRef.current.style.transform = `scale(${scale})`
         nodeRef.current.style.boxShadow = `0 0 ${glowSize}px ${color}99`
         animFrameRef.current = requestAnimationFrame(animate)
       }
       animFrameRef.current = requestAnimationFrame(animate)

       return () => {
         if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current)
       }
     }, [nodo.estado, color])

     // Animación de shake para error
     useEffect(() => {
       if (nodo.estado !== 'error' || !nodeRef.current) return
       const el = nodeRef.current
       let t = 0
       const duration = 400
       const start = Date.now()
       const shake = () => {
         const elapsed = Date.now() - start
         if (elapsed >= duration) {
           el.style.transform = 'translateX(0)'
           return
         }
         const progress = elapsed / duration
         const x = Math.sin(progress * Math.PI * 6) * 3 * (1 - progress)
         el.style.transform = `translateX(${x}px)`
         requestAnimationFrame(shake)
       }
       requestAnimationFrame(shake)
     }, [nodo.estado])

     return (
       <div
         ref={nodeRef}
         data-testid={`nodo-grafo-${nodo.id}`}
         data-estado={nodo.estado}
         style={{
           display: 'flex',
           flexDirection: 'column',
           alignItems: 'center',
           gap: '4px',
           opacity: opacidad,
           transition: 'opacity 0.3s ease',
         }}
       >
         {/* Círculo del nodo */}
         <div
           style={{
             width: '32px',
             height: '32px',
             borderRadius: '50%',
             backgroundColor: color,
             border: `2px solid ${color}`,
             display: 'flex',
             alignItems: 'center',
             justifyContent: 'center',
             fontSize: '14px',
             transition: 'background-color 0.3s ease',
           }}
         >
           {nodo.estado === 'completado' && '✓'}
           {nodo.estado === 'error' && '✗'}
           {nodo.estado === 'saltado' && '↷'}
           {(nodo.estado === 'pendiente' || nodo.estado === 'activo') && '·'}
         </div>

         {/* Etiqueta */}
         <span
           style={{
             fontSize: '10px',
             color: color,
             maxWidth: '64px',
             textAlign: 'center',
             overflow: 'hidden',
             textOverflow: 'ellipsis',
             whiteSpace: 'nowrap',
             fontFamily: 'monospace',
           }}
         >
           {nodo.etiqueta}
         </span>

         {/* Mensaje de estado si está activo */}
         {nodo.estado === 'activo' && nodo.mensaje && (
           <span
             style={{
               fontSize: '9px',
               color: '#aaaaaa',
               maxWidth: '80px',
               textAlign: 'center',
               overflow: 'hidden',
               textOverflow: 'ellipsis',
               whiteSpace: 'nowrap',
             }}
           >
             {nodo.mensaje}
           </span>
         )}
       </div>
     )
   }

   // ─── Subcomponente: línea de conexión ─────────────────────────────────────
   interface ConexionVisualProps {
     desdeEstado: EstadoNodoGrafo
     hastaEstado: EstadoNodoGrafo
   }

   function ConexionVisual({ desdeEstado, hastaEstado }: ConexionVisualProps) {
     const color =
       desdeEstado === 'completado'
         ? '#4CAF50'
         : desdeEstado === 'activo'
         ? '#F5A623'
         : desdeEstado === 'error'
         ? '#F44336'
         : '#444444'

     return (
       <div
         data-testid="conexion-grafo"
         style={{
           display: 'flex',
           alignItems: 'center',
           padding: '0 4px',
           color,
           fontSize: '16px',
           transition: 'color 0.3s ease',
           marginTop: '-8px', // alinear con el centro del nodo
         }}
       >
         →
       </div>
     )
   }

   // ─── Subcomponente: barra de progreso ─────────────────────────────────────
   interface BarraProgresoProps {
     progreso: number   // 0.0 - 1.0
     completado: boolean
     hayError: boolean
   }

   function BarraProgreso({ progreso, completado, hayError }: BarraProgresoProps) {
     const color = hayError ? '#F44336' : completado ? '#4CAF50' : '#F5A623'
     const porcentaje = Math.round(progreso * 100)

     return (
       <div style={{ width: '100%' }}>
         <div
           style={{
             height: '3px',
             backgroundColor: '#333333',
             borderRadius: '2px',
             overflow: 'hidden',
           }}
         >
           <div
             data-testid="barra-progreso"
             style={{
               height: '100%',
               width: `${porcentaje}%`,
               backgroundColor: color,
               borderRadius: '2px',
               transition: 'width 0.4s ease, background-color 0.3s ease',
             }}
           />
         </div>
         <div
           style={{
             fontSize: '9px',
             color: '#888888',
             textAlign: 'right',
             marginTop: '2px',
             fontFamily: 'monospace',
           }}
         >
           {completado
             ? hayError
               ? 'error'
               : 'completado'
             : `${porcentaje}%`}
         </div>
       </div>
     )
   }

   // ─── Componente principal ──────────────────────────────────────────────────
   export interface GraphExecutionViewProps {
     grafoId: string
     onCompletar?: (grafoId: string) => void
     onError?: (grafoId: string, error: string) => void
     className?: string
     style?: React.CSSProperties
   }

   export function GraphExecutionView({
     grafoId,
     onCompletar,
     onError,
     className,
     style,
   }: GraphExecutionViewProps) {
     const grafo = useGraphStore((state) => state.grafosActivos[grafoId])

     // Llamar callbacks cuando el grafo termina
     useEffect(() => {
       if (!grafo) return
       if (grafo.completado && onCompletar) {
         const hayError = grafo.nodos.some((n) => n.estado === 'error')
         if (!hayError) onCompletar(grafoId)
       }
       if (grafo.nodos.some((n) => n.estado === 'error') && onError) {
         const nodoConError = grafo.nodos.find((n) => n.estado === 'error')
         onError(grafoId, nodoConError?.mensaje ?? 'Error desconocido')
       }
     }, [grafo?.completado, grafo?.nodos, grafoId, onCompletar, onError])

     if (!grafo) {
       return (
         <div
           data-testid="graph-execution-view-vacio"
           style={{
             color: '#555555',
             fontSize: '11px',
             fontFamily: 'monospace',
             padding: '8px',
             ...style,
           }}
           className={className}
         >
           Esperando grafo...
         </div>
       )
     }

     const hayError = grafo.nodos.some((n) => n.estado === 'error')

     return (
       <div
         data-testid="graph-execution-view"
         data-grafo-id={grafoId}
         className={className}
         style={{
           backgroundColor: '#1a1a1a',
           border: '1px solid #333333',
           borderRadius: '8px',
           padding: '12px',
           display: 'flex',
           flexDirection: 'column',
           gap: '10px',
           minWidth: '200px',
           maxWidth: '400px',
           ...style,
         }}
       >
         {/* Header */}
         <div
           style={{
             display: 'flex',
             alignItems: 'center',
             justifyContent: 'space-between',
             fontSize: '11px',
             fontFamily: 'monospace',
           }}
         >
           <span style={{ color: '#888888' }}>grafo:</span>
           <span style={{ color: '#cccccc' }}>{grafoId.replace(/_/g, ' ')}</span>
         </div>

         {/* Nodos y conexiones */}
         <div
           data-testid="nodos-container"
           style={{
             display: 'flex',
             flexDirection: 'row',
             alignItems: 'flex-start',
             justifyContent: 'center',
             gap: '2px',
             flexWrap: 'wrap',
             minHeight: '60px',
           }}
         >
           {grafo.nodos.map((nodo, idx) => (
             <React.Fragment key={nodo.id}>
               <NodoVisual nodo={nodo} />
               {idx < grafo.nodos.length - 1 && grafo.conexiones.length === 0 && (
                 <ConexionVisual
                   desdeEstado={nodo.estado}
                   hastaEstado={grafo.nodos[idx + 1]?.estado ?? 'pendiente'}
                 />
               )}
               {grafo.conexiones
                 .filter((c) => c.desde === nodo.id)
                 .map((conexion) => {
                   const nodoHasta = grafo.nodos.find((n) => n.id === conexion.hasta)
                   if (!nodoHasta) return null
                   return (
                     <ConexionVisual
                       key={`${conexion.desde}-${conexion.hasta}`}
                       desdeEstado={nodo.estado}
                       hastaEstado={nodoHasta.estado}
                     />
                   )
                 })}
             </React.Fragment>
           ))}
         </div>

         {/* Barra de progreso */}
         <BarraProgreso
           progreso={grafo.progreso}
           completado={grafo.completado}
           hayError={hayError}
         />

         {/* Nodo activo actual */}
         {grafo.activo && (
           <div
             data-testid="nodo-activo-label"
             style={{
               fontSize: '10px',
               color: '#F5A623',
               fontFamily: 'monospace',
               textAlign: 'center',
             }}
           >
             {grafo.nodos.find((n) => n.estado === 'activo')?.mensaje ?? '...'}
           </div>
         )}
       </div>
     )
   }

   // ─── Hook para conectar WebSocket al graphStore ────────────────────────────
   export function useGraphWebSocket(wsInstance: { onMessage?: (handler: (msg: unknown) => void) => void } | null) {
     const procesarEvento = useGraphStore((state) => state.procesarEvento)

     useEffect(() => {
       if (!wsInstance?.onMessage) return

       wsInstance.onMessage((mensaje: unknown) => {
         if (
           mensaje &&
           typeof mensaje === 'object' &&
           (mensaje as Record<string, unknown>).type === 'graph_event'
         ) {
           procesarEvento(mensaje as Parameters<typeof procesarEvento>[0])
         }
       })
     }, [wsInstance, procesarEvento])
   }

4. Crear archivo frontend/src/__tests__/hub/GraphExecutionView.test.tsx:

   Ruta: ~/yeyo-os/frontend/src/__tests__/hub/GraphExecutionView.test.tsx
   Contenido:

   /**
    * Tests para GraphExecutionView y graphStore — Micro-fase 3.16
    */

   import React from 'react'
   import { render, screen, act } from '@testing-library/react'
   import { GraphExecutionView } from '../../components/hub/GraphExecutionView'
   import { useGraphStore, GraphEventPayload } from '../../stores/graphStore'

   // Resetear store antes de cada test
   beforeEach(() => {
     useGraphStore.getState().limpiarTodo()
   })

   const eventoBase: GraphEventPayload = {
     type: 'graph_event',
     grafo_id: 'test_grafo',
     nodo_id: 'nodo_a',
     estado: 'activo',
     progreso: 0.33,
     mensaje: 'Procesando...',
     timestamp: '2025-01-01T00:00:00Z',
     nodos_totales: 3,
   }

   describe('graphStore', () => {
     it('inicialmente no tiene grafos activos', () => {
       const store = useGraphStore.getState()
       expect(Object.keys(store.grafosActivos)).toHaveLength(0)
       expect(store.hayGrafosActivos()).toBe(false)
     })

     it('procesa evento y crea grafo nuevo', () => {
       act(() => {
         useGraphStore.getState().procesarEvento(eventoBase)
       })
       const grafo = useGraphStore.getState().grafosActivos['test_grafo']
       expect(grafo).toBeDefined()
       expect(grafo.grafoId).toBe('test_grafo')
       expect(grafo.nodos).toHaveLength(1)
       expect(grafo.nodos[0].id).toBe('nodo_a')
       expect(grafo.nodos[0].estado).toBe('activo')
     })

     it('actualiza estado de nodo existente', () => {
       act(() => {
         useGraphStore.getState().procesarEvento(eventoBase)
         useGraphStore.getState().procesarEvento({
           ...eventoBase,
           estado: 'completado',
           progreso: 1,
           mensaje: 'Listo',
         })
       })
       const grafo = useGraphStore.getState().grafosActivos['test_grafo']
       expect(grafo.nodos[0].estado).toBe('completado')
       expect(grafo.nodos[0].mensaje).toBe('Listo')
     })

     it('agrega múltiples nodos al grafo', () => {
       act(() => {
         useGraphStore.getState().procesarEvento({ ...eventoBase, nodo_id: 'nodo_a', estado: 'completado' })
         useGraphStore.getState().procesarEvento({ ...eventoBase, nodo_id: 'nodo_b', estado: 'activo' })
         useGraphStore.getState().procesarEvento({ ...eventoBase, nodo_id: 'nodo_c', estado: 'pendiente' })
       })
       const grafo = useGraphStore.getState().grafosActivos['test_grafo']
       expect(grafo.nodos).toHaveLength(3)
     })

     it('calcula progreso global correctamente', () => {
       act(() => {
         useGraphStore.getState().procesarEvento({ ...eventoBase, nodo_id: 'nodo_a', estado: 'completado', nodos_totales: 3 })
         useGraphStore.getState().procesarEvento({ ...eventoBase, nodo_id: 'nodo_b', estado: 'saltado', nodos_totales: 3 })
         useGraphStore.getState().procesarEvento({ ...eventoBase, nodo_id: 'nodo_c', estado: 'activo', nodos_totales: 3 })
       })
       const grafo = useGraphStore.getState().grafosActivos['test_grafo']
       // 2 de 3 terminados = 0.666...
       expect(grafo.progreso).toBeCloseTo(0.666, 1)
     })

     it('marca grafo como completado cuando todos los nodos terminan', () => {
       act(() => {
         useGraphStore.getState().procesarEvento({ ...eventoBase, nodo_id: 'nodo_a', estado: 'completado', nodos_totales: 2 })
         useGraphStore.getState().procesarEvento({ ...eventoBase, nodo_id: 'nodo_b', estado: 'completado', nodos_totales: 2 })
       })
       const grafo = useGraphStore.getState().grafosActivos['test_grafo']
       expect(grafo.completado).toBe(true)
       expect(grafo.activo).toBe(false)
     })

     it('limpia grafo correctamente', () => {
       act(() => {
         useGraphStore.getState().procesarEvento(eventoBase)
         useGraphStore.getState().limpiarGrafo('test_grafo')
       })
       expect(useGraphStore.getState().grafosActivos['test_grafo']).toBeUndefined()
     })

     it('limpiaTodo elimina todos los grafos', () => {
       act(() => {
         useGraphStore.getState().procesarEvento(eventoBase)
         useGraphStore.getState().procesarEvento({ ...eventoBase, grafo_id: 'otro_grafo' })
         useGraphStore.getState().limpiarTodo()
       })
       expect(Object.keys(useGraphStore.getState().grafosActivos)).toHaveLength(0)
     })

     it('hayGrafosActivos retorna true cuando hay un grafo activo', () => {
       act(() => {
         useGraphStore.getState().procesarEvento(eventoBase)
       })
       expect(useGraphStore.getState().hayGrafosActivos()).toBe(true)
     })
   })

   describe('GraphExecutionView', () => {
     it('muestra mensaje de espera cuando no hay grafo', () => {
       render(<GraphExecutionView grafoId="no_existe" />)
       expect(screen.getByTestId('graph-execution-view-vacio')).toBeInTheDocument()
     })

     it('muestra el componente cuando hay grafo activo', () => {
       act(() => {
         useGraphStore.getState().procesarEvento(eventoBase)
       })
       render(<GraphExecutionView grafoId="test_grafo" />)
       expect(screen.getByTestId('graph-execution-view')).toBeInTheDocument()
     })

     it('muestra los nodos del grafo', () => {
       act(() => {
         useGraphStore.getState().procesarEvento({ ...eventoBase, nodo_id: 'nodo_a', estado: 'completado' })
         useGraphStore.getState().procesarEvento({ ...eventoBase, nodo_id: 'nodo_b', estado: 'activo' })
       })
       render(<GraphExecutionView grafoId="test_grafo" />)
       expect(screen.getByTestId('nodo-grafo-nodo_a')).toBeInTheDocument()
       expect(screen.getByTestId('nodo-grafo-nodo_b')).toBeInTheDocument()
     })

     it('nodo activo tiene atributo data-estado correcto', () => {
       act(() => {
         useGraphStore.getState().procesarEvento({ ...eventoBase, nodo_id: 'nodo_a', estado: 'activo' })
       })
       render(<GraphExecutionView grafoId="test_grafo" />)
       const nodo = screen.getByTestId('nodo-grafo-nodo_a')
       expect(nodo).toHaveAttribute('data-estado', 'activo')
     })

     it('nodo completado tiene atributo data-estado correcto', () => {
       act(() => {
         useGraphStore.getState().procesarEvento({ ...eventoBase, nodo_id: 'nodo_a', estado: 'completado' })
       })
       render(<GraphExecutionView grafoId="test_grafo" />)
       const nodo = screen.getByTestId('nodo-grafo-nodo_a')
       expect(nodo).toHaveAttribute('data-estado', 'completado')
     })

     it('muestra barra de progreso', () => {
       act(() => {
         useGraphStore.getState().procesarEvento({ ...eventoBase, progreso: 0.5 })
       })
       render(<GraphExecutionView grafoId="test_grafo" />)
       expect(screen.getByTestId('barra-progreso')).toBeInTheDocument()
     })

     it('llama onCompletar cuando el grafo completa', () => {
       const onCompletar = jest.fn()
       act(() => {
         useGraphStore.getState().procesarEvento({ ...eventoBase, nodo_id: 'nodo_a', estado: 'completado', nodos_totales: 1 })
       })
       render(<GraphExecutionView grafoId="test_grafo" onCompletar={onCompletar} />)
       expect(onCompletar).toHaveBeenCalledWith('test_grafo')
     })

     it('llama onError cuando hay un nodo con error', () => {
       const onError = jest.fn()
       act(() => {
         useGraphStore.getState().procesarEvento({ ...eventoBase, nodo_id: 'nodo_a', estado: 'error', mensaje: 'fallo grave' })
       })
       render(<GraphExecutionView grafoId="test_grafo" onError={onError} />)
       expect(onError).toHaveBeenCalledWith('test_grafo', 'fallo grave')
     })

     it('el data-grafo-id coincide con el grafoId prop', () => {
       act(() => {
         useGraphStore.getState().procesarEvento(eventoBase)
       })
       render(<GraphExecutionView grafoId="test_grafo" />)
       expect(screen.getByTestId('graph-execution-view')).toHaveAttribute('data-grafo-id', 'test_grafo')
     })
   })

5. Ejecutar tests:
   cd ~/yeyo-os/frontend
   npm test -- --testPathPattern="GraphExecutionView" --watchAll=false

VERIFICAR:
- [ ] Archivo frontend/src/stores/graphStore.ts existe con useGraphStore
- [ ] Archivo frontend/src/components/hub/GraphExecutionView.tsx existe
- [ ] graphStore.procesarEvento() crea y actualiza grafos correctamente
- [ ] GraphExecutionView renderiza nodos con data-estado correcto
- [ ] Barra de progreso muestra porcentaje correcto
- [ ] onCompletar se llama cuando todos los nodos terminan
- [ ] onError se llama cuando un nodo tiene estado "error"
- [ ] Colores correctos: pendiente=#555, activo=#F5A623, completado=#4CAF50, error=#F44336, saltado=#777
- [ ] TODOS los tests pasan

SI FALLA:
- @testing-library/react no instalado: npm install --save-dev @testing-library/react @testing-library/jest-dom
- zustand no instalado: npm install zustand
- jest no configurado: verificar jest.config.js en frontend/
- Error de módulo: verificar que las rutas de import usan ../../ correctamente

NO HACER:
- No conectar con WebSocket real aún — eso es micro-fase 3.17
- No integrar con SatelliteNode aún — eso es micro-fase 3.17
- No usar PixiJS directamente — este componente usa React puro para simplicidad
- No implementar layout de grafo complejo (DAG visual) — flujo lineal es suficiente para 3.16

GATE: GraphExecutionView muestra nodos con estados animados correctamente, graphStore gestiona eventos de grafo, onCompletar y onError se invocan en momentos correctos, todos los tests pasan.
```
