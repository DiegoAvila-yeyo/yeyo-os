/**
 * YeyoOS — AutomationNodeLayout
 * Micro-fase 3.20 — Capa 3: Cuerpo
 *
 * Layout del nodo de automatización.
 * [Pipeline canvas visual (izq flex)] | [Chat IA (der 300px)]
 * Pipeline canvas: bloques arrastrables con React Flow
 * Historial de ejecuciones abajo del chat
 */

import React, { useState, useCallback } from 'react'
import ReactFlow, {
  Node, Edge, Controls, Background,
  useNodesState, useEdgesState, addEdge, Connection,
  BackgroundVariant,
} from 'reactflow'

// CSS import handled by Jest mock in tests
try {
  require('reactflow/dist/style.css')
} catch (e) {
  // Ignore CSS import errors in test environment
}

export interface EjecucionHistorial {
  id: string
  timestamp: number
  estado: 'completado' | 'error' | 'cancelado'
  duracionMs: number
  mensaje?: string
}

export interface AutomationNodeLayoutProps {
  chatMessages?: Array<{ id: string; role: 'user' | 'assistant'; content: string }>
  onChatSend?: (mensaje: string) => void
  historialEjecuciones?: EjecucionHistorial[]
  initialNodes?: Node[]
  initialEdges?: Edge[]
}

const DEFAULT_NODES: Node[] = [
  { id: 'trigger', position: { x: 50, y: 100 }, data: { label: '⚡ Trigger' }, type: 'input' },
  { id: 'action', position: { x: 250, y: 100 }, data: { label: '⚙️ Acción' } },
  { id: 'output', position: { x: 450, y: 100 }, data: { label: '✅ Resultado' }, type: 'output' },
]

const DEFAULT_EDGES: Edge[] = [
  { id: 'e-trigger-action', source: 'trigger', target: 'action', animated: true },
  { id: 'e-action-output', source: 'action', target: 'output', animated: true },
]

const REACT_FLOW_STYLE: React.CSSProperties = {
  backgroundColor: '#060B18',
}

export function AutomationNodeLayout({
  chatMessages = [],
  onChatSend,
  historialEjecuciones = [],
  initialNodes = DEFAULT_NODES,
  initialEdges = DEFAULT_EDGES,
}: AutomationNodeLayoutProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)
  const [chatInput, setChatInput] = useState('')

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge({ ...params, animated: true }, eds)),
    [setEdges]
  )

  const handleChatSend = (e: React.FormEvent) => {
    e.preventDefault()
    if (!chatInput.trim()) return
    onChatSend?.(chatInput)
    setChatInput('')
  }

  return (
    <div data-testid="automation-node-layout" style={{ display: 'flex', height: '100%', backgroundColor: '#060B18' }}>
      {/* === PIPELINE CANVAS (izquierda flex) === */}
      <div data-testid="pipeline-canvas" style={{ flex: 1, position: 'relative' }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          style={REACT_FLOW_STYLE}
          fitView
        >
          <Controls />
          <Background variant={BackgroundVariant.Dots} color="#1E3A5F" gap={20} size={1} />
        </ReactFlow>
      </div>

      {/* === CHAT + HISTORIAL (derecha 300px) — SIEMPRE VISIBLE === */}
      <aside
        data-testid="chat-panel"
        style={{
          width: 300, flexShrink: 0, borderLeft: '1px solid #1E3A5F',
          display: 'flex', flexDirection: 'column',
        }}
      >
        <div style={{ padding: '12px 16px', borderBottom: '1px solid #1E3A5F', color: '#4FC3F7', fontSize: 12, fontWeight: 600 }}>
          Chat IA
        </div>
        <div data-testid="chat-messages" style={{ flex: 1, overflowY: 'auto', padding: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
          {chatMessages.map((msg) => (
            <div key={msg.id} data-testid={`chat-msg-${msg.id}`} style={{
              backgroundColor: msg.role === 'user' ? '#1E3A5F' : '#0A0E1A',
              borderRadius: 8, padding: '8px 12px', fontSize: 13,
              color: msg.role === 'user' ? '#E0F7FA' : '#90CAF9',
              alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start', maxWidth: '90%',
            }}>
              {msg.content}
            </div>
          ))}
        </div>
        <form onSubmit={handleChatSend} style={{ padding: 12, borderTop: '1px solid #1E3A5F' }}>
          <input
            data-testid="chat-input"
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            placeholder="Escribe un mensaje..."
            style={{
              width: '100%', backgroundColor: '#0A0E1A', border: '1px solid #1E3A5F',
              borderRadius: 6, color: '#E0F7FA', padding: '8px 12px',
              fontSize: 13, boxSizing: 'border-box',
            }}
          />
        </form>

        {/* Historial de ejecuciones */}
        {historialEjecuciones.length > 0 && (
          <div
            data-testid="historial-ejecuciones"
            style={{ borderTop: '1px solid #1E3A5F', maxHeight: 180, overflowY: 'auto', padding: 8 }}
          >
            <div style={{ color: '#607D8B', fontSize: 11, fontWeight: 600, marginBottom: 6, letterSpacing: '1px' }}>
              HISTORIAL
            </div>
            {historialEjecuciones.map((e) => (
              <div
                key={e.id}
                data-testid={`historial-${e.id}`}
                style={{
                  padding: '4px 8px', borderRadius: 4, marginBottom: 2,
                  backgroundColor: '#0A0E1A', border: '1px solid #1E3A5F',
                  fontSize: 11, color: e.estado === 'completado' ? '#A5D6A7' : '#EF9A9A',
                  display: 'flex', justifyContent: 'space-between',
                }}
              >
                <span>{e.estado === 'completado' ? '✅' : '❌'} {e.mensaje ?? e.estado}</span>
                <span style={{ color: '#37474F' }}>{e.duracionMs}ms</span>
              </div>
            ))}
          </div>
        )}
      </aside>
    </div>
  )
}
