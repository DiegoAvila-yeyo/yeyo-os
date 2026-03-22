/**
 * YeyoOS — MicIndicator
 * Micro-fase 5.27 — Capa 5: Órganos
 *
 * Punto de 10px en el topbar que indica el estado del micrófono.
 * Colores y animaciones por estado. Click = toggle micrófono.
 * Se conecta via WebSocket /ws/voice para recibir cambios de estado.
 */

import React, { useEffect, useRef } from 'react'
import { useVoiceStore, MicState } from '../../stores/voiceStore'

const STATE_CONFIG: Record<MicState, { color: string; size: number; animation: string; tooltip: string }> = {
  idle: {
    color: '#2EA043',
    size: 10,
    animation: 'mic-pulse-slow 2s ease-in-out infinite',
    tooltip: 'Micrófono activo — Di "Yeyo" para hablar',
  },
  listening: {
    color: '#4FC3F7',
    size: 14,
    animation: 'mic-pulse-fast 0.5s ease-in-out infinite',
    tooltip: 'Escuchando... Di "Yeyo" para hablar',
  },
  recording: {
    color: '#4FC3F7',
    size: 14,
    animation: 'mic-pulse-fast 0.5s ease-in-out infinite',
    tooltip: 'Grabando tu voz...',
  },
  processing: {
    color: '#FFD600',
    size: 12,
    animation: 'mic-spin 0.8s linear infinite',
    tooltip: 'Procesando...',
  },
  speaking: {
    color: '#ffffff',
    size: 12,
    animation: 'none',
    tooltip: 'YEYO está hablando',
  },
  disabled: {
    color: '#484F58',
    size: 10,
    animation: 'none',
    tooltip: 'Micrófono desactivado — Click para activar',
  },
}

export function MicIndicator() {
  const { micState, isEnabled, toggleMic, setMicState } = useVoiceStore()
  const wsRef = useRef<WebSocket | null>(null)

  // Conectar WebSocket /ws/voice
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/voice`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'mic_state') {
          setMicState(data.state as MicState)
        }
      } catch {
        // Ignorar mensajes malformados
      }
    }

    ws.onclose = () => {
      // Reconectar en 3s
      setTimeout(() => {
        if (wsRef.current?.readyState === WebSocket.CLOSED) {
          // El useEffect cleanup y re-mount no aplica aquí —
          // en producción usar un manager de reconexión (como en Capa 3.12)
        }
      }, 3000)
    }

    return () => {
      ws.close()
      wsRef.current = null
    }
  }, [setMicState])

  const config = STATE_CONFIG[micState] || STATE_CONFIG.idle

  return (
    <>
      <style>{`
        @keyframes mic-pulse-slow {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.6; transform: scale(0.85); }
        }
        @keyframes mic-pulse-fast {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.5; transform: scale(1.2); }
        }
        @keyframes mic-spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .mic-indicator-dot:hover .mic-indicator-tooltip {
          opacity: 1;
          transform: translateX(-50%) translateY(0);
        }
      `}</style>

      <div
        className="mic-indicator-dot"
        data-testid="mic-indicator"
        data-state={micState}
        onClick={toggleMic}
        title={config.tooltip}
        style={{
          position: 'relative',
          width: config.size,
          height: config.size,
          borderRadius: '50%',
          background: config.color,
          animation: config.animation,
          cursor: 'pointer',
          transition: 'width 0.2s, height 0.2s, background 0.3s',
          flexShrink: 0,
        }}
      >
        {/* Tooltip */}
        <div
          className="mic-indicator-tooltip"
          style={{
            position: 'absolute',
            top: '100%',
            left: '50%',
            transform: 'translateX(-50%) translateY(4px)',
            background: '#161B22',
            border: '1px solid #30363D',
            borderRadius: 6,
            padding: '5px 10px',
            fontSize: 12,
            color: '#C9D1D9',
            whiteSpace: 'nowrap',
            pointerEvents: 'none',
            opacity: 0,
            transition: 'opacity 0.15s, transform 0.15s',
            zIndex: 1000,
            marginTop: 6,
          }}
        >
          {config.tooltip}
        </div>
      </div>
    </>
  )
}
