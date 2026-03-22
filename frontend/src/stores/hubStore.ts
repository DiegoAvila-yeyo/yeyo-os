/**
 * YeyoOS — Hub Store
 * Zustand store para el estado del Neural Hub.
 * Creado en micro-fase 3.17 para soportar grafos en ejecución por nodo.
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
  nodoGrafoActivo: Record<string, string> // { nodeId: grafoId }

  // Acciones nodos
  setNodos: (nodos: NodoHubInfo[]) => void
  seleccionarNodo: (id: string | null) => void
  expandirNodo: (id: string, expandido: boolean) => void

  // Acciones grafos
  setNodoGrafoActivo: (nodeId: string, grafoId: string | null) => void
  obtenerGrafoDeNodo: (nodeId: string) => string | undefined

  // Posiciones libres (3.19)
  posicionesNodos: Record<string, { x: number; y: number }>
  setPosicionNodo: (nodeId: string, x: number, y: number) => void
  cargarPosicionesDesdeStorage: (userId: string) => void
  guardarPosicionesEnStorage: (userId: string) => void

  // Nodos instalados (3.19)
  nodosInstalados: string[]
  setNodosInstalados: (ids: string[]) => void
  esNodoInstalado: (id: string) => boolean

  // Estado de pipeline activo (3.19)
  pipelineActivo: boolean
  nodosEnPipeline: string[]
  setPipelineActivo: (activo: boolean, nodos?: string[]) => void
}

export const useHubStore = create<HubStore>((set, get) => ({
  nodos: [],
  nodoSeleccionado: null,
  nodoGrafoActivo: {},
  posicionesNodos: {},
  nodosInstalados: [],
  pipelineActivo: false,
  nodosEnPipeline: [],

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

  // Posiciones libres
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
    } catch {
      // ignorar errores de storage
    }
  },
  guardarPosicionesEnStorage: (userId) => {
    try {
      const key = `yeyo_hub_positions_${userId}`
      localStorage.setItem(key, JSON.stringify(get().posicionesNodos))
    } catch {
      // ignorar errores de storage
    }
  },

  // Nodos instalados
  setNodosInstalados: (ids) => set({ nodosInstalados: ids }),
  esNodoInstalado: (id) => get().nodosInstalados.includes(id),

  // Pipeline activo
  setPipelineActivo: (activo, nodos = []) =>
    set({ pipelineActivo: activo, nodosEnPipeline: nodos }),
}))
