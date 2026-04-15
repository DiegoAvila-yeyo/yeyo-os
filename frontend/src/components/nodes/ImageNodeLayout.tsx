/**
 * YeyoOS — ImageNodeLayout
 * Micro-fase 3.20 — Capa 3: Cuerpo
 *
 * Layout del nodo de generación de imágenes.
 * [Controles (izq 220px)] | [Galería (centro flex)] | [Chat IA (der 300px)]
 *
 * REGLA: Chat SIEMPRE a la derecha. Resultado (galería) SIEMPRE visible.
 */

import React, { useState, useEffect, useRef } from 'react'
import { GridBackground } from '../hub/GridBackground'

const API_BASE = 'http://localhost:8000'

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
  onAssistantMessage?: (mensaje: string) => void
  isGenerating?: boolean
}

export interface ImageOpciones {
  resolucion: string
  estilo: string
  seed: number
  pasos: number
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
}

export function ImageNodeLayout({
  imagenes: imagenesExternas = [],
  onGenerar,
  chatMessages = [],
  onChatSend,
  onAssistantMessage,
  isGenerating: isGeneratingExterno = false,
}: ImageNodeLayoutProps) {
  const [prompt, setPrompt] = useState('')
  const [modelo, setModelo] = useState('sd15')
  const [resolucion, setResolucion] = useState('512x512')
  const [estilo, setEstilo] = useState('none')
  const [seed, setSeed] = useState(-1)
  const [pasos, setPasos] = useState(10)
  const [chatInput, setChatInput] = useState('')

  // Estado local de generación real
  const [isGenerating, setIsGenerating] = useState(false)
  const [progress, setProgress] = useState(0)       // 0-100
  const [progressStep, setProgressStep] = useState(0)
  const [progressTotal, setProgressTotal] = useState(0)
  const [errorMsg, setErrorMsg] = useState('')
  const [imagenesLocales, setImagenesLocales] = useState<ImageGenerada[]>([])

  const pollingRef = useRef<NodeJS.Timeout | null>(null)

  const imagenes = [...imagenesLocales, ...imagenesExternas]

  // Polling de progreso mientras genera
  useEffect(() => {
    if (!isGenerating) {
      if (pollingRef.current) clearInterval(pollingRef.current)
      return
    }
    pollingRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/api/v1/media/image/progress`)
        const data = await res.json()
        if (data.active) {
          setProgress(data.percent)
          setProgressStep(data.step)
          setProgressTotal(data.total_steps)
        }
      } catch (_) {}
    }, 800)
    return () => { if (pollingRef.current) clearInterval(pollingRef.current) }
  }, [isGenerating])

  const [w, h] = resolucion.split('x').map(Number)

  const handleGenerar = async (overridePrompt?: string) => {
    const promptToUse = (overridePrompt ?? prompt).trim()
    if (!promptToUse || isGenerating) return
    setIsGenerating(true)
    setProgress(0)
    setProgressStep(0)
    setProgressTotal(pasos)
    setErrorMsg('')

    // Callback externo (solo notificación, no dispara fetch)
    onGenerar?.(promptToUse, modelo, { resolucion, estilo, seed, pasos })

    try {
      const res = await fetch(`${API_BASE}/api/v1/media/image/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: promptToUse,
          steps: pasos,
          width: w,
          height: h,
          seed: seed === -1 ? null : seed,
          guidance_scale: 7.5,
        }),
      })
      const data = await res.json()

      if (data.success && data.image_b64) {
        const nueva: ImageGenerada = {
          id: `img-${Date.now()}`,
          url: data.image_b64,
          prompt: promptToUse,
          modelo: data.model?.split('/').pop() || modelo,
          timestamp: Date.now(),
        }
        setImagenesLocales(prev => [nueva, ...prev])
        setProgress(100)
        onAssistantMessage?.(`Imagen generada con ${data.model?.split('/').pop() || modelo} en ${w}x${h}.`)
      } else {
        const errMsg = data.detail || data.error || 'Error generando imagen'
        setErrorMsg(errMsg)
        onAssistantMessage?.(`No pude generar la imagen: ${errMsg}`)
      }
    } catch (e: any) {
      const errMsg = `No se pudo conectar al backend: ${e.message}`
      setErrorMsg(errMsg)
      onAssistantMessage?.(`No pude generar la imagen: ${errMsg}`)
    } finally {
      setIsGenerating(false)
      setTimeout(() => setProgress(0), 1500)
    }
  }

  const handleChatSend = (e: React.FormEvent) => {
    e.preventDefault()
    const msg = chatInput.trim()
    if (!msg || isGenerating) return
    onChatSend?.(msg)   // page.tsx añade el mensaje del usuario al chat
    setChatInput('')
    void handleGenerar(msg)  // genera directamente sin pasar por el proxy de Next.js
  }

  const generandoAhora = isGenerating || isGeneratingExterno

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
            <option value="sd15">SD 1.5</option>
            <option value="lcm">LCM (Rápido)</option>
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
            <option value="256x256">256×256</option>
            <option value="512x512">512×512</option>
            <option value="512x384">512×384</option>
          </select>
        </label>

        <label style={{ color: '#90CAF9', fontSize: 12 }}>
          Estilo
          <select
            data-testid="estilo-input"
            value={estilo}
            onChange={(e) => setEstilo(e.target.value)}
            style={{
              display: 'block', width: '100%', marginTop: 4,
              backgroundColor: '#0A0E1A', border: '1px solid #1E3A5F',
              color: '#E0F7FA', padding: '6px 8px', borderRadius: 4,
            }}
          >
            <option value="none">Sin estilo</option>
            <option value="photorealistic">Fotorrealista</option>
            <option value="anime">Anime</option>
            <option value="cyberpunk">Cyberpunk</option>
            <option value="watercolor">Acuarela</option>
            <option value="minimalist">Minimalista</option>
          </select>
        </label>

        <label style={{ color: '#90CAF9', fontSize: 12 }}>
          Pasos ({pasos})
          <input
            type="range"
            min={4}
            max={30}
            value={pasos}
            onChange={(e) => setPasos(Number(e.target.value))}
            style={{ display: 'block', width: '100%', marginTop: 4, accentColor: '#4FC3F7' }}
          />
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#607D8B', marginTop: 2 }}>
            <span>4 (rápido)</span><span>30 (calidad)</span>
          </div>
        </label>

        <label style={{ color: '#90CAF9', fontSize: 12 }}>
          Seed (-1 = aleatorio)
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

        {/* Barra de progreso */}
        {generandoAhora && (
          <div style={{ marginTop: 4 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#4FC3F7', marginBottom: 4 }}>
              <span>Generando...</span>
              <span>{progressTotal > 0 ? `${progressStep}/${progressTotal}` : '...'} · {progress}%</span>
            </div>
            <div style={{ height: 6, backgroundColor: '#0A0E1A', borderRadius: 3, border: '1px solid #1E3A5F', overflow: 'hidden' }}>
              <div
                style={{
                  height: '100%',
                  width: `${progress}%`,
                  backgroundColor: '#4FC3F7',
                  borderRadius: 3,
                  transition: 'width 0.5s ease',
                  boxShadow: '0 0 8px #4FC3F7',
                }}
              />
            </div>
          </div>
        )}

        {/* Error */}
        {errorMsg && (
          <div style={{ fontSize: 11, color: '#FF6B6B', padding: '6px 8px', backgroundColor: '#1A0A0A', borderRadius: 4, border: '1px solid #FF6B6B33' }}>
            {errorMsg}
          </div>
        )}

        <button
          data-testid="generar-btn"
          onClick={() => void handleGenerar()}
          disabled={generandoAhora || !prompt.trim()}
          style={{
            backgroundColor: generandoAhora || !prompt.trim() ? '#294766' : '#1565C0',
            border: '1px solid #4FC3F7',
            color: '#E0F7FA',
            borderRadius: 6,
            padding: '8px 0',
            cursor: generandoAhora || !prompt.trim() ? 'not-allowed' : 'pointer',
            fontWeight: 600,
            fontSize: 14,
            marginTop: 'auto',
            opacity: generandoAhora || !prompt.trim() ? 0.65 : 1,
          }}
        >
          {generandoAhora ? `Generando ${progress}%` : 'Generar'}
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
          {generandoAhora && (
            <div style={{
              width: w || 512,
              maxWidth: '100%',
              borderRadius: 8,
              border: '1px solid #4FC3F733',
              backgroundColor: '#0A0E1A',
              aspectRatio: `${w}/${h}`,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 12,
            }}>
              <div style={{ fontSize: 12, color: '#4FC3F7' }}>Generando imagen...</div>
              <div style={{ width: '80%', height: 4, backgroundColor: '#1E3A5F', borderRadius: 2, overflow: 'hidden' }}>
                <div style={{
                  height: '100%',
                  width: `${progress}%`,
                  backgroundColor: '#4FC3F7',
                  transition: 'width 0.5s ease',
                  boxShadow: '0 0 6px #4FC3F7',
                }} />
              </div>
              <div style={{ fontSize: 11, color: '#607D8B' }}>
                Paso {progressStep} de {progressTotal} · {progress}%
              </div>
            </div>
          )}
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
                backgroundColor: '#0A0E1A',
                position: 'relative',
              }}
            >
              <img
                src={img.url}
                alt={img.prompt}
                style={{ width: '100%', height: 180, objectFit: 'cover', display: 'block', cursor: 'pointer' }}
                onClick={() => window.open(img.url, '_blank')}
              />
              {/* Download button */}
              <a
                href={img.url}
                download={`yeyo-${img.id}.png`}
                title="Descargar imagen"
                style={{
                  position: 'absolute',
                  top: 6,
                  right: 6,
                  backgroundColor: 'rgba(10,14,26,0.82)',
                  border: '1px solid #4FC3F7',
                  borderRadius: 6,
                  color: '#4FC3F7',
                  fontSize: 14,
                  padding: '3px 7px',
                  textDecoration: 'none',
                  lineHeight: 1,
                  cursor: 'pointer',
                }}
              >
                ⬇
              </a>
              <div style={{ padding: '6px 8px', fontSize: 11, color: '#607D8B' }}>
                {img.modelo} • {img.prompt.slice(0, 40)}...
              </div>
            </div>
          ))}
          {imagenes.length === 0 && !generandoAhora && (
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
          {chatMessages.length === 0 && (
            <div style={{ color: '#4A6072', fontSize: 12, lineHeight: 1.5 }}>
              Describe la imagen aquí y presiona Enter. La generación aparecerá en la galería central.
            </div>
          )}
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
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              data-testid="chat-input"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="Escribe un mensaje..."
              disabled={generandoAhora}
              style={{
                flex: 1,
                backgroundColor: '#0A0E1A',
                border: '1px solid #1E3A5F',
                borderRadius: 6,
                color: '#E0F7FA',
                padding: '8px 12px',
                fontSize: 13,
                boxSizing: 'border-box',
                opacity: generandoAhora ? 0.65 : 1,
              }}
            />
            <button
              type="submit"
              disabled={generandoAhora || !chatInput.trim()}
              style={{
                backgroundColor: generandoAhora || !chatInput.trim() ? '#294766' : '#1565C0',
                border: '1px solid #4FC3F7',
                borderRadius: 6,
                color: '#E0F7FA',
                padding: '8px 12px',
                fontSize: 13,
                cursor: generandoAhora || !chatInput.trim() ? 'not-allowed' : 'pointer',
                opacity: generandoAhora || !chatInput.trim() ? 0.65 : 1,
              }}
            >
              Enviar
            </button>
          </div>
        </form>
      </aside>
    </div>
  )
}
