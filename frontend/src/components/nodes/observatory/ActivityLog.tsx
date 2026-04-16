/**
 * YeyoOS — ActivityLog
 * Scrollable log of recent observatory events.
 */
'use client'

import React, { useRef, useEffect } from 'react'
import type { GameEvent } from './game/GameEngine'

interface ActivityLogProps {
  events: GameEvent[]
  maxItems?: number
}

const AGENT_EMOJI: Record<string, string> = {
  miner: '⛏️',
  scientist: '🔬',
  tester: '🧪',
  writer: '✏️',
  optimizer: '🏋️',
  guard: '🛡️',
  sage: '📖',
  robot: '🤖',
}

const TYPE_COLORS: Record<string, string> = {
  task_complete: '#10B981',
  error: '#EF4444',
  task_start: '#4FC3F7',
  idle: '#556',
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function describeEvent(evt: GameEvent): string {
  switch (evt.event_type) {
    case 'task_start':
      return evt.building ? `→ ${evt.building}` : 'started task'
    case 'task_complete':
      return '✅ done'
    case 'error':
      return '❌ error'
    case 'idle':
      return '💤 idle'
    default:
      return evt.event_type
  }
}

export function ActivityLog({ events, maxItems = 20 }: ActivityLogProps) {
  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to top (newest) when new events arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = 0
    }
  }, [events.length])

  const visibleEvents = events.slice(-maxItems).reverse()

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        background: '#060B18',
        borderTop: '1px solid #1E3A5F',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '6px 10px',
          fontSize: 11,
          fontWeight: 600,
          color: '#4FC3F7',
          textTransform: 'uppercase',
          letterSpacing: 1,
          borderBottom: '1px solid #1E3A5F',
          flexShrink: 0,
        }}
      >
        📋 Activity Log
      </div>

      {/* Scrollable list */}
      <div
        ref={scrollRef}
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '4px 0',
        }}
      >
        {visibleEvents.length === 0 && (
          <div style={{ textAlign: 'center', color: '#445', fontSize: 11, padding: 16 }}>
            No events yet…
          </div>
        )}

        {visibleEvents.map((evt, i) => {
          const color = TYPE_COLORS[evt.event_type] ?? '#B0BEC5'
          const emoji = AGENT_EMOJI[evt.agent_name.toLowerCase()] ?? '🔹'
          const now = new Date()
          return (
            <div
              key={`${evt.agent_name}-${evt.event_type}-${i}`}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '3px 10px',
                fontSize: 11,
                lineHeight: '16px',
                color: '#B0BEC5',
                borderBottom: '1px solid rgba(30, 58, 95, 0.25)',
              }}
            >
              <span style={{ color: '#445', fontSize: 10, flexShrink: 0, fontVariantNumeric: 'tabular-nums' }}>
                {formatTime(now)}
              </span>
              <span style={{ flexShrink: 0 }}>{emoji}</span>
              <span
                style={{
                  fontWeight: 500,
                  color: '#fff',
                  maxWidth: 70,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  flexShrink: 0,
                }}
              >
                {evt.agent_name}
              </span>
              <span style={{ color, flexShrink: 0 }}>{describeEvent(evt)}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default ActivityLog
