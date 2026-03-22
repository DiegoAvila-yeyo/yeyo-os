/**
 * YeyoOS — OnboardingScreen
 * Micro-fase 3.18 — Capa 3: Cuerpo
 *
 * Flujo completo de onboarding:
 *   0. Todo gris (saturation=0) — Hub inerte visible detrás
 *   1. Pulso azul del nodo central (1 segundo)
 *   2. Saturación 0→1 en 4 segundos (center-out)
 *   3. Typewriter: "Hola." → pausa → "¿Cómo me llamas?"
 *   4. Input minimalista — Enter confirma nombre
 *   5. TTS habla: "Hola [nombre]. ¿Cuál va a ser la primera tarea del día?"
 *   6. Input se convierte en chat principal del Hub
 *   7. Nombre guardado en Flash Memory
 */

import React, { useState, useEffect, useRef, useCallback } from 'react'
import { TypewriterText } from './TypewriterText'
import { GridBackground } from '../hub/GridBackground'
import { useSystemStore } from '../../stores/systemStore'
import { useFirstTaskStore } from '../../stores/firstTaskStore'

type OnboardingStep =
  | 'pulse'          // Paso 1: pulso inicial
  | 'saturate'       // Paso 2: transición de color
  | 'greet_hola'     // Paso 3a: typewriter "Hola."
  | 'greet_name'     // Paso 3b: typewriter "¿Cómo me llamas?"
  | 'input_name'     // Paso 4: input de nombre
  | 'tts_response'   // Paso 5: TTS + typewriter respuesta
  | 'input_task'     // Paso 6: input de primera tarea
  | 'done'           // Paso 7: listo

export interface OnboardingScreenProps {
  onComplete: (nombre: string) => void
}

export function OnboardingScreen({ onComplete }: OnboardingScreenProps) {
  const [step, setStep] = useState<OnboardingStep>('pulse')
  const [saturation, setSaturation] = useState(0)
  const [nombre, setNombre] = useState('')
  const [inputValue, setInputValue] = useState('')
  const [taskValue, setTaskValue] = useState('')
  const [ttsText, setTtsText] = useState('')
  const [pulsing, setPulsing] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const taskInputRef = useRef<HTMLInputElement>(null)
  const satAnimRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const killSwitchRegistered = useSystemStore((s) => s.killSwitchRegistered)
  const { iniciarPrimeraTarea } = useFirstTaskStore()

  // Paso 1: pulso al montar
  useEffect(() => {
    setPulsing(true)
    const t = setTimeout(() => {
      setPulsing(false)
      setStep('saturate')
    }, 1000)
    return () => clearTimeout(t)
  }, [])

  // Paso 2: saturación 0→1 en 4 segundos
  useEffect(() => {
    if (step !== 'saturate') return
    const startTime = Date.now()
    const duration = 4000
    satAnimRef.current = setInterval(() => {
      const elapsed = Date.now() - startTime
      const progress = Math.min(elapsed / duration, 1)
      setSaturation(progress)
      if (progress >= 1) {
        clearInterval(satAnimRef.current!)
        setStep('greet_hola')
      }
    }, 16)
    return () => { if (satAnimRef.current) clearInterval(satAnimRef.current) }
  }, [step])

  // Paso 3b: después de "Hola." pausa 800ms → siguiente texto
  const handleHolaComplete = useCallback(() => {
    setTimeout(() => setStep('greet_name'), 800)
  }, [])

  // Paso 4: mostrar input al terminar "¿Cómo me llamas?"
  const handleNamePromptComplete = useCallback(() => {
    setStep('input_name')
    setTimeout(() => inputRef.current?.focus(), 50)
  }, [])

  // Paso 5: enviar nombre
  const handleSubmitNombre = useCallback(async (e: React.FormEvent | React.KeyboardEvent) => {
    e.preventDefault()
    const trimmed = inputValue.trim()
    if (!trimmed) return
    setNombre(trimmed)
    setStep('tts_response')

    const respuestaTexto = `Hola ${trimmed}. ¿Cuál va a ser la primera tarea del día?`
    setTtsText(respuestaTexto)

    // Llamar TTS backend
    try {
      await fetch('/api/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: respuestaTexto }),
      })
    } catch {
      // TTS falla silenciosamente — la UI continúa
    }

    // Guardar en Flash Memory
    try {
      await fetch('/api/memory/flash', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tipo: 'user_profile',
          contenido: { nombre: trimmed },
          importancia: 1.0,
        }),
      })
    } catch {
      // Flash Memory falla silenciosamente
    }
  }, [inputValue])

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') handleSubmitNombre(e)
  }, [handleSubmitNombre])

  const handleTtsComplete = useCallback(() => {
    setTimeout(() => {
      setStep('input_task')
      setTimeout(() => taskInputRef.current?.focus(), 50)
    }, 500)
  }, [])

  // Paso 7: enviar primera tarea
  const handleSubmitTask = useCallback(async (e: React.FormEvent | React.KeyboardEvent) => {
    e.preventDefault()
    const trimmed = taskValue.trim()
    if (!trimmed) return
    iniciarPrimeraTarea(trimmed)
    setTimeout(() => onComplete(nombre), 500)
  }, [taskValue, nombre, iniciarPrimeraTarea, onComplete])

  const handleTaskKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') handleSubmitTask(e)
  }, [handleSubmitTask])

  return (
    <div
      data-testid="onboarding-screen"
      data-step={step}
      style={{
        position: 'fixed',
        inset: 0,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#050A14',
        zIndex: 1000,
      }}
    >
      {/* Fondo de cuadrícula */}
      <GridBackground saturation={saturation} />

      {/* Nodo central con pulso */}
      <div
        data-testid="central-node-pulse"
        style={{
          position: 'relative',
          zIndex: 2,
          width: 80,
          height: 80,
          borderRadius: '50%',
          backgroundColor: '#4FC3F7',
          boxShadow: pulsing
            ? '0 0 60px 30px rgba(79, 195, 247, 0.6)'
            : '0 0 20px 8px rgba(79, 195, 247, 0.3)',
          transition: 'box-shadow 0.5s ease',
          marginBottom: 48,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 28,
        }}
      >
        ✦
      </div>

      {/* Área de texto */}
      <div
        style={{
          position: 'relative',
          zIndex: 2,
          textAlign: 'center',
          color: '#E0F7FA',
          fontFamily: 'Inter, system-ui, sans-serif',
          minHeight: 120,
        }}
      >
        {(step === 'greet_hola') && (
          <div style={{ fontSize: 32, fontWeight: 300, marginBottom: 8 }}>
            <TypewriterText text="Hola." speed={80} onComplete={handleHolaComplete} />
          </div>
        )}

        {(step === 'greet_name' || step === 'input_name') && (
          <>
            <div style={{ fontSize: 32, fontWeight: 300, marginBottom: 16 }}>
              Hola.
            </div>
            {step === 'greet_name' && (
              <div style={{ fontSize: 22, color: '#90CAF9' }}>
                <TypewriterText
                  text="¿Cómo me llamas?"
                  speed={60}
                  onComplete={handleNamePromptComplete}
                />
              </div>
            )}
          </>
        )}

        {step === 'input_name' && (
          <>
            <div style={{ fontSize: 32, fontWeight: 300, marginBottom: 16 }}>Hola.</div>
            <div style={{ fontSize: 22, color: '#90CAF9', marginBottom: 32 }}>¿Cómo me llamas?</div>
            <form onSubmit={handleSubmitNombre} style={{ display: 'flex', justifyContent: 'center' }}>
              <input
                ref={inputRef}
                data-testid="name-input"
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder=""
                autoFocus
                style={{
                  background: 'transparent',
                  border: 'none',
                  borderBottom: '1px solid #4FC3F7',
                  color: '#E0F7FA',
                  fontSize: 24,
                  textAlign: 'center',
                  outline: 'none',
                  width: 280,
                  padding: '8px 0',
                  fontFamily: 'inherit',
                  caretColor: '#4FC3F7',
                }}
              />
            </form>
          </>
        )}

        {step === 'tts_response' && (
          <div style={{ fontSize: 22, color: '#90CAF9', maxWidth: 480 }}>
            <TypewriterText
              text={ttsText}
              speed={40}
              onComplete={handleTtsComplete}
            />
          </div>
        )}

        {step === 'input_task' && (
          <>
            <div style={{ fontSize: 22, color: '#90CAF9', marginBottom: 32, maxWidth: 480 }}>
              Hola {nombre}. ¿Cuál va a ser la primera tarea del día?
            </div>
            <form onSubmit={handleSubmitTask} style={{ display: 'flex', justifyContent: 'center' }}>
              <input
                ref={taskInputRef}
                data-testid="task-input"
                type="text"
                value={taskValue}
                onChange={(e) => setTaskValue(e.target.value)}
                onKeyDown={handleTaskKeyDown}
                placeholder="Describe tu tarea..."
                autoFocus
                style={{
                  background: 'transparent',
                  border: 'none',
                  borderBottom: '1px solid #4FC3F7',
                  color: '#E0F7FA',
                  fontSize: 18,
                  textAlign: 'center',
                  outline: 'none',
                  width: 380,
                  padding: '8px 0',
                  fontFamily: 'inherit',
                  caretColor: '#4FC3F7',
                }}
              />
            </form>
          </>
        )}
      </div>
    </div>
  )
}
