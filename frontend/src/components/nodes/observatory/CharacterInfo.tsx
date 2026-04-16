/**
 * YeyoOS — CharacterInfo
 * Shows character details when a character sprite is clicked in the game.
 */
'use client'

import React, { useEffect, useState } from 'react'

export interface AgentState {
  name: string
  status: string
  building: string
  last_event?: string
  event_count?: number
  color?: string
}

interface CharacterInfoProps {
  characterName: string | null
  agents: AgentState[]
  events?: Array<{ agent_name: string; event_type: string; data?: Record<string, unknown>; building?: string }>
  onClose: () => void
}

export function CharacterInfo({ characterName, agents, events = [], onClose }: CharacterInfoProps) {
  const [visible, setVisible] = useState(false)
  const miniCanvasRef = React.useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    if (characterName) {
      // Double rAF for smoother slide-in trigger
      requestAnimationFrame(() => requestAnimationFrame(() => setVisible(true)))
    } else {
      setVisible(false)
    }
  }, [characterName])

  // Draw mini sprite preview
  useEffect(() => {
    if (!characterName || !miniCanvasRef.current) return
    const canvas = miniCanvasRef.current
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => {
      ctx.clearRect(0, 0, 48, 48)
      ctx.imageSmoothingEnabled = false
      ctx.drawImage(img, 0, 0, 16, 16, 0, 0, 48, 48)
    }
    img.src = `/sprites/characters/${characterName}/Idle.png`
  }, [characterName])

  if (!characterName) return null

  const recentEvents = events
    .filter((e) => e.agent_name.toLowerCase() === characterName.toLowerCase())
    .slice(-5)
    .reverse()

  const tasksCompleted = events.filter(
    (e) => e.agent_name.toLowerCase() === characterName.toLowerCase() && e.event_type === 'task_complete'
  ).length

  const agent = agents.find(
    (a) => a.name.toLowerCase() === characterName.toLowerCase(),
  )

  const displayName = characterName.charAt(0).toUpperCase() + characterName.slice(1)

  const statusColor: Record<string, string> = {
    idle: '#B0BEC5',
    working: '#4FC3F7',
    walking: '#F59E0B',
    error: '#EF4444',
    dead: '#555',
  }

  const agentStatus = agent?.status ?? 'idle'
  const dotColor = statusColor[agentStatus] ?? '#B0BEC5'

  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        right: 0,
        bottom: 0,
        width: 220,
        background: '#060B18',
        borderLeft: '1px solid #1E3A5F',
        transform: visible ? 'translateX(0)' : 'translateX(100%)',
        transition: 'transform 0.35s cubic-bezier(0.16, 1, 0.3, 1)',
        zIndex: 20,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '10px 12px',
          borderBottom: '1px solid #1E3A5F',
        }}
      >
        <span style={{ fontSize: 13, fontWeight: 600, color: '#fff' }}>{displayName}</span>
        <button
          onClick={onClose}
          style={{
            background: 'none',
            border: 'none',
            color: '#556',
            cursor: 'pointer',
            fontSize: 16,
            lineHeight: 1,
            padding: '2px 4px',
          }}
          aria-label="Close"
        >
          ✕
        </button>
      </div>

      {/* Sprite preview */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          padding: '12px 0',
          borderBottom: '1px solid #1E3A5F',
        }}
      >
        <canvas
          ref={miniCanvasRef}
          width={48}
          height={48}
          style={{
            width: 48,
            height: 48,
            borderRadius: 8,
            background: agent?.color ?? '#1E3A5F',
            imageRendering: 'pixelated',
          }}
        />
      </div>

      {/* Details */}
      <div style={{ flex: 1, padding: '10px 12px', fontSize: 12, color: '#B0BEC5', overflowY: 'auto' }}>
        <Row label="Status">
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                background: dotColor,
                display: 'inline-block',
                boxShadow: `0 0 4px ${dotColor}`,
              }}
            />
            {agentStatus}
          </span>
        </Row>
        <Row label="Building">{agent?.building ?? '—'}</Row>
        <Row label="Tasks Done">
          <span style={{ fontVariantNumeric: 'tabular-nums', color: '#4FC3F7' }}>{tasksCompleted}</span>
        </Row>
        <Row label="Total Events">
          <span style={{ fontVariantNumeric: 'tabular-nums' }}>{agent?.event_count ?? 0}</span>
        </Row>
        <Row label="Last Event">{agent?.last_event ?? '—'}</Row>

        {/* Recent events */}
        <div
          style={{
            marginTop: 10,
            fontSize: 10,
            fontWeight: 600,
            color: agent?.color ?? '#4FC3F7',
            textTransform: 'uppercase',
            letterSpacing: 0.8,
          }}
        >
          Recent Activity
        </div>
        {recentEvents.length === 0 ? (
          <div style={{ fontSize: 11, color: '#445', fontStyle: 'italic', marginTop: 4 }}>
            No recent activity
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 3, marginTop: 4 }}>
            {recentEvents.map((e, i) => (
              <div
                key={i}
                style={{
                  fontSize: 10,
                  color: '#8899AA',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                }}
              >
                <span
                  style={{
                    width: 4,
                    height: 4,
                    borderRadius: '50%',
                    background: agent?.color ?? '#4FC3F7',
                    flexShrink: 0,
                  }}
                />
                <span>{e.event_type}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '5px 0',
        borderBottom: '1px solid rgba(30, 58, 95, 0.4)',
      }}
    >
      <span style={{ color: '#556' }}>{label}</span>
      <span style={{ color: '#fff' }}>{children}</span>
    </div>
  )
}

export default CharacterInfo
