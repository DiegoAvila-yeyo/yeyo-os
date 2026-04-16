/**
 * YeyoOS — StatusBoard
 * HTML overlay showing real-time observatory metrics on top of game canvas.
 */
'use client'

import React, { useRef, useEffect } from 'react'

export interface ObservatoryMetrics {
  workflows_active: number
  agents_active: number
  total_events: number
  events_per_min: number
}

interface StatusBoardProps {
  metrics: ObservatoryMetrics
}

const EMPTY_METRICS: ObservatoryMetrics = {
  workflows_active: 0,
  agents_active: 0,
  total_events: 0,
  events_per_min: 0,
}

export function StatusBoard({ metrics = EMPTY_METRICS }: StatusBoardProps) {
  const prevRef = useRef<ObservatoryMetrics>(metrics)
  const pulseRef = useRef<Set<string>>(new Set())
  const [, forceRender] = React.useState(0)

  useEffect(() => {
    const changed = new Set<string>()
    const prev = prevRef.current
    if (prev.workflows_active !== metrics.workflows_active) changed.add('workflows_active')
    if (prev.agents_active !== metrics.agents_active) changed.add('agents_active')
    if (prev.total_events !== metrics.total_events) changed.add('total_events')
    if (prev.events_per_min !== metrics.events_per_min) changed.add('events_per_min')
    prevRef.current = metrics

    if (changed.size > 0) {
      pulseRef.current = changed
      forceRender((n) => n + 1)
      const timer = setTimeout(() => {
        pulseRef.current = new Set()
        forceRender((n) => n + 1)
      }, 600)
      return () => clearTimeout(timer)
    }
  }, [metrics])

  const rows: Array<{ key: keyof ObservatoryMetrics; label: string; icon: string }> = [
    { key: 'workflows_active', label: 'Workflows', icon: '⚙️' },
    { key: 'agents_active', label: 'Agents', icon: '🤖' },
    { key: 'total_events', label: 'Events', icon: '📨' },
    { key: 'events_per_min', label: 'Evt/min', icon: '⚡' },
  ]

  return (
    <div
      style={{
        position: 'absolute',
        top: 8,
        right: 8,
        background: 'rgba(6, 11, 24, 0.85)',
        border: '1px solid #1E3A5F',
        borderRadius: 6,
        padding: '6px 10px',
        pointerEvents: 'none',
        zIndex: 10,
        minWidth: 130,
      }}
    >
      <div
        style={{
          fontSize: 10,
          fontWeight: 600,
          color: '#4FC3F7',
          textTransform: 'uppercase',
          letterSpacing: 1,
          marginBottom: 4,
          textAlign: 'center',
        }}
      >
        Observatory
      </div>

      {rows.map(({ key, label, icon }) => {
        const isPulsing = pulseRef.current.has(key)
        return (
          <div
            key={key}
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              fontSize: 11,
              lineHeight: '18px',
              color: '#B0BEC5',
              transition: 'color 0.3s',
              ...(isPulsing ? { color: '#4FC3F7' } : {}),
            }}
          >
            <span>
              {icon} {label}
            </span>
            <span
              style={{
                fontWeight: 600,
                fontVariantNumeric: 'tabular-nums',
                color: isPulsing ? '#fff' : '#B0BEC5',
                transition: 'color 0.3s',
              }}
            >
              {metrics[key]}
            </span>
          </div>
        )
      })}
    </div>
  )
}

export default StatusBoard
