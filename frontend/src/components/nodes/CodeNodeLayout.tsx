/**
 * YeyoOS — CodeNodeLayout
 * Micro-fase 3.20 — Capa 3: Cuerpo
 *
 * Layout del nodo de código.
 * [File explorer (izq 200px)] | [Monaco editor (centro flex)] | [Chat IA (der 300px)]
 * [Terminal (bottom 180px, collapsable)]
 */

import React, { useState } from 'react'
import Editor from '@monaco-editor/react'

export interface FileNode {
  id: string
  nombre: string
  tipo: 'file' | 'folder'
  children?: FileNode[]
  contenido?: string
}

export interface CodeNodeLayoutProps {
  archivos?: FileNode[]
  chatMessages?: Array<{ id: string; role: 'user' | 'assistant'; content: string }>
  onChatSend?: (mensaje: string) => void
  onArchivoSeleccionado?: (archivo: FileNode) => void
  terminalOutput?: string
}

export function CodeNodeLayout({
  archivos = [],
  chatMessages = [],
  onChatSend,
  onArchivoSeleccionado,
  terminalOutput = '',
}: CodeNodeLayoutProps) {
  const [archivoActivo, setArchivoActivo] = useState<FileNode | null>(null)
  const [codigoActivo, setCodigoActivo] = useState('')
  const [terminalVisible, setTerminalVisible] = useState(true)
  const [chatInput, setChatInput] = useState('')

  const handleArchivoClick = (archivo: FileNode) => {
    if (archivo.tipo === 'file') {
      setArchivoActivo(archivo)
      setCodigoActivo(archivo.contenido ?? '')
      onArchivoSeleccionado?.(archivo)
    }
  }

  const handleChatSend = (e: React.FormEvent) => {
    e.preventDefault()
    if (!chatInput.trim()) return
    onChatSend?.(chatInput)
    setChatInput('')
  }

  const renderFileTree = (nodes: FileNode[], depth = 0) =>
    nodes.map((n) => (
      <div key={n.id}>
        <button
          data-testid={`file-${n.id}`}
          onClick={() => handleArchivoClick(n)}
          style={{
            display: 'block', width: '100%', textAlign: 'left',
            background: archivoActivo?.id === n.id ? '#1E3A5F' : 'transparent',
            border: 'none', color: '#B0BEC5', fontSize: 12,
            padding: `4px 8px 4px ${8 + depth * 12}px`, cursor: 'pointer',
          }}
        >
          {n.tipo === 'folder' ? '📁' : '📄'} {n.nombre}
        </button>
        {n.children && renderFileTree(n.children, depth + 1)}
      </div>
    ))

  return (
    <div data-testid="code-node-layout" style={{ display: 'flex', height: '100%', backgroundColor: '#060B18' }}>
      {/* === FILE EXPLORER (izquierda 200px) === */}
      <aside
        data-testid="file-explorer"
        style={{
          width: 200, flexShrink: 0, borderRight: '1px solid #1E3A5F',
          overflowY: 'auto', padding: '8px 0',
        }}
      >
        <div style={{ color: '#4FC3F7', fontSize: 11, fontWeight: 600, padding: '4px 12px 8px', letterSpacing: '1px' }}>
          EXPLORADOR
        </div>
        {renderFileTree(archivos)}
        {archivos.length === 0 && (
          <div style={{ color: '#37474F', fontSize: 12, padding: '8px 12px' }}>Sin archivos</div>
        )}
      </aside>

      {/* === EDITOR + TERMINAL (centro) === */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* Monaco Editor */}
        <div data-testid="monaco-editor-container" style={{ flex: 1, overflow: 'hidden' }}>
          <Editor
            height="100%"
            language={archivoActivo?.nombre.endsWith('.py') ? 'python' : 'typescript'}
            value={codigoActivo}
            onChange={(val) => setCodigoActivo(val ?? '')}
            theme="vs-dark"
            options={{
              fontSize: 14,
              minimap: { enabled: false },
              scrollBeyondLastLine: false,
              wordWrap: 'on',
            }}
          />
        </div>

        {/* Terminal */}
        {terminalVisible && (
          <div
            data-testid="terminal"
            style={{
              height: 180, borderTop: '1px solid #1E3A5F', backgroundColor: '#000',
              fontFamily: 'monospace', fontSize: 12, color: '#A5D6A7',
              padding: 12, overflowY: 'auto',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              <span style={{ color: '#4FC3F7', fontWeight: 600 }}>TERMINAL</span>
              <button
                data-testid="terminal-toggle"
                onClick={() => setTerminalVisible(false)}
                style={{ background: 'transparent', border: 'none', color: '#607D8B', cursor: 'pointer' }}
              >
                ▼
              </button>
            </div>
            <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{terminalOutput || '$ _'}</pre>
          </div>
        )}
        {!terminalVisible && (
          <button
            data-testid="terminal-toggle-show"
            onClick={() => setTerminalVisible(true)}
            style={{
              height: 28, backgroundColor: '#0A0E1A', border: 'none',
              borderTop: '1px solid #1E3A5F', color: '#607D8B',
              cursor: 'pointer', fontSize: 12, width: '100%',
            }}
          >
            ▲ Terminal
          </button>
        )}
      </div>

      {/* === CHAT IA (derecha 300px) — SIEMPRE VISIBLE === */}
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
      </aside>
    </div>
  )
}
