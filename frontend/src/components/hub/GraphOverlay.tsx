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
