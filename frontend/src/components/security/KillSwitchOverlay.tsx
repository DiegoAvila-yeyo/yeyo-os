/**
 * YeyoOS — KillSwitchOverlay
 * Micro-fase 3.21 — Capa 3: Cuerpo
 *
 * Overlay visual del Kill Switch (Ctrl+Alt+K).
 * Se registra ANTES que cualquier otro componente en el árbol React.
 * Borde rojo fijo (no pulsa), overlay negro semitransparente, ⛔ SISTEMA EN PAUSA.
 */

import React, { useEffect, useCallback } from 'react'
import { useSecurityStore } from '../../stores/securityStore'

export function KillSwitchOverlay() {
  const { killSwitchActive, toggleKillSwitch, cancelledTasks, suspendedProcesses } = useSecurityStore()

  // CRÍTICO: registrar Ctrl+Alt+K con capture=true, antes que cualquier otro listener
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.ctrlKey && e.altKey && e.key === 'k') {
        e.preventDefault()
        e.stopImmediatePropagation()
        toggleKillSwitch()
      }
    },
    [toggleKillSwitch]
  )

  useEffect(() => {
    // capture: true asegura que este listener se dispara PRIMERO
    window.addEventListener('keydown', handleKeyDown, { capture: true })
    return () => window.removeEventListener('keydown', handleKeyDown, { capture: true })
  }, [handleKeyDown])

  if (!killSwitchActive) return null

  return (
    <>
      <style>{`
        @keyframes kill-border-pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.6; }
        }
      `}</style>

      {/* Borde rojo fijo alrededor de toda la pantalla */}
      <div
        data-testid="kill-switch-border"
        style={{
          position: 'fixed',
          inset: 0,
          pointerEvents: 'none',
          zIndex: 9998,
          boxShadow: 'inset 0 0 0 5px #FF1744',
          // Borde fijo, sin pulso
        }}
      />

      {/* Overlay semitransparente */}
      <div
        data-testid="kill-switch-overlay"
        style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0,0,0,0.82)',
          zIndex: 9999,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          fontFamily: 'Inter, system-ui, sans-serif',
          color: '#fff',
          gap: 20,
        }}
      >
        {/* Icono y título */}
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 72, marginBottom: 12 }}>⛔</div>
          <div
            data-testid="kill-switch-title"
            style={{
              fontSize: 28,
              fontWeight: 800,
              letterSpacing: 4,
              color: '#FF1744',
              textTransform: 'uppercase',
            }}
          >
            SISTEMA EN PAUSA
          </div>
        </div>

        {/* Contadores */}
        <div
          data-testid="kill-switch-counters"
          style={{
            display: 'flex',
            gap: 32,
            background: '#1A0A0A',
            border: '1px solid #FF174444',
            borderRadius: 10,
            padding: '16px 32px',
          }}
        >
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 800, color: '#FF6B6B' }}>{cancelledTasks}</div>
            <div style={{ fontSize: 12, color: '#8B949E', marginTop: 4 }}>Tareas canceladas</div>
          </div>
          <div style={{ width: 1, background: '#FF174433' }} />
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 800, color: '#FF6B6B' }}>{suspendedProcesses}</div>
            <div style={{ fontSize: 12, color: '#8B949E', marginTop: 4 }}>Procesos suspendidos</div>
          </div>
        </div>

        {/* Botones */}
        <div style={{ display: 'flex', gap: 12, marginTop: 8 }}>
          <button
            data-testid="resume-btn"
            onClick={toggleKillSwitch}
            style={{
              background: '#FF1744',
              border: 'none',
              color: '#fff',
              borderRadius: 8,
              padding: '13px 32px',
              fontWeight: 700,
              fontSize: 15,
              cursor: 'pointer',
              letterSpacing: 0.5,
            }}
          >
            ▶ Reanudar
          </button>
          <button
            data-testid="view-activity-btn"
            onClick={() => {/* abre log de actividad */}}
            style={{
              background: 'transparent',
              border: '1px solid #30363D',
              color: '#C9D1D9',
              borderRadius: 8,
              padding: '13px 24px',
              fontWeight: 500,
              fontSize: 15,
              cursor: 'pointer',
            }}
          >
            Ver qué estaba haciendo
          </button>
        </div>

        <div style={{ fontSize: 13, color: '#8B949E', marginTop: 4 }}>
          Ctrl+Alt+K para reanudar
        </div>
      </div>
    </>
  )
}
