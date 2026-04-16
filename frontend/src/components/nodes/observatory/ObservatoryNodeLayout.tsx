/**
 * YeyoOS — Observatory Node Layout
 * 3-tab layout: Town (game view), Arena (battle view), Metrics (dashboard)
 */
'use client'

import React, { useState, useEffect, useRef, useCallback } from 'react'
import { GameCanvas } from './GameCanvas'
import { StatusBoard, ObservatoryMetrics } from './StatusBoard'
import { CharacterInfo, AgentState } from './CharacterInfo'
import { ActivityLog } from './ActivityLog'
import { ArenaView } from './ArenaView'
import type { GameEvent } from './game/GameEngine'
import { BUILDINGS } from './game/TileMap'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type TabId = 'town' | 'arena' | 'metrics'

interface Tab {
  id: TabId
  label: string
}

const TABS: Tab[] = [
  { id: 'town', label: '🏭 Town' },
  { id: 'arena', label: '⚔️ Arena' },
  { id: 'metrics', label: '📊 Metrics' },
]

// ---------------------------------------------------------------------------
// Building descriptions & popup
// ---------------------------------------------------------------------------

const BUILDING_DESCRIPTIONS: Record<string, string> = {
  'Workflow Factory': 'Central hub for orchestrating multi-agent workflows and task pipelines.',
  'Error Mine': 'Deep excavation of bugs and errors — miners extract issues from the codebase.',
  'Lab': 'Research facility where scientists analyse code patterns and run experiments.',
  'Library': 'Archive of documentation, knowledge, and written artifacts.',
  'Gym': 'Testing grounds where testers exercise code through rigorous workouts.',
  'Security Station': 'Perimeter defense and security auditing headquarters.',
  'Pattern Palace': 'Hall of architectural patterns, optimisations, and sage wisdom.',
}

const AGENT_BUILDING_MAP: Record<string, string> = {
  miner: 'Error Mine',
  scientist: 'Lab',
  tester: 'Gym',
  writer: 'Library',
  optimizer: 'Pattern Palace',
  guard: 'Security Station',
  sage: 'Pattern Palace',
  robot: 'Workflow Factory',
}

function BuildingPopup({
  buildingName,
  events,
  onClose,
}: {
  buildingName: string
  events: GameEvent[]
  onClose: () => void
}) {
  const def = BUILDINGS.find((b) => b.name === buildingName)
  if (!def) return null

  const description = BUILDING_DESCRIPTIONS[buildingName] ?? 'A building in the observatory town.'
  const recentEvents = events
    .filter((e) => {
      return e.building === buildingName || AGENT_BUILDING_MAP[e.agent_name] === buildingName
    })
    .slice(-5)
    .reverse()

  return (
    <div
      style={{
        position: 'absolute',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        background: 'rgba(6, 11, 24, 0.95)',
        border: `1px solid ${def.color}44`,
        borderRadius: 12,
        padding: 0,
        zIndex: 30,
        width: 280,
        maxHeight: 340,
        overflow: 'hidden',
        boxShadow: `0 0 24px ${def.color}22, 0 8px 32px rgba(0,0,0,0.6)`,
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 14px',
          borderBottom: `1px solid ${def.color}33`,
          background: `${def.color}11`,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 20 }}>{def.icon}</span>
          <span style={{ fontSize: 14, fontWeight: 700, color: '#fff' }}>{def.name}</span>
        </div>
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

      {/* Description */}
      <div style={{ padding: '10px 14px', fontSize: 11, color: '#8899AA', lineHeight: 1.5 }}>
        {description}
      </div>

      {/* Recent activities */}
      <div style={{ padding: '0 14px 12px' }}>
        <div
          style={{
            fontSize: 10,
            fontWeight: 600,
            color: def.color,
            textTransform: 'uppercase',
            letterSpacing: 0.8,
            marginBottom: 6,
          }}
        >
          Recent Activity
        </div>
        {recentEvents.length === 0 ? (
          <div style={{ fontSize: 11, color: '#445', fontStyle: 'italic' }}>No recent activity</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {recentEvents.map((e, i) => (
              <div
                key={i}
                style={{
                  fontSize: 11,
                  color: '#B0BEC5',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                }}
              >
                <span
                  style={{
                    width: 5,
                    height: 5,
                    borderRadius: '50%',
                    background: def.color,
                    flexShrink: 0,
                  }}
                />
                <span style={{ color: '#fff', fontWeight: 500 }}>{e.agent_name}</span>
                <span style={{ color: '#667' }}>·</span>
                <span>{e.event_type}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Metrics view (embedded)
// ---------------------------------------------------------------------------

function MetricsView({ metrics, agents }: { metrics: ObservatoryMetrics; agents: AgentState[] }) {
  const cards: Array<{ label: string; value: number | string; color: string }> = [
    { label: 'Active Workflows', value: metrics.workflows_active, color: '#6366F1' },
    { label: 'Active Agents', value: metrics.agents_active, color: '#4FC3F7' },
    { label: 'Total Events', value: metrics.total_events, color: '#10B981' },
    { label: 'Events / min', value: metrics.events_per_min, color: '#F59E0B' },
  ]

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
      {/* Metric cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 12 }}>
        {cards.map((c) => (
          <div
            key={c.label}
            style={{
              background: '#0A0E1A',
              border: '1px solid #1E3A5F',
              borderRadius: 8,
              padding: '12px 14px',
            }}
          >
            <div style={{ fontSize: 11, color: '#556', textTransform: 'uppercase', letterSpacing: 0.5 }}>
              {c.label}
            </div>
            <div style={{ fontSize: 24, fontWeight: 700, color: c.color, marginTop: 4, fontVariantNumeric: 'tabular-nums' }}>
              {c.value}
            </div>
          </div>
        ))}
      </div>

      {/* Agent table */}
      <div style={{ marginTop: 20 }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: '#4FC3F7', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 }}>
          Agent Status
        </div>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12, color: '#B0BEC5' }}>
          <thead>
            <tr>
              {['Name', 'Status', 'Building', 'Events'].map((h) => (
                <th
                  key={h}
                  style={{
                    textAlign: 'left',
                    padding: '6px 8px',
                    borderBottom: '1px solid #1E3A5F',
                    color: '#556',
                    fontWeight: 500,
                  }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {agents.map((a) => (
              <tr key={a.name}>
                <td style={{ padding: '5px 8px', borderBottom: '1px solid rgba(30,58,95,0.3)', color: '#fff' }}>
                  {a.name}
                </td>
                <td style={{ padding: '5px 8px', borderBottom: '1px solid rgba(30,58,95,0.3)' }}>
                  <StatusDot status={a.status} />
                </td>
                <td style={{ padding: '5px 8px', borderBottom: '1px solid rgba(30,58,95,0.3)' }}>{a.building || '—'}</td>
                <td style={{ padding: '5px 8px', borderBottom: '1px solid rgba(30,58,95,0.3)', fontVariantNumeric: 'tabular-nums' }}>
                  {a.event_count ?? 0}
                </td>
              </tr>
            ))}
            {agents.length === 0 && (
              <tr>
                <td colSpan={4} style={{ padding: 16, textAlign: 'center', color: '#445' }}>
                  No agents connected
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function StatusDot({ status }: { status: string }) {
  const colors: Record<string, string> = {
    idle: '#B0BEC5',
    working: '#4FC3F7',
    walking: '#F59E0B',
    error: '#EF4444',
  }
  const c = colors[status] ?? '#B0BEC5'
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
      <span
        style={{
          width: 7,
          height: 7,
          borderRadius: '50%',
          background: c,
          display: 'inline-block',
          boxShadow: `0 0 4px ${c}`,
        }}
      />
      {status}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Main Layout
// ---------------------------------------------------------------------------

export function ObservatoryNodeLayout() {
  const [activeTab, setActiveTab] = useState<TabId>('town')
  const [events, setEvents] = useState<GameEvent[]>([])
  const [selectedCharacter, setSelectedCharacter] = useState<string | null>(null)
  const [selectedBuilding, setSelectedBuilding] = useState<string | null>(null)
  const [metrics, setMetrics] = useState<ObservatoryMetrics>({
    workflows_active: 0,
    agents_active: 0,
    total_events: 0,
    events_per_min: 0,
  })
  const [agents, setAgents] = useState<AgentState[]>([])
  const wsRef = useRef<WebSocket | null>(null)

  // ---- WebSocket ----
  useEffect(() => {
    let ws: WebSocket | null = null
    let reconnectTimer: ReturnType<typeof setTimeout>

    function connect() {
      try {
        ws = new WebSocket('ws://localhost:8000/api/v1/observatory/live')

        ws.onmessage = (msg) => {
          try {
            const event: GameEvent = JSON.parse(msg.data)
            setEvents((prev) => [...prev, event])
          } catch {
            // ignore non-JSON frames
          }
        }

        ws.onclose = () => {
          reconnectTimer = setTimeout(connect, 3000)
        }

        ws.onerror = () => {
          ws?.close()
        }

        wsRef.current = ws
      } catch {
        reconnectTimer = setTimeout(connect, 3000)
      }
    }

    connect()

    return () => {
      clearTimeout(reconnectTimer)
      ws?.close()
      wsRef.current = null
    }
  }, [])

  // ---- Fetch initial data ----
  useEffect(() => {
    async function fetchInitialData() {
      try {
        const [metricsRes, agentsRes] = await Promise.all([
          fetch('/api/v1/observatory/metrics').catch(() => null),
          fetch('/api/v1/observatory/agents').catch(() => null),
        ])
        if (metricsRes?.ok) {
          const data = await metricsRes.json()
          setMetrics(data)
        }
        if (agentsRes?.ok) {
          const data = await agentsRes.json()
          setAgents(data)
        }
      } catch {
        // API may not be available yet — that's fine
      }
    }

    fetchInitialData()
  }, [])

  // Update metrics from events
  useEffect(() => {
    if (events.length === 0) return
    setMetrics((prev) => ({ ...prev, total_events: events.length }))
  }, [events.length])

  const handleCharacterClick = useCallback((name: string) => {
    setSelectedCharacter(name)
    setSelectedBuilding(null)
  }, [])

  const handleBuildingClick = useCallback((name: string) => {
    setSelectedBuilding(name)
    setSelectedCharacter(null)
  }, [])

  const handleCloseCharacterInfo = useCallback(() => {
    setSelectedCharacter(null)
  }, [])

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        width: '100%',
        backgroundColor: '#060B18',
        color: '#B0BEC5',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        overflow: 'hidden',
      }}
    >
      {/* Tab bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 2,
          padding: '6px 8px',
          borderBottom: '1px solid #1E3A5F',
          flexShrink: 0,
        }}
      >
        {TABS.map((tab) => {
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                background: isActive ? '#1E3A5F' : 'transparent',
                color: isActive ? '#fff' : '#556',
                border: isActive ? '1px solid #4FC3F7' : '1px solid transparent',
                borderRadius: 4,
                padding: '5px 14px',
                fontSize: 12,
                fontWeight: isActive ? 600 : 400,
                cursor: 'pointer',
                transition: 'all 0.15s',
              }}
            >
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* Tab content */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {activeTab === 'town' && (
          <TownTab
            events={events}
            metrics={metrics}
            agents={agents}
            selectedCharacter={selectedCharacter}
            selectedBuilding={selectedBuilding}
            onCharacterClick={handleCharacterClick}
            onBuildingClick={handleBuildingClick}
            onCloseCharacterInfo={handleCloseCharacterInfo}
            onCloseBuildingInfo={() => setSelectedBuilding(null)}
          />
        )}

        {activeTab === 'arena' && <ArenaView />}

        {activeTab === 'metrics' && <MetricsView metrics={metrics} agents={agents} />}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Town tab sub-layout
// ---------------------------------------------------------------------------

function TownTab({
  events,
  metrics,
  agents,
  selectedCharacter,
  selectedBuilding,
  onCharacterClick,
  onBuildingClick,
  onCloseCharacterInfo,
  onCloseBuildingInfo,
}: {
  events: GameEvent[]
  metrics: ObservatoryMetrics
  agents: AgentState[]
  selectedCharacter: string | null
  selectedBuilding: string | null
  onCharacterClick: (name: string) => void
  onBuildingClick: (name: string) => void
  onCloseCharacterInfo: () => void
  onCloseBuildingInfo: () => void
}) {
  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Game area + overlays */}
      <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
        <GameCanvas
          events={events}
          onCharacterClick={onCharacterClick}
          onBuildingClick={onBuildingClick}
        />
        <StatusBoard metrics={metrics} />
        <CharacterInfo
          characterName={selectedCharacter}
          agents={agents}
          events={events}
          onClose={onCloseCharacterInfo}
        />
        {selectedBuilding && (
          <BuildingPopup
            buildingName={selectedBuilding}
            events={events}
            onClose={onCloseBuildingInfo}
          />
        )}
      </div>

      {/* Activity log (bottom strip) */}
      <div style={{ height: 160, flexShrink: 0 }}>
        <ActivityLog events={events} maxItems={20} />
      </div>
    </div>
  )
}

export default ObservatoryNodeLayout
