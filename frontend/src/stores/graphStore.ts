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
