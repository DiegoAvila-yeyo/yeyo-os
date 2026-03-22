/**
 * YeyoOS — ImageNodeLayout
 * Micro-fase 3.20 — Capa 3: Cuerpo
 *
 * Layout del nodo de generación de imágenes.
 * [Controles (izq 220px)] | [Galería (centro flex)] | [Chat IA (der 300px)]
 *
 * REGLA: Chat SIEMPRE a la derecha. Resultado (galería) SIEMPRE visible.
 */

import React, { useState } from 'react'
import { GridBackground } from '../hub/GridBackground'

export interface ImageGenerada {
  id: string
  url: string
  prompt: string
  modelo: string
  timestamp: number
}

export interface ImageNodeLayoutProps {
  imagenes?: ImageGenerada[]
  onGenerar?: (prompt: string, modelo: string, opciones: ImageOpciones) => void
  chatMessages?: ChatMessage[]
  onChatSend?: (mensaje: string) => void
}

export interface ImageOpciones {
  resolucion: string
  estilo: string
  seed: number
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
}

export function ImageNodeLayout({
  imagenes = [],
  onGenerar,
  chatMessages = [],
  onChatSend,
}: ImageNodeLayoutProps) {
  const [prompt, setPrompt] = useState('')
  const [modelo, setModelo] = useState('sdxl')
  const [resolucion, setResolucion] = useState('1024x1024')
  const [estilo, setEstilo] = useState('photorealistic')
  const [seed, setSeed] = useState(-1)
  const [chatInput, setChatInput] = useState('')

  const handleGenerar = () => {
    if (!prompt.trim()) return
    onGenerar?.(prompt, modelo, { resolucion, estilo, seed })
  }

  const handleChatSend = (e: React.FormEvent) => {
    e.preventDefault()
    if (!chatInput.trim()) return
    onChatSend?.(chatInput)
    setChatInput('')
  }

  return (
    <div
      data-testid="image-node-layout"
      style={{
        display: 'flex',
        height: '100%',
        position: 'relative',
        overflow: 'hidden',
        backgroundColor: '#060B18',
      }}
    >
      {/* Double Grid Background sutil */}
      <GridBackground saturation={1.0} style={{ opacity: 0.5 }} />

      {/* === CONTROLES (izquierda 220px) === */}
      <aside
        data-testid="image-controls"
        style={{
          width: 220,
          flexShrink: 0,
          padding: 16,
          borderRight: '1px solid #1E3A5F',
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
          position: 'relative',
          zIndex: 1,
          overflowY: 'auto',
        }}
      >
        <label style={{ color: '#90CAF9', fontSize: 12 }}>
          Prompt
          <textarea
            data-testid="prompt-textarea"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={4}
            style={{
              display: 'block',
              width: '100%',
              marginTop: 4,
              backgroundColor: '#0A0E1A',
              border: '1px solid #1E3A5F',
              borderRadius: 4,
              color: '#E0F7FA',
              padding: 8,
              fontSize: 13,
              resize: 'vertical',
              fontFamily: 'inherit',
            }}
          />
        </label>

        <label style={{ color: '#90CAF9', fontSize: 12 }}>
          Modelo
          <select
            data-testid="modelo-select"
            value={modelo}
            onChange={(e) => setModelo(e.target.value)}
            style={{
              display: 'block',
              width: '100%',
              marginTop: 4,
              backgroundColor: '#0A0E1A',
              border: '1px solid #1E3A5F',
              color: '#E0F7FA',
              padding: '6px 8px',
              borderRadius: 4,
            }}
          >
            <option value="sdxl">SDXL</option>
            <option value="flux">Flux</option>
            <option value="dalle3">DALL-E 3</option>
          </select>
        </label>

        <label style={{ color: '#90CAF9', fontSize: 12 }}>
          Resolución
          <select
            data-testid="resolucion-select"
            value={resolucion}
            onChange={(e) => setResolucion(e.target.value)}
            style={{
              display: 'block', width: '100%', marginTop: 4,
              backgroundColor: '#0A0E1A', border: '1px solid #1E3A5F',
              color: '#E0F7FA', padding: '6px 8px', borderRadius: 4,
            }}
          >
            <option value="512x512">512×512</option>
            <option value="1024x1024">1024×1024</option>
            <option value="1920x1080">1920×1080</option>
          </select>
        </label>

        <label style={{ color: '#90CAF9', fontSize: 12 }}>
          Estilo
          <input
            data-testid="estilo-input"
            value={estilo}
            onChange={(e) => setEstilo(e.target.value)}
            style={{
              display: 'block', width: '100%', marginTop: 4,
              backgroundColor: '#0A0E1A', border: '1px solid #1E3A5F',
              color: '#E0F7FA', padding: '6px 8px', borderRadius: 4,
            }}
          />
        </label>

        <label style={{ color: '#90CAF9', fontSize: 12 }}>
          Seed
          <input
            data-testid="seed-input"
            type="number"
            value={seed}
            onChange={(e) => setSeed(Number(e.target.value))}
            style={{
              display: 'block', width: '100%', marginTop: 4,
              backgroundColor: '#0A0E1A', border: '1px solid #1E3A5F',
              color: '#E0F7FA', padding: '6px 8px', borderRadius: 4,
            }}
          />
        </label>

        <button
          data-testid="generar-btn"
          onClick={handleGenerar}
          style={{
            backgroundColor: '#1565C0',
            border: '1px solid #4FC3F7',
            color: '#E0F7FA',
            borderRadius: 6,
            padding: '8px 0',
            cursor: 'pointer',
            fontWeight: 600,
            fontSize: 14,
            marginTop: 'auto',
          }}
        >
          Generar
        </button>
      </aside>

      {/* === GALERÍA (centro flex) === */}
      <main
        data-testid="gallery-area"
        style={{
          flex: 1,
          padding: 16,
          overflowY: 'auto',
          position: 'relative',
          zIndex: 1,
        }}
      >
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
            gap: 12,
          }}
        >
          {imagenes.map((img) => (
            <div
              key={img.id}
              data-testid={`imagen-card-${img.id}`}
              draggable
              onDragStart={(e) => e.dataTransfer.setData('application/yeyo-image', img.id)}
              style={{
                borderRadius: 8,
                overflow: 'hidden',
                border: '1px solid #1E3A5F',
                cursor: 'grab',
                backgroundColor: '#0A0E1A',
              }}
            >
              <img
                src={img.url}
                alt={img.prompt}
                style={{ width: '100%', height: 180, objectFit: 'cover', display: 'block' }}
              />
              <div style={{ padding: '6px 8px', fontSize: 11, color: '#607D8B' }}>
                {img.modelo} • {img.prompt.slice(0, 40)}...
              </div>
            </div>
          ))}
          {imagenes.length === 0 && (
            <div style={{ color: '#37474F', fontSize: 14, gridColumn: '1/-1', textAlign: 'center', paddingTop: 60 }}>
              Las imágenes generadas aparecerán aquí
            </div>
          )}
        </div>
      </main>

      {/* === CHAT IA (derecha 300px) — SIEMPRE VISIBLE === */}
      <aside
        data-testid="chat-panel"
        style={{
          width: 300,
          flexShrink: 0,
          borderLeft: '1px solid #1E3A5F',
          display: 'flex',
          flexDirection: 'column',
          position: 'relative',
          zIndex: 1,
        }}
      >
        <div style={{ padding: '12px 16px', borderBottom: '1px solid #1E3A5F', color: '#4FC3F7', fontSize: 12, fontWeight: 600 }}>
          Chat IA
        </div>
        <div
          data-testid="chat-messages"
          style={{ flex: 1, overflowY: 'auto', padding: 12, display: 'flex', flexDirection: 'column', gap: 8 }}
        >
          {chatMessages.map((msg) => (
            <div
              key={msg.id}
              data-testid={`chat-msg-${msg.id}`}
              style={{
                backgroundColor: msg.role === 'user' ? '#1E3A5F' : '#0A0E1A',
                borderRadius: 8,
                padding: '8px 12px',
                fontSize: 13,
                color: msg.role === 'user' ? '#E0F7FA' : '#90CAF9',
                alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                maxWidth: '90%',
              }}
            >
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
              width: '100%',
              backgroundColor: '#0A0E1A',
              border: '1px solid #1E3A5F',
              borderRadius: 6,
              color: '#E0F7FA',
              padding: '8px 12px',
              fontSize: 13,
              boxSizing: 'border-box',
            }}
          />
        </form>
      </aside>
    </div>
  )
}
