/**
 * YeyoOS — GraphExecutionView
 * Micro-fase 3.16 — Capa 3: Cuerpo
 *
 * Mini-grafo animado que muestra el estado de ejecución de un YeyoGrafo.
 * Renderiza nodos con estados visuales animados y conexiones entre ellos.
 */

import React, { useEffect, useRef } from 'react'
import { useGraphStore, EstadoNodoGrafo, NodoGrafoVisual } from '../../stores/graphStore'

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

function ConexionVisual({ desdeEstado }: ConexionVisualProps) {
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
        marginTop: '-8px',
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
export function useGraphWebSocket(
  wsInstance: { onMessage?: (handler: (msg: unknown) => void) => void } | null
) {
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
