/**
 * YeyoOS — PermissionAlert
 * Micro-fase 3.21 — Capa 3: Cuerpo
 *
 * Popup de alerta de permisos con tres zonas de riesgo:
 * - Verde: NO renderiza nada (log silencioso)
 * - Amarilla: overlay semitransparente, borde pulsante amarillo, chat inline, 4 botones
 * - Roja: flash rojo, borde rojo intenso, campo "confirmo" obligatorio, 2 botones
 */

import React, { useState, useEffect, useRef, useCallback } from 'react'

export type PermissionZone = 'green' | 'yellow' | 'red'

export interface PermissionAlertProps {
  nodeName: string
  nodeIcon: string
  permission: string
  permissionLabel: string
  zone: PermissionZone
  taskDescription: string
  packageInfo?: { name: string; origin: string; size: string }
  onAllow: () => void
  onAllowAlways: () => void
  onDeny: () => void
  onAskMore: (question: string) => void
}

interface ChatMessage {
  role: 'user' | 'system'
  text: string
}

const ZONE_STYLES = {
  yellow: {
    overlay: 'rgba(0,0,0,0.60)',
    borderColor: '#FFD600',
    borderAnimation: 'pulse-yellow',
    borderWidth: 4,
  },
  red: {
    overlay: 'rgba(0,0,0,0.75)',
    borderColor: '#FF1744',
    borderAnimation: 'pulse-red',
    borderWidth: 5,
  },
}

export function PermissionAlert({
  nodeName,
  nodeIcon,
  permission,
  permissionLabel,
  zone,
  taskDescription,
  packageInfo,
  onAllow,
  onAllowAlways,
  onDeny,
  onAskMore,
}: PermissionAlertProps) {
  const [confirmText, setConfirmText] = useState('')
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
  const [chatInput, setChatInput] = useState('')
  const [showDetails, setShowDetails] = useState(false)
  const [flashActive, setFlashActive] = useState(false)
  const confirmRef = useRef<HTMLInputElement>(null)
  const chatInputRef = useRef<HTMLInputElement>(null)

  // Zona verde: no renderiza nada
  if (zone === 'green') return null

  // Zona roja: flash inicial 0.5s
  useEffect(() => {
    if (zone === 'red') {
      setFlashActive(true)
      const t = setTimeout(() => setFlashActive(false), 500)
      return () => clearTimeout(t)
    }
  }, [zone])

  const canProceedRed = confirmText.trim().toLowerCase() === 'confirmo'

  const handleChatSend = useCallback(() => {
    const q = chatInput.trim()
    if (!q || chatMessages.length >= 6) return
    const newMessages: ChatMessage[] = [...chatMessages, { role: 'user', text: q }]
    setChatMessages(newMessages)
    setChatInput('')
    onAskMore(q)
  }, [chatInput, chatMessages, onAskMore])

  const handleChatKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter') handleChatSend()
    },
    [handleChatSend]
  )

  const styles = ZONE_STYLES[zone as 'yellow' | 'red']

  return (
    <>
      {/* Estilos CSS para animaciones */}
      <style>{`
        @keyframes pulse-yellow {
          0%, 100% { box-shadow: inset 0 0 0 4px #FFD600, inset 0 0 20px rgba(255,214,0,0.3); }
          50% { box-shadow: inset 0 0 0 4px #FFD600, inset 0 0 40px rgba(255,214,0,0.7); }
        }
        @keyframes pulse-red {
          0%, 100% { box-shadow: inset 0 0 0 5px #FF1744, inset 0 0 20px rgba(255,23,68,0.4); }
          50% { box-shadow: inset 0 0 0 5px #FF1744, inset 0 0 50px rgba(255,23,68,0.8); }
        }
        @keyframes flash-red-bg {
          0% { background: rgba(255,23,68,0.4); }
          100% { background: rgba(0,0,0,0.75); }
        }
      `}</style>

      {/* Overlay de pantalla completa */}
      <div
        data-testid="permission-alert-overlay"
        data-zone={zone}
        style={{
          position: 'fixed',
          inset: 0,
          background: flashActive
            ? 'rgba(255,23,68,0.4)'
            : styles.overlay,
          animation: flashActive
            ? 'flash-red-bg 0.5s ease forwards'
            : undefined,
          zIndex: 9000,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      />

      {/* Borde pulsante de pantalla */}
      <div
        data-testid="permission-alert-border"
        style={{
          position: 'fixed',
          inset: 0,
          pointerEvents: 'none',
          zIndex: 9001,
          animation: `${styles.borderAnimation} ${zone === 'yellow' ? '2s' : '1s'} ease-in-out infinite`,
        }}
      />

      {/* Popup central */}
      <div
        data-testid="permission-alert-popup"
        style={{
          position: 'fixed',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          zIndex: 9002,
          background: '#0D1117',
          border: `2px solid ${styles.borderColor}`,
          borderRadius: 12,
          padding: '28px 32px',
          minWidth: 420,
          maxWidth: 560,
          boxShadow: `0 0 40px ${styles.borderColor}44`,
          fontFamily: 'Inter, system-ui, sans-serif',
          color: '#E0E6ED',
        }}
      >
        {/* Cabecera */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
          <span style={{ fontSize: 32 }}>{nodeIcon}</span>
          <div>
            <div style={{ fontWeight: 700, fontSize: 16, color: '#fff' }}>{nodeName}</div>
            <div style={{ fontSize: 13, color: '#8B949E' }}>solicita permiso</div>
          </div>
          {zone === 'red' && (
            <div
              data-testid="high-risk-badge"
              style={{
                marginLeft: 'auto',
                background: '#FF1744',
                color: '#fff',
                fontWeight: 800,
                fontSize: 11,
                padding: '4px 10px',
                borderRadius: 4,
                letterSpacing: 1,
              }}
            >
              ACCIÓN DE ALTO RIESGO
            </div>
          )}
        </div>

        {/* Permiso solicitado */}
        <div
          style={{
            background: zone === 'red' ? '#1A0A0A' : '#0F1923',
            border: `1px solid ${styles.borderColor}44`,
            borderRadius: 8,
            padding: '12px 16px',
            marginBottom: 16,
          }}
        >
          <div style={{ fontSize: 12, color: '#8B949E', marginBottom: 4, textTransform: 'uppercase', letterSpacing: 0.8 }}>
            Permiso
          </div>
          <div style={{ fontWeight: 600, fontSize: 15, color: zone === 'red' ? '#FF6B6B' : '#FFD600' }}>
            {permissionLabel}
          </div>
          <div style={{ fontSize: 12, color: '#8B949E', marginTop: 4, fontFamily: 'monospace' }}>
            {permission}
          </div>
        </div>

        {/* Tarea */}
        <div style={{ fontSize: 14, color: '#C9D1D9', marginBottom: 16 }}>
          <span style={{ color: '#8B949E' }}>Para: </span>
          {taskDescription}
        </div>

        {/* Info de paquete (zona roja) */}
        {zone === 'red' && packageInfo && (
          <div
            data-testid="package-info"
            style={{
              background: '#1A0A0A',
              border: '1px solid #FF174444',
              borderRadius: 8,
              padding: '10px 14px',
              marginBottom: 16,
              fontSize: 13,
            }}
          >
            <div style={{ color: '#8B949E', marginBottom: 4, fontSize: 11, textTransform: 'uppercase' }}>Paquete/Origen</div>
            <div>📦 <strong>{packageInfo.name}</strong></div>
            <div style={{ color: '#8B949E' }}>Origen: {packageInfo.origin}</div>
            <div style={{ color: '#8B949E' }}>Tamaño: {packageInfo.size}</div>
          </div>
        )}

        {/* Advertencia irreversible (zona roja) */}
        {zone === 'red' && (
          <div
            data-testid="irreversible-warning"
            style={{
              background: '#FF174422',
              border: '1px solid #FF1744',
              borderRadius: 6,
              padding: '8px 14px',
              marginBottom: 20,
              color: '#FF6B6B',
              fontWeight: 700,
              fontSize: 13,
              textAlign: 'center',
              letterSpacing: 0.5,
            }}
          >
            ⚠️ ESTO NO SE PUEDE DESHACER FÁCILMENTE
          </div>
        )}

        {/* Chat inline (zona amarilla, máx 3 turnos = 6 mensajes) */}
        {zone === 'yellow' && (
          <div
            data-testid="inline-chat"
            style={{ marginBottom: 20 }}
          >
            {chatMessages.length > 0 && (
              <div
                style={{
                  background: '#0F1923',
                  borderRadius: 8,
                  padding: '10px 12px',
                  marginBottom: 10,
                  maxHeight: 140,
                  overflowY: 'auto',
                }}
              >
                {chatMessages.map((msg, i) => (
                  <div
                    key={i}
                    style={{
                      marginBottom: 6,
                      textAlign: msg.role === 'user' ? 'right' : 'left',
                      fontSize: 13,
                      color: msg.role === 'user' ? '#4FC3F7' : '#C9D1D9',
                    }}
                  >
                    {msg.role === 'user' ? '👤 ' : '🤖 '}
                    {msg.text}
                  </div>
                ))}
              </div>
            )}
            {chatMessages.length < 6 && (
              <div style={{ display: 'flex', gap: 8 }}>
                <input
                  ref={chatInputRef}
                  data-testid="chat-input"
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={handleChatKeyDown}
                  placeholder="¿Por qué necesitas este permiso?"
                  style={{
                    flex: 1,
                    background: '#0F1923',
                    border: '1px solid #FFD60044',
                    borderRadius: 6,
                    color: '#E0E6ED',
                    padding: '7px 10px',
                    fontSize: 13,
                    outline: 'none',
                  }}
                />
                <button
                  onClick={handleChatSend}
                  style={{
                    background: '#FFD600',
                    color: '#000',
                    border: 'none',
                    borderRadius: 6,
                    padding: '7px 14px',
                    fontWeight: 700,
                    cursor: 'pointer',
                    fontSize: 13,
                  }}
                >
                  →
                </button>
              </div>
            )}
          </div>
        )}

        {/* Campo "confirmo" (zona roja) */}
        {zone === 'red' && (
          <div style={{ marginBottom: 20 }}>
            <div style={{ fontSize: 13, color: '#8B949E', marginBottom: 8 }}>
              Escribe <strong style={{ color: '#FF6B6B' }}>confirmo</strong> para continuar:
            </div>
            <input
              ref={confirmRef}
              data-testid="confirm-input"
              type="text"
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              placeholder="confirmo"
              autoFocus
              style={{
                width: '100%',
                background: '#0D0000',
                border: `1px solid ${canProceedRed ? '#FF1744' : '#FF174444'}`,
                borderRadius: 6,
                color: '#FF6B6B',
                padding: '10px 14px',
                fontSize: 15,
                outline: 'none',
                textAlign: 'center',
                letterSpacing: 2,
                fontWeight: 600,
                boxSizing: 'border-box',
              }}
            />
          </div>
        )}

        {/* Botones zona amarilla */}
        {zone === 'yellow' && (
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button
              data-testid="btn-allow-once"
              onClick={onAllow}
              style={{
                background: '#FFD60022',
                border: '1px solid #FFD600',
                color: '#FFD600',
                borderRadius: 6,
                padding: '9px 16px',
                fontWeight: 600,
                cursor: 'pointer',
                fontSize: 13,
                flex: 1,
              }}
            >
              Permitir esta vez
            </button>
            <button
              data-testid="btn-allow-always"
              onClick={onAllowAlways}
              style={{
                background: '#1B4332',
                border: '1px solid #2EA043',
                color: '#2EA043',
                borderRadius: 6,
                padding: '9px 16px',
                fontWeight: 600,
                cursor: 'pointer',
                fontSize: 13,
                flex: 1,
              }}
            >
              Siempre permitir
            </button>
            <button
              data-testid="btn-deny"
              onClick={onDeny}
              style={{
                background: '#1A0A0A',
                border: '1px solid #FF4444',
                color: '#FF6B6B',
                borderRadius: 6,
                padding: '9px 16px',
                fontWeight: 600,
                cursor: 'pointer',
                fontSize: 13,
                flex: 1,
              }}
            >
              Denegar
            </button>
            <button
              data-testid="btn-details"
              onClick={() => setShowDetails(!showDetails)}
              style={{
                background: 'transparent',
                border: '1px solid #30363D',
                color: '#8B949E',
                borderRadius: 6,
                padding: '9px 16px',
                cursor: 'pointer',
                fontSize: 13,
                flex: '0 0 auto',
              }}
            >
              Ver detalles técnicos
            </button>
          </div>
        )}

        {/* Botones zona roja */}
        {zone === 'red' && (
          <div style={{ display: 'flex', gap: 10 }}>
            <button
              data-testid="btn-proceed-red"
              onClick={onAllow}
              disabled={!canProceedRed}
              style={{
                flex: 1,
                background: canProceedRed ? '#FF1744' : '#FF174433',
                border: `1px solid ${canProceedRed ? '#FF1744' : '#FF174444'}`,
                color: canProceedRed ? '#fff' : '#FF174477',
                borderRadius: 6,
                padding: '11px 16px',
                fontWeight: 700,
                cursor: canProceedRed ? 'pointer' : 'not-allowed',
                fontSize: 14,
                transition: 'all 0.2s',
              }}
            >
              Entiendo, proceder
            </button>
            <button
              data-testid="btn-cancel-red"
              onClick={onDeny}
              style={{
                flex: 1,
                background: '#161B22',
                border: '1px solid #30363D',
                color: '#C9D1D9',
                borderRadius: 6,
                padding: '11px 16px',
                fontWeight: 600,
                cursor: 'pointer',
                fontSize: 14,
              }}
            >
              Cancelar todo
            </button>
          </div>
        )}

        {/* Detalles técnicos (expandible zona amarilla) */}
        {showDetails && (
          <div
            data-testid="technical-details"
            style={{
              marginTop: 16,
              padding: '10px 14px',
              background: '#0F1923',
              borderRadius: 8,
              fontSize: 12,
              fontFamily: 'monospace',
              color: '#8B949E',
            }}
          >
            <div><strong>nodo:</strong> {nodeName}</div>
            <div><strong>permiso:</strong> {permission}</div>
            <div><strong>zona:</strong> {zone}</div>
            <div><strong>tarea:</strong> {taskDescription}</div>
            {packageInfo && (
              <>
                <div><strong>paquete:</strong> {packageInfo.name}</div>
                <div><strong>origen:</strong> {packageInfo.origin}</div>
                <div><strong>tamaño:</strong> {packageInfo.size}</div>
              </>
            )}
          </div>
        )}
      </div>
    </>
  )
}
