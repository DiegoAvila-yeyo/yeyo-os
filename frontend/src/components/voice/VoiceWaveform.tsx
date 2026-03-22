/**
 * YeyoOS — VoiceWaveform
 * Micro-fase 5.27 — Capa 5: Órganos
 *
 * Barra de voz que aparece en bottom-center cuando el micrófono graba.
 * Waveform animado con Web Audio API. Texto transcrito letra por letra.
 * Se desvanece automáticamente al terminar.
 */

import React, { useEffect, useRef, useCallback } from 'react'
import { useVoiceStore, MicState } from '../../stores/voiceStore'

const BAR_COUNT = 24
const BAR_MIN_HEIGHT = 4
const BAR_MAX_HEIGHT = 40

export function VoiceWaveform() {
  const { micState, transcript } = useVoiceStore()
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animFrameRef = useRef<number | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const audioCtxRef = useRef<AudioContext | null>(null)

  const visible = micState === 'recording' || micState === 'processing'

  // Iniciar captura de audio para el waveform cuando graba
  useEffect(() => {
    if (micState !== 'recording') {
      // Limpiar audio context al salir de recording
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop())
        streamRef.current = null
      }
      if (audioCtxRef.current) {
        audioCtxRef.current.close()
        audioCtxRef.current = null
        analyserRef.current = null
      }
      return
    }

    // Obtener acceso al micrófono para visualización
    navigator.mediaDevices
      ?.getUserMedia({ audio: true })
      .then((stream) => {
        streamRef.current = stream
        const ctx = new AudioContext()
        audioCtxRef.current = ctx
        const analyser = ctx.createAnalyser()
        analyser.fftSize = 64
        analyserRef.current = analyser
        const source = ctx.createMediaStreamSource(stream)
        source.connect(analyser)
      })
      .catch(() => {
        // Sin permisos de micrófono — usar animación genérica
      })
  }, [micState])

  // Dibujar waveform en canvas
  const drawWaveform = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const width = canvas.width
    const height = canvas.height
    ctx.clearRect(0, 0, width, height)

    const barWidth = Math.floor(width / BAR_COUNT) - 2
    const analyser = analyserRef.current

    let dataArray: Uint8Array

    if (analyser) {
      dataArray = new Uint8Array(analyser.frequencyBinCount)
      analyser.getByteFrequencyData(dataArray)
    } else {
      // Animación genérica cuando no hay acceso al micrófono
      dataArray = new Uint8Array(BAR_COUNT).fill(0).map((_, i) =>
        Math.floor(128 + 80 * Math.sin(Date.now() / 200 + i * 0.5))
      )
    }

    for (let i = 0; i < BAR_COUNT; i++) {
      const dataIndex = Math.floor((i / BAR_COUNT) * dataArray.length)
      const normalized = (dataArray[dataIndex] || 0) / 255
      const barHeight = BAR_MIN_HEIGHT + normalized * (BAR_MAX_HEIGHT - BAR_MIN_HEIGHT)

      const gradient = ctx.createLinearGradient(0, height - barHeight, 0, height)
      gradient.addColorStop(0, '#4FC3F7')
      gradient.addColorStop(1, '#0288D1')

      ctx.fillStyle = gradient
      ctx.beginPath()
      ctx.roundRect(
        i * (barWidth + 2),
        height / 2 - barHeight / 2,
        barWidth,
        barHeight,
        2
      )
      ctx.fill()
    }

    animFrameRef.current = requestAnimationFrame(drawWaveform)
  }, [])

  useEffect(() => {
    if (micState === 'recording') {
      animFrameRef.current = requestAnimationFrame(drawWaveform)
    } else {
      if (animFrameRef.current) {
        cancelAnimationFrame(animFrameRef.current)
        animFrameRef.current = null
      }
    }
    return () => {
      if (animFrameRef.current) {
        cancelAnimationFrame(animFrameRef.current)
      }
    }
  }, [micState, drawWaveform])

  if (!visible) return null

  return (
    <div
      data-testid="voice-waveform"
      data-state={micState}
      style={{
        position: 'fixed',
        bottom: 32,
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 500,
        background: 'rgba(13, 17, 23, 0.92)',
        border: '1px solid #30363D',
        borderRadius: 16,
        padding: '16px 24px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 10,
        minWidth: 280,
        backdropFilter: 'blur(8px)',
        animation: 'waveform-appear 0.2s ease',
      }}
    >
      <style>{`
        @keyframes waveform-appear {
          from { opacity: 0; transform: translateX(-50%) translateY(10px); }
          to { opacity: 1; transform: translateX(-50%) translateY(0); }
        }
      `}</style>

      {/* Status text */}
      <div
        data-testid="waveform-status"
        style={{
          fontSize: 13,
          color: micState === 'recording' ? '#4FC3F7' : '#FFD600',
          fontWeight: 600,
          letterSpacing: 0.5,
        }}
      >
        {micState === 'recording' ? '🎙 Te escucho...' : '⚙ Procesando...'}
      </div>

      {/* Canvas del waveform */}
      {micState === 'recording' && (
        <canvas
          ref={canvasRef}
          data-testid="waveform-canvas"
          width={BAR_COUNT * 6}
          height={BAR_MAX_HEIGHT + 8}
          style={{ display: 'block' }}
        />
      )}

      {/* Transcripción en tiempo real */}
      {transcript && (
        <div
          data-testid="waveform-transcript"
          style={{
            fontSize: 14,
            color: '#C9D1D9',
            maxWidth: 360,
            textAlign: 'center',
            fontStyle: 'italic',
          }}
        >
          "{transcript}"
        </div>
      )}
    </div>
  )
}
