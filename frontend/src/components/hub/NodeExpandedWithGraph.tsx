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
