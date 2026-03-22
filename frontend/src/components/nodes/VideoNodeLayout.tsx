/**
 * YeyoOS — VideoNodeLayout
 * Micro-fase 3.20 — Capa 3: Cuerpo
 *
 * Layout del nodo de video.
 * [Preview player (top 50%)] | [Chat IA (der 300px, full height)]
 * [Assets panel (izq 180px)] | [Timeline (centro flex, bottom 50%)]
 */

import React, { useState } from 'react'

export interface ClipInfo {
  id: string
  nombre: string
  duracion: number  // segundos
  tipo: 'video' | 'audio' | 'imagen'
  url?: string
}

export interface VideoNodeLayoutProps {
  clips?: ClipInfo[]
  chatMessages?: Array<{ id: string; role: 'user' | 'assistant'; content: string }>
  onChatSend?: (mensaje: string) => void
  onClipAdd?: (clip: ClipInfo) => void
}

export function VideoNodeLayout({
  clips = [],
  chatMessages = [],
  onChatSend,
  onClipAdd,
}: VideoNodeLayoutProps) {
  const [chatInput, setChatInput] = useState('')
  const [playbackTime, setPlaybackTime] = useState(0)

  const handleChatSend = (e: React.FormEvent) => {
    e.preventDefault()
    if (!chatInput.trim()) return
    onChatSend?.(chatInput)
    setChatInput('')
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    Array.from(e.dataTransfer.files).forEach((file) => {
      const tipo: ClipInfo['tipo'] = file.type.startsWith('video') ? 'video'
        : file.type.startsWith('audio') ? 'audio' : 'imagen'
      onClipAdd?.({ id: crypto.randomUUID(), nombre: file.name, duracion: 0, tipo })
    })
  }

  return (
    <div
      data-testid="video-node-layout"
      style={{ display: 'flex', height: '100%', backgroundColor: '#060B18' }}
    >
      {/* === ÁREA PRINCIPAL (izquierda + centro) === */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* TOP: Preview player + Assets */}
        <div style={{ flex: '0 0 50%', display: 'flex', borderBottom: '1px solid #1E3A5F' }}>
          {/* Assets panel */}
          <aside
            data-testid="assets-panel"
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
            style={{
              width: 180, flexShrink: 0, borderRight: '1px solid #1E3A5F',
              padding: 12, overflowY: 'auto',
            }}
          >
            <div style={{ color: '#4FC3F7', fontSize: 11, fontWeight: 600, marginBottom: 8, letterSpacing: '1px' }}>
              ASSETS
            </div>
            <div style={{ fontSize: 11, color: '#37474F', marginBottom: 8 }}>Arrastra archivos aquí</div>
            {clips.map((c) => (
              <div
                key={c.id}
                data-testid={`asset-${c.id}`}
                draggable
                onDragStart={(e) => e.dataTransfer.setData('application/yeyo-clip', c.id)}
                style={{
                  padding: '6px 8px', borderRadius: 4, backgroundColor: '#0A0E1A',
                  border: '1px solid #1E3A5F', marginBottom: 4, cursor: 'grab',
                  fontSize: 12, color: '#B0BEC5',
                }}
              >
                {c.tipo === 'video' ? '🎬' : c.tipo === 'audio' ? '🎵' : '🖼️'} {c.nombre}
              </div>
            ))}
          </aside>

          {/* Preview player */}
          <div data-testid="preview-player" style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: '#000', position: 'relative' }}>
            <div style={{ color: '#37474F', fontSize: 14 }}>
              {clips.length === 0 ? '▷  Sin clips en timeline' : '▷  Preview'}
            </div>
          </div>
        </div>

        {/* BOTTOM: Timeline */}
        <div
          data-testid="timeline"
          style={{
            flex: 1, padding: 12, overflowX: 'auto', position: 'relative',
            backgroundColor: '#080D18',
          }}
        >
          {/* Timeline controls */}
          <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
            {['✂️', '➕', '🎵', '📝', '⚙️'].map((icon) => (
              <button
                key={icon}
                data-testid={`timeline-btn-${icon}`}
                style={{
                  background: 'transparent', border: '1px solid #1E3A5F',
                  borderRadius: 4, padding: '4px 8px', cursor: 'pointer',
                  color: '#90CAF9', fontSize: 16,
                }}
              >
                {icon}
              </button>
            ))}
          </div>

          {/* Clips en timeline */}
          <div style={{ display: 'flex', gap: 4, height: 60, alignItems: 'center', position: 'relative' }}>
            {clips.filter(c => c.tipo === 'video').map((c, i) => (
              <div
                key={c.id}
                data-testid={`timeline-clip-${c.id}`}
                draggable
                style={{
                  height: 48, minWidth: 100, backgroundColor: '#1565C0',
                  borderRadius: 4, border: '1px solid #4FC3F7',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 11, color: '#E0F7FA', cursor: 'grab',
                }}
              >
                {c.nombre.slice(0, 12)}
              </div>
            ))}
            {clips.length === 0 && (
              <div style={{ color: '#37474F', fontSize: 12 }}>Arrastra clips al timeline</div>
            )}
          </div>
        </div>
      </div>

      {/* === CHAT IA (derecha 300px, full height) — SIEMPRE VISIBLE === */}
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
