/**
 * YeyoOS — HubSidebar
 * Micro-fase 3.20 — Capa 3: Cuerpo
 *
 * Sidebar izquierdo colapsable con mini-Hub canvas.
 * - 240px abierto / 0px cerrado, transición 300ms
 * - Muestra nodos instalados en miniatura con su estado
 * - Double grid background en miniatura
 * - Click en nodo → abre tab en workspace
 */

import React from 'react'
import { useHubStore } from '../../stores/hubStore'
import { GridBackground } from '../hub/GridBackground'
import { VignetteOverlay } from '../hub/VignetteOverlay'

export interface NodoMiniInfo {
  id: string
  label: string
  icono?: string
  estado?: 'idle' | 'activo' | 'error'
}

export interface HubSidebarProps {
  open: boolean
  nodos: NodoMiniInfo[]
  onNodoClick: (nodeId: string) => void
}

const ESTADO_COLOR: Record<string, string> = {
  idle: '#1565C0',
  activo: '#4FC3F7',
  error: '#F44336',
}

export function HubSidebar({ open, nodos, onNodoClick }: HubSidebarProps) {
  const pipelineActivo = useHubStore((s) => s.pipelineActivo)
  const nodosEnPipeline = useHubStore((s) => s.nodosEnPipeline)

  return (
    <aside
      data-testid="hub-sidebar"
      data-open={open}
      style={{
        width: open ? 240 : 0,
        minWidth: open ? 240 : 0,
        maxWidth: open ? 240 : 0,
        overflow: 'hidden',
        transition: 'width 300ms ease, min-width 300ms ease, max-width 300ms ease',
        backgroundColor: '#060B18',
        borderRight: open ? '1px solid #1E3A5F' : 'none',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
        flexShrink: 0,
      }}
      aria-hidden={!open}
    >
      {open && (
        <>
          {/* Mini Hub canvas con double grid */}
          <div style={{ position: 'relative', height: 180, overflow: 'hidden' }}>
            <GridBackground saturation={1.0} style={{ opacity: 0.6 }} />
            <VignetteOverlay visible={pipelineActivo} maxOpacity={0.25} />
            <div style={{ position: 'relative', zIndex: 2, padding: 12 }}>
              <div style={{ color: '#4FC3F7', fontSize: 11, fontWeight: 600, marginBottom: 8, letterSpacing: '1px', textTransform: 'uppercase' }}>
                Hub
              </div>
              {/* Representación visual mínima del hub */}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {nodos.map((n) => {
                  const enPipeline = nodosEnPipeline.includes(n.id)
                  const estado = enPipeline ? 'activo' : (n.estado ?? 'idle')
                  return (
                    <button
                      key={n.id}
                      data-testid={`mini-node-${n.id}`}
                      data-estado={estado}
                      onClick={() => onNodoClick(n.id)}
                      title={n.label}
                      style={{
                        width: 36,
                        height: 36,
                        borderRadius: '50%',
                        backgroundColor: ESTADO_COLOR[estado] ?? ESTADO_COLOR.idle,
                        border: `2px solid ${enPipeline ? '#4FC3F7' : '#1E3A5F'}`,
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: 16,
                        boxShadow: enPipeline ? '0 0 12px rgba(79,195,247,0.5)' : 'none',
                        transition: 'all 300ms ease',
                      }}
                    >
                      {n.icono ?? '◎'}
                    </button>
                  )
                })}
              </div>
            </div>
          </div>

          {/* Lista de nodos instalados */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '8px 0' }}>
            {nodos.map((n) => {
              const enPipeline = nodosEnPipeline.includes(n.id)
              const estado = enPipeline ? 'activo' : (n.estado ?? 'idle')
              return (
                <button
                  key={n.id}
                  data-testid={`sidebar-node-${n.id}`}
                  onClick={() => onNodoClick(n.id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    width: '100%',
                    padding: '8px 16px',
                    background: 'transparent',
                    border: 'none',
                    borderBottom: '1px solid #0D1B2A',
                    cursor: 'pointer',
                    color: '#B0BEC5',
                    fontSize: 13,
                    textAlign: 'left',
                  }}
                >
                  <span style={{
                    width: 8, height: 8, borderRadius: '50%',
                    backgroundColor: ESTADO_COLOR[estado],
                    flexShrink: 0,
                  }} />
                  <span style={{ fontSize: 16 }}>{n.icono ?? '◎'}</span>
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {n.label}
                  </span>
                </button>
              )
            })}
          </div>
        </>
      )}
    </aside>
  )
}
