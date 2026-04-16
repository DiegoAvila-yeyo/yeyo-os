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
  onClose: () => void
}

export function CharacterInfo({ characterName, agents, onClose }: CharacterInfoProps) {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    if (characterName) {
      // Trigger slide-in on next frame for CSS transition
      requestAnimationFrame(() => setVisible(true))
    } else {
      setVisible(false)
    }
  }, [characterName])

  if (!characterName) return null

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
        transition: 'transform 0.25s ease-out',
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

      {/* Sprite thumbnail placeholder */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          padding: '12px 0',
          borderBottom: '1px solid #1E3A5F',
        }}
      >
        <div
          style={{
            width: 48,
            height: 48,
            borderRadius: 8,
            background: agent?.color ?? '#1E3A5F',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 24,
          }}
        >
          🧑‍💻
        </div>
      </div>

      {/* Details */}
      <div style={{ flex: 1, padding: '10px 12px', fontSize: 12, color: '#B0BEC5' }}>
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
        <Row label="Last Event">{agent?.last_event ?? '—'}</Row>
        <Row label="Event Count">
          <span style={{ fontVariantNumeric: 'tabular-nums' }}>{agent?.event_count ?? 0}</span>
        </Row>
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
