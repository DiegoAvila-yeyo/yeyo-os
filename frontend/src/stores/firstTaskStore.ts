/**
 * YeyoOS — firstTaskStore
 * Micro-fase 3.22 — Capa 3: Cuerpo
 *
 * Store Zustand que gestiona la secuencia de primera tarea:
 * idle → materializing → drawing_line → processing → scanning → complete
 */

import { create } from 'zustand'

export type FirstTaskPhase =
  | 'idle'
  | 'materializing'
  | 'drawing_line'
  | 'processing'
  | 'scanning'
  | 'complete'

export type NodeType = 'image' | 'video' | 'code' | 'text' | 'audio' | 'generic'

export interface FirstTaskResult {
  type: NodeType
  imageUrl?: string
  textContent?: string
  title: string
}

export const NODE_COLORS: Record<NodeType, string> = {
  image:   '#A855F7',
  video:   '#3B82F6',
  code:    '#10B981',
  text:    '#F59E0B',
  audio:   '#EC4899',
  generic: '#60A5FA',
}

const MOCK_RESULTS: Record<NodeType, FirstTaskResult> = {
  image: {
    type: 'image',
    title: 'Imagen generada',
    imageUrl: 'https://picsum.photos/320/200?random=42',
  },
  video: {
    type: 'video',
    title: 'Video procesado',
    textContent: 'Video clip generado: 1080p, 30fps, 15 segundos.\nListo para exportar.',
  },
  code: {
    type: 'code',
    title: 'Código generado',
    textContent: 'def generar_atardecer():\n    paleta = ["#FF6B35", "#F7C59F", "#EFEFD0"]\n    return pintar(paleta)\n\nresultado = generar_atardecer()',
  },
  text: {
    type: 'text',
    title: 'Texto generado',
    textContent: 'YeyoOS es un sistema operativo AI-nativo con arquitectura hexagonal. Diseñado para potenciar tu creatividad con inteligencia artificial integrada.',
  },
  audio: {
    type: 'audio',
    title: 'Audio generado',
    textContent: 'Pista de audio sintetizada.\nDuración: 30 segundos\nFormato: WAV 44.1kHz estéreo\nListo para reproducir.',
  },
  generic: {
    type: 'generic',
    title: 'Tarea completada',
    textContent: 'La tarea fue procesada exitosamente por YeyoOS.',
  },
}

/** Detecta el tipo de nodo según palabras clave en la tarea. */
export function detectarTipoNodo(tarea: string): NodeType {
  const t = tarea.toLowerCase()
  if (/imagen|foto|diseño|ilustra|pinta|dibuja|render|genera.*imagen|fotogr/.test(t)) return 'image'
  if (/video|clip|reel|película|animación|graba|screencast/.test(t)) return 'video'
  if (/código|code|programa|script|función|clase|api|endpoint|debug/.test(t)) return 'code'
  if (/audio|música|canción|sonido|podcast|voz|beat|melodía/.test(t)) return 'audio'
  if (/texto|redacta|escribe|resume|traduce|corrije|carta|email|artículo/.test(t)) return 'text'
  return 'generic'
}

export interface FirstTaskStore {
  phase: FirstTaskPhase
  taskText: string
  nodeType: NodeType
  nodeColor: string
  result: FirstTaskResult | null
  iniciarPrimeraTarea: (tarea: string, tipoNodo?: NodeType) => void
  setPhase: (phase: FirstTaskPhase) => void
  setResult: (result: FirstTaskResult) => void
  reset: () => void
}

export const useFirstTaskStore = create<FirstTaskStore>((set, get) => ({
  phase: 'idle',
  taskText: '',
  nodeType: 'generic',
  nodeColor: '#60A5FA',
  result: null,

  iniciarPrimeraTarea: (tarea: string, tipoNodo?: NodeType) => {
    const tipo = tipoNodo ?? detectarTipoNodo(tarea)
    set({
      phase: 'materializing',
      taskText: tarea,
      nodeType: tipo,
      nodeColor: NODE_COLORS[tipo],
      result: null,
    })

    // Secuencia temporal con timeouts
    setTimeout(() => set({ phase: 'drawing_line' }), 800)
    setTimeout(() => set({ phase: 'processing' }), 1200)
    setTimeout(() => {
      set({ phase: 'scanning', result: MOCK_RESULTS[get().nodeType] })
    }, 3200)
    setTimeout(() => set({ phase: 'complete' }), 3800)
  },

  setPhase: (phase) => set({ phase }),
  setResult: (result) => set({ result }),
  reset: () => set({ phase: 'idle', taskText: '', nodeType: 'generic', nodeColor: '#60A5FA', result: null }),
}))
