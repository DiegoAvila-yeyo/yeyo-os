/**
 * YeyoOS — SecurityDashboard
 * Micro-fase 3.21 — Capa 3: Cuerpo
 *
 * Dashboard de seguridad: resumen de permisos, lista de nodos,
 * historial últimas 24h, drawer lateral por nodo.
 */

import React, { useState, useMemo } from 'react'
import { useSecurityStore, PermissionRecord, AccessLogEntry } from '../../stores/securityStore'

export function SecurityDashboard() {
  const { permissions, history, denyPermission } = useSecurityStore()
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)

  const now = Date.now()
  const last24h = useMemo(
    () => history.filter((e) => now - e.timestamp < 24 * 60 * 60 * 1000),
    [history, now]
  )

  const autoActive = useMemo(
    () => [...permissions.values()].flat().filter((p) => p.zone === 'green').length,
    [permissions]
  )
  const confirmed = useMemo(
    () => last24h.filter((e) => e.result === 'allowed').length,
    [last24h]
  )
  const blocked = useMemo(
    () => last24h.filter((e) => e.result === 'denied').length,
    [last24h]
  )

  const selectedPerms = selectedNodeId ? permissions.get(selectedNodeId) ?? [] : []
  const selectedHistory = useMemo(
    () => last24h.filter((e) => e.nodeId === selectedNodeId),
    [last24h, selectedNodeId]
  )

  const openDrawer = (nodeId: string) => {
    setSelectedNodeId(nodeId)
    setDrawerOpen(true)
  }
  const closeDrawer = () => {
    setDrawerOpen(false)
    setSelectedNodeId(null)
  }

  return (
    <div
      data-testid="security-dashboard"
      style={{
        padding: '24px 32px',
        fontFamily: 'Inter, system-ui, sans-serif',
        color: '#C9D1D9',
        background: '#0D1117',
        minHeight: '100%',
      }}
    >
      <h2 style={{ color: '#fff', marginBottom: 24, fontSize: 22, fontWeight: 700 }}>
        🛡️ Seguridad
      </h2>

      {/* Cards resumen */}
      <div
        data-testid="summary-cards"
        style={{ display: 'flex', gap: 16, marginBottom: 32 }}
      >
        {[
          { label: 'Auto activos', value: autoActive, color: '#2EA043', icon: '🟢' },
          { label: 'Confirmados (24h)', value: confirmed, color: '#FFD600', icon: '✅' },
          { label: 'Bloqueados (24h)', value: blocked, color: '#FF4444', icon: '❌' },
        ].map((card) => (
          <div
            key={card.label}
            data-testid={`card-${card.label.toLowerCase().replace(/\s+/g, '-').replace(/[()\/]/g, '')}`}
            style={{
              flex: 1,
              background: '#161B22',
              border: `1px solid ${card.color}44`,
              borderRadius: 10,
              padding: '16px 20px',
            }}
          >
            <div style={{ fontSize: 28, fontWeight: 800, color: card.color }}>
              {card.icon} {card.value}
            </div>
            <div style={{ fontSize: 13, color: '#8B949E', marginTop: 4 }}>{card.label}</div>
          </div>
        ))}
      </div>

      {/* Lista de nodos con permisos */}
      <div style={{ marginBottom: 32 }}>
        <h3 style={{ fontSize: 15, fontWeight: 600, color: '#8B949E', marginBottom: 14, textTransform: 'uppercase', letterSpacing: 0.8 }}>
          Nodos y Permisos
        </h3>
        <div
          data-testid="nodes-list"
          style={{ display: 'flex', flexDirection: 'column', gap: 8 }}
        >
          {[...permissions.entries()].map(([nodeId, perms]) => (
            <div
              key={nodeId}
              data-testid={`node-row-${nodeId}`}
              onClick={() => openDrawer(nodeId)}
              style={{
                background: '#161B22',
                border: '1px solid #21262D',
                borderRadius: 8,
                padding: '12px 16px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                transition: 'border-color 0.15s',
              }}
            >
              <div style={{ fontWeight: 600, flex: 1 }}>{nodeId}</div>
              <div style={{ display: 'flex', gap: 6 }}>
                {perms.map((p) => (
                  <span
                    key={p.permission}
                    style={{
                      fontSize: 11,
                      padding: '2px 8px',
                      borderRadius: 12,
                      background:
                        p.zone === 'green' ? '#1B4332' :
                        p.zone === 'yellow' ? '#2E2400' : '#1A0A0A',
                      color:
                        p.zone === 'green' ? '#2EA043' :
                        p.zone === 'yellow' ? '#FFD600' : '#FF6B6B',
                      border: `1px solid ${
                        p.zone === 'green' ? '#2EA04344' :
                        p.zone === 'yellow' ? '#FFD60044' : '#FF174444'
                      }`,
                    }}
                  >
                    {p.zone === 'green' ? '🟢' : p.zone === 'yellow' ? '🟡' : '🔴'} {p.permissionLabel}
                  </span>
                ))}
              </div>
              <span style={{ color: '#8B949E', fontSize: 18 }}>›</span>
            </div>
          ))}
          {permissions.size === 0 && (
            <div style={{ color: '#8B949E', fontSize: 14, padding: '16px 0' }}>
              Ningún nodo ha solicitado permisos aún.
            </div>
          )}
        </div>
      </div>

      {/* Historial últimas 24h */}
      <div>
        <h3 style={{ fontSize: 15, fontWeight: 600, color: '#8B949E', marginBottom: 14, textTransform: 'uppercase', letterSpacing: 0.8 }}>
          Historial últimas 24h
        </h3>
        <div
          data-testid="access-history"
          style={{
            background: '#161B22',
            border: '1px solid #21262D',
            borderRadius: 8,
            overflow: 'hidden',
          }}
        >
          {last24h.length === 0 ? (
            <div style={{ padding: '16px 20px', color: '#8B949E', fontSize: 14 }}>
              Sin actividad en las últimas 24 horas.
            </div>
          ) : (
            last24h.slice().reverse().map((entry, i) => (
              <div
                key={i}
                data-testid="history-entry"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                  padding: '10px 16px',
                  borderBottom: i < last24h.length - 1 ? '1px solid #21262D' : 'none',
                  fontSize: 13,
                }}
              >
                <span style={{ color: '#8B949E', fontFamily: 'monospace', minWidth: 80 }}>
                  {new Date(entry.timestamp).toLocaleTimeString()}
                </span>
                <span style={{ fontWeight: 600, minWidth: 100 }}>{entry.nodeId}</span>
                <span style={{ color: '#8B949E', flex: 1 }}>{entry.permissionLabel}</span>
                <span>{entry.result === 'allowed' ? '✅' : '❌'}</span>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Drawer lateral por nodo */}
      {drawerOpen && selectedNodeId && (
        <>
          <div
            data-testid="drawer-backdrop"
            onClick={closeDrawer}
            style={{
              position: 'fixed',
              inset: 0,
              background: 'rgba(0,0,0,0.5)',
              zIndex: 800,
            }}
          />
          <div
            data-testid="node-drawer"
            style={{
              position: 'fixed',
              top: 0,
              right: 0,
              bottom: 0,
              width: 380,
              background: '#161B22',
              borderLeft: '1px solid #30363D',
              zIndex: 801,
              padding: '24px 24px',
              overflowY: 'auto',
              fontFamily: 'Inter, system-ui, sans-serif',
              color: '#C9D1D9',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
              <h3 style={{ margin: 0, fontSize: 18, color: '#fff' }}>{selectedNodeId}</h3>
              <button
                data-testid="close-drawer"
                onClick={closeDrawer}
                style={{ background: 'none', border: 'none', color: '#8B949E', fontSize: 22, cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            {/* Permisos granulares */}
            <div style={{ marginBottom: 24 }}>
              <div style={{ fontSize: 12, color: '#8B949E', textTransform: 'uppercase', marginBottom: 12, letterSpacing: 0.8 }}>
                Permisos
              </div>
              {selectedPerms.map((p) => (
                <div
                  key={p.permission}
                  data-testid={`perm-row-${p.permission}`}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    padding: '10px 0',
                    borderBottom: '1px solid #21262D',
                  }}
                >
                  <span style={{ flex: 1, fontSize: 14 }}>{p.permissionLabel}</span>
                  <span style={{ fontFamily: 'monospace', fontSize: 11, color: '#8B949E' }}>{p.permission}</span>
                  <select
                    data-testid={`zone-select-${p.permission}`}
                    defaultValue={p.zone}
                    style={{
                      background: '#0D1117',
                      border: '1px solid #30363D',
                      color: '#C9D1D9',
                      borderRadius: 4,
                      padding: '4px 8px',
                      fontSize: 12,
                      cursor: 'pointer',
                    }}
                  >
                    <option value="green">🟢 Verde</option>
                    <option value="yellow">🟡 Amarilla</option>
                    <option value="red">🔴 Roja</option>
                  </select>
                </div>
              ))}
            </div>

            {/* Historial del nodo */}
            <div style={{ marginBottom: 24 }}>
              <div style={{ fontSize: 12, color: '#8B949E', textTransform: 'uppercase', marginBottom: 12, letterSpacing: 0.8 }}>
                Historial del nodo
              </div>
              {selectedHistory.length === 0 ? (
                <div style={{ color: '#8B949E', fontSize: 13 }}>Sin historial.</div>
              ) : (
                selectedHistory.slice().reverse().map((entry, i) => (
                  <div key={i} style={{ fontSize: 13, padding: '6px 0', borderBottom: '1px solid #21262D22', display: 'flex', gap: 10 }}>
                    <span style={{ color: '#8B949E', fontFamily: 'monospace' }}>{new Date(entry.timestamp).toLocaleTimeString()}</span>
                    <span style={{ flex: 1 }}>{entry.permissionLabel}</span>
                    <span>{entry.result === 'allowed' ? '✅' : '❌'}</span>
                  </div>
                ))
              )}
            </div>

            {/* Botón revocar todo */}
            <button
              data-testid="revoke-all-btn"
              onClick={() => {
                selectedPerms.forEach((p) => denyPermission(selectedNodeId, p.permission))
                closeDrawer()
              }}
              style={{
                width: '100%',
                background: '#1A0A0A',
                border: '1px solid #FF4444',
                color: '#FF6B6B',
                borderRadius: 6,
                padding: '11px',
                fontWeight: 600,
                cursor: 'pointer',
                fontSize: 14,
              }}
            >
              🚫 Revocar todos los permisos
            </button>
          </div>
        </>
      )}
    </div>
  )
}
