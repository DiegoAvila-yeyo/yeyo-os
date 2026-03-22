/**
 * YeyoOS — FreeCanvas
 * Micro-fase 3.19 — Capa 3: Cuerpo
 *
 * Canvas HTML/CSS puro con nodos arrastrables.
 * - Nodos flotan en posiciones libres (no órbita)
 * - Posiciones guardadas en localStorage por usuario
 * - Drag para mover nodos, doble-click para abrir
 * - Pan con mouse drag en fondo, zoom con scroll
 */

import React, { useEffect, useRef, useState, useCallback } from 'react'
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

const NODE_SIZE = 72

const DEFAULT_COLORS: Record<string, string> = {
  idle:   '#1565C0',
  activo: '#4FC3F7',
  error:  '#F44336',
}

function defaultPositions(nodos: NodoLibreInfo[]): Record<string, { x: number; y: number }> {
  const cx = 400, cy = 300, radius = 200
  const out: Record<string, { x: number; y: number }> = {}
  nodos.forEach((n, i) => {
    const angle = (i / nodos.length) * Math.PI * 2 - Math.PI / 2
    out[n.id] = { x: cx + Math.cos(angle) * radius, y: cy + Math.sin(angle) * radius }
  })
  return out
}

export function FreeCanvas({
  nodos,
  userId,
  onNodoClick,
  onNodoDoubleClick,
  style,
}: FreeCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  const {
    posicionesNodos,
    setPosicionNodo,
    cargarPosicionesDesdeStorage,
    guardarPosicionesEnStorage,
    pipelineActivo,
  } = useHubStore()

  // Pan & zoom state
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [zoom, setZoom] = useState(1)
  const panningRef = useRef(false)
  const panStartRef = useRef({ x: 0, y: 0, panX: 0, panY: 0 })

  // Drag state per nodo
  const dragRef = useRef<{
    nodeId: string
    startX: number; startY: number
    origX: number; origY: number
    moved: boolean
  } | null>(null)

  useEffect(() => {
    cargarPosicionesDesdeStorage(userId)
  }, [userId, cargarPosicionesDesdeStorage])

  // Guardar posiciones al desmontar
  useEffect(() => {
    return () => { guardarPosicionesEnStorage(userId) }
  }, [userId, guardarPosicionesEnStorage])

  // ── Pan (drag on background) ──────────────────────────
  const onBgMouseDown = useCallback((e: React.MouseEvent) => {
    // Solo si click en el fondo, no en un nodo
    if ((e.target as HTMLElement).closest('[data-nodo-id]')) return
    panningRef.current = true
    panStartRef.current = { x: e.clientX, y: e.clientY, panX: pan.x, panY: pan.y }
  }, [pan])

  const onMouseMove = useCallback((e: React.MouseEvent) => {
    // ── Drag nodo ──
    if (dragRef.current) {
      const d = dragRef.current
      const dx = (e.clientX - d.startX) / zoom
      const dy = (e.clientY - d.startY) / zoom
      if (Math.abs(dx) > 3 || Math.abs(dy) > 3) d.moved = true
      if (d.moved) {
        setPosicionNodo(d.nodeId, d.origX + dx, d.origY + dy)
      }
      return
    }
    // ── Pan background ──
    if (panningRef.current) {
      const s = panStartRef.current
      setPan({ x: s.panX + (e.clientX - s.x), y: s.panY + (e.clientY - s.y) })
    }
  }, [zoom, setPosicionNodo])

  const onMouseUp = useCallback(() => {
    if (dragRef.current) {
      const d = dragRef.current
      if (!d.moved) {
        onNodoClick?.(d.nodeId)
      }
      guardarPosicionesEnStorage(userId)
      dragRef.current = null
      return
    }
    panningRef.current = false
  }, [userId, onNodoClick, guardarPosicionesEnStorage])

  // ── Zoom ──────────────────────────────────────────────
  const onWheel = useCallback((e: React.WheelEvent) => {
    e.stopPropagation()
    const factor = e.deltaY > 0 ? 0.92 : 1.08
    setZoom(z => Math.max(0.3, Math.min(3, z * factor)))
  }, [])

  // Posiciones: merge defaults con las guardadas
  const defaults = defaultPositions(nodos)
  const getPos = (id: string) => posicionesNodos[id] ?? defaults[id] ?? { x: 200, y: 200 }

  return (
    <div
      ref={containerRef}
      data-testid="free-canvas"
      data-pipeline-activo={pipelineActivo}
      onMouseDown={onBgMouseDown}
      onMouseMove={onMouseMove}
      onMouseUp={onMouseUp}
      onMouseLeave={onMouseUp}
      onWheel={onWheel}
      style={{
        position: 'relative',
        width: '100%', height: '100%',
        overflow: 'hidden',
        cursor: panningRef.current ? 'grabbing' : 'grab',
        ...style,
      }}
    >
      {/* Grid background */}
      <GridBackground saturation={1} />

      {/* World layer — transformed by pan/zoom */}
      <div style={{
        position: 'absolute', inset: 0,
        transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
        transformOrigin: '0 0',
      }}>
        {nodos.map(nodo => {
          const pos = getPos(nodo.id)
          const estado = nodo.estado ?? 'idle'
          const color = nodo.colorAcento ?? DEFAULT_COLORS[estado]

          return (
            <div
              key={nodo.id}
              data-nodo-id={nodo.id}
              onMouseDown={(e) => {
                e.stopPropagation()
                dragRef.current = {
                  nodeId: nodo.id,
                  startX: e.clientX, startY: e.clientY,
                  origX: pos.x, origY: pos.y,
                  moved: false,
                }
              }}
              onDoubleClick={(e) => {
                e.stopPropagation()
                onNodoDoubleClick?.(nodo.id)
              }}
              style={{
                position: 'absolute',
                left: pos.x - NODE_SIZE / 2,
                top: pos.y - NODE_SIZE / 2,
                width: NODE_SIZE, height: NODE_SIZE,
                borderRadius: '50%',
                background: `radial-gradient(circle at 35% 35%, ${color}cc, ${color}66)`,
                border: `2px solid ${color}`,
                boxShadow: `0 0 20px ${color}44, 0 0 40px ${color}22`,
                display: 'flex', flexDirection: 'column',
                alignItems: 'center', justifyContent: 'center',
                cursor: 'pointer',
                userSelect: 'none',
                transition: dragRef.current?.nodeId === nodo.id ? 'none' : 'box-shadow 0.3s ease',
              }}
            >
              <span style={{ fontSize: 24, lineHeight: 1 }}>{nodo.icono ?? '●'}</span>
              <span style={{
                position: 'absolute', bottom: -20,
                fontSize: 11, color: '#C0D8E8',
                whiteSpace: 'nowrap', fontFamily: 'Inter, system-ui, sans-serif',
                textShadow: '0 1px 4px rgba(0,0,0,0.8)',
              }}>{nodo.label}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
