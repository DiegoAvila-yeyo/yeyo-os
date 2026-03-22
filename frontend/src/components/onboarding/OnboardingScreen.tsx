/**
 * YeyoOS — OnboardingScreen
 * Micro-fase 3.18 — Capa 3: Cuerpo
 *
 * Flujo:
 *   1. Pulso azul (1s)
 *   2. Saturación gris→azul (3s)
 *   3. Typewriter: "Hola."
 *   4. Typewriter: "¿Cómo me llamas?"
 *   5. Input nombre → Enter
 *   6. TTS habla + typewriter respuesta
 *   7. Input primera tarea → Enter → Hub
 */

import React, { useState, useEffect, useRef, useCallback } from 'react'
import { TypewriterText } from './TypewriterText'
import { GridBackground } from '../hub/GridBackground'
import { useSystemStore } from '../../stores/systemStore'
import { useFirstTaskStore } from '../../stores/firstTaskStore'

export interface OnboardingScreenProps {
  onComplete: (nombre: string) => void
}

type Step = 'pulse' | 'saturate' | 'hola' | 'nombre_prompt' | 'nombre_input' | 'respuesta' | 'tarea_input'

function hablar(texto: string) {
  if (typeof window === 'undefined' || !('speechSynthesis' in window)) return
  window.speechSynthesis.cancel()
  const utt = new SpeechSynthesisUtterance(texto)
  utt.lang = 'es-MX'
  utt.rate = 0.92
  utt.pitch = 1.05
  window.speechSynthesis.speak(utt)
}

export function OnboardingScreen({ onComplete }: OnboardingScreenProps) {
  const [step, setStep]         = useState<Step>('pulse')
  const [saturation, setSat]    = useState(0)
  const [nombre, setNombre]     = useState('')
  const [inputVal, setInputVal] = useState('')
  const [tareaVal, setTareaVal] = useState('')
  const [respuesta, setRespuesta] = useState('')

  const inputRef = useRef<HTMLInputElement>(null)
  const tareaRef = useRef<HTMLInputElement>(null)

  const { iniciarPrimeraTarea } = useFirstTaskStore()

  // ── Paso 1: pulso → 1s → saturate ─────────────────────────────
  useEffect(() => {
    if (step !== 'pulse') return
    const t = setTimeout(() => setStep('saturate'), 1200)
    return () => clearTimeout(t)
  }, [step])

  // ── Paso 2: saturación 0→1 en 3s → hola ──────────────────────
  useEffect(() => {
    if (step !== 'saturate') return
    const start = Date.now()
    const duration = 3000
    const tick = setInterval(() => {
      const p = Math.min((Date.now() - start) / duration, 1)
      setSat(p)
      if (p >= 1) { clearInterval(tick); setStep('hola') }
    }, 16)
    return () => clearInterval(tick)
  }, [step])

  // ── Paso 3: typewriter "Hola." → 800ms → nombre_prompt ────────
  const onHolaComplete = useCallback(() => {
    setTimeout(() => setStep('nombre_prompt'), 800)
  }, [])

  // ── Paso 4: typewriter "¿Cómo me llamas?" → nombre_input ──────
  const onNombrePromptComplete = useCallback(() => {
    setStep('nombre_input')
    setTimeout(() => inputRef.current?.focus(), 60)
  }, [])

  // ── Paso 5: submit nombre ─────────────────────────────────────
  const submitNombre = useCallback((e: React.FormEvent) => {
    e.preventDefault()
    const n = inputVal.trim()
    if (!n) return
    setNombre(n)
    const txt = `Hola ${n}. ¿Cuál va a ser la primera tarea del día?`
    setRespuesta(txt)
    setStep('respuesta')
    // TTS: debe llamarse sincrónicamente desde el evento del usuario
    hablar(txt)
  }, [inputVal])

  // ── Paso 6: typewriter respuesta → tarea_input ────────────────
  const onRespuestaComplete = useCallback(() => {
    setTimeout(() => {
      setStep('tarea_input')
      setTimeout(() => tareaRef.current?.focus(), 60)
    }, 400)
  }, [])

  // ── Paso 7: submit tarea → Hub ────────────────────────────────
  const submitTarea = useCallback((e: React.FormEvent) => {
    e.preventDefault()
    const t = tareaVal.trim()
    if (!t) return
    // Guardar tarea en store (sin timeouts que crasheen)
    try { iniciarPrimeraTarea(t) } catch (_) { /* safe */ }
    onComplete(nombre)
  }, [tareaVal, nombre, iniciarPrimeraTarea, onComplete])

  const pulsing = step === 'pulse'

  // ── Indicador de progreso para saturate ──────────────────
  const saturateMsg =
    saturation < 0.33 ? 'Inicializando núcleo...' :
    saturation < 0.66 ? 'Sincronizando redes...' :
    saturation < 1.0  ? 'Cargando contexto...' : ''

  return (
    <div
      data-testid="onboarding-screen"
      data-step={step}
      style={{
        position: 'fixed', inset: 0, zIndex: 1000,
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        backgroundColor: '#050A14',
        fontFamily: 'Inter, system-ui, sans-serif',
      }}
    >
      <GridBackground saturation={saturation} />

      {/* Nodo central */}
      <div style={{
        position: 'relative', zIndex: 2,
        width: 80, height: 80, borderRadius: '50%',
        backgroundColor: '#0D1B2A',
        border: '2px solid #4FC3F7',
        animation: pulsing ? 'pulse-glow 1.4s ease-in-out infinite' : undefined,
        boxShadow: pulsing
          ? undefined
          : '0 0 24px 8px rgba(79,195,247,0.25)',
        transition: 'box-shadow 0.6s ease',
        marginBottom: 52,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 30,
      }}>✦</div>

      {/* Texto durante saturate */}
      {step === 'saturate' && (
        <div style={{
          position: 'relative', zIndex: 2,
          color: '#4FC3F7', fontSize: 13,
          fontFamily: 'monospace', letterSpacing: '0.12em',
          marginTop: -36, marginBottom: 36,
          opacity: 0.7,
          animation: 'fade-in 0.4s ease',
        }}>
          {saturateMsg}
        </div>
      )}

      {/* Texto principal */}
      <div style={{
        position: 'relative', zIndex: 2,
        textAlign: 'center', color: '#E0F7FA',
        minHeight: 140, display: 'flex', flexDirection: 'column',
        alignItems: 'center', gap: 16,
      }}>

        {/* "Hola." typewriter */}
        {step === 'hola' && (
          <div style={{ fontSize: 34, fontWeight: 300 }}>
            <TypewriterText text="Hola." speed={80} onComplete={onHolaComplete} />
          </div>
        )}

        {/* "Hola." estático + "¿Cómo me llamas?" typewriter */}
        {step === 'nombre_prompt' && (
          <>
            <div style={{ fontSize: 34, fontWeight: 300 }}>Hola.</div>
            <div style={{ fontSize: 22, color: '#90CAF9' }}>
              <TypewriterText text="¿Cómo me llamas?" speed={55} onComplete={onNombrePromptComplete} />
            </div>
          </>
        )}

        {/* Input nombre */}
        {step === 'nombre_input' && (
          <>
            <div style={{ fontSize: 34, fontWeight: 300 }}>Hola.</div>
            <div style={{ fontSize: 22, color: '#90CAF9', marginBottom: 8 }}>¿Cómo me llamas?</div>
            <form onSubmit={submitNombre}>
              <input
                ref={inputRef}
                data-testid="name-input"
                value={inputVal}
                onChange={e => setInputVal(e.target.value)}
                autoFocus
                style={{
                  background: 'transparent', border: 'none',
                  borderBottom: '2px solid #4FC3F7',
                  color: '#E0F7FA', fontSize: 26, textAlign: 'center',
                  outline: 'none', width: 260, padding: '6px 0',
                  caretColor: '#4FC3F7', fontFamily: 'inherit',
                }}
              />
            </form>
          </>
        )}

        {/* TTS + typewriter respuesta */}
        {step === 'respuesta' && (
          <div style={{ fontSize: 22, color: '#90CAF9', maxWidth: 480 }}>
            <TypewriterText text={respuesta} speed={38} onComplete={onRespuestaComplete} />
          </div>
        )}

        {/* Input primera tarea */}
        {step === 'tarea_input' && (
          <>
            <div style={{ fontSize: 22, color: '#90CAF9', marginBottom: 8, maxWidth: 480 }}>
              Hola {nombre}. ¿Cuál va a ser la primera tarea del día?
            </div>
            <form onSubmit={submitTarea}>
              <input
                ref={tareaRef}
                data-testid="task-input"
                value={tareaVal}
                onChange={e => setTareaVal(e.target.value)}
                placeholder="Describe tu tarea..."
                autoFocus
                style={{
                  background: 'transparent', border: 'none',
                  borderBottom: '2px solid #4FC3F7',
                  color: '#E0F7FA', fontSize: 20, textAlign: 'center',
                  outline: 'none', width: 380, padding: '6px 0',
                  caretColor: '#4FC3F7', fontFamily: 'inherit',
                  '::placeholder': { color: '#445' },
                } as React.CSSProperties}
              />
            </form>
          </>
        )}
      </div>

      {/* Hint Enter */}
      {(step === 'nombre_input' || step === 'tarea_input') && (
        <div style={{
          position: 'relative', zIndex: 2, marginTop: 24,
          color: '#2a4a5a', fontSize: 12, fontFamily: 'monospace',
        }}>
          Presiona Enter para continuar
        </div>
      )}
    </div>
  )
}
