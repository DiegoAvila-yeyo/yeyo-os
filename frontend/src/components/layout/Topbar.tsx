/**
 * YeyoOS — Topbar
 * Micro-fase 3.20 — Capa 3: Cuerpo
 *
 * Barra superior siempre visible (48px).
 * Contiene: toggle Hub Sidebar, tabs de nodos abiertos,
 * indicador de pipelines activos, y Kill Switch.
 *
 * REGLA: Kill Switch es SAGRADO — siempre visible, siempre funcional.
 */

import React, { useCallback } from 'react'
import { useHubStore } from '../../stores/hubStore'
import { useSystemStore } from '../../stores/systemStore'
import { MicIndicator } from '../voice/MicIndicator'

export interface TabInfo {
  id: string
  label: string
  icono?: string
  activo: boolean
}

export interface TopbarProps {
  tabs: TabInfo[]
  onTabClick: (tabId: string) => void
  onTabClose: (tabId: string) => void
  onToggleSidebar: () => void
  sidebarOpen: boolean
}

const MAX_TABS = 5

const TOPBAR_STYLES: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  height: 48,
  backgroundColor: '#0A0E1A',
  borderBottom: '1px solid #1E3A5F',
  padding: '0 12px',
  gap: 8,
  userSelect: 'none',
  flexShrink: 0,
  zIndex: 100,
}

export function Topbar({ tabs, onTabClick, onTabClose, onToggleSidebar, sidebarOpen }: TopbarProps) {
  const pipelineActivo = useHubStore((s) => s.pipelineActivo)

  const handleKillSwitch = useCallback(() => {
    // Disparar evento de teclado para activar KillSwitchOverlay (que escucha Ctrl+Alt+K)
    window.dispatchEvent(new KeyboardEvent('keydown', { ctrlKey: true, altKey: true, key: 'k', bubbles: true }))
  }, [])

  const visibleTabs = tabs.slice(0, MAX_TABS)

  return (
    <header data-testid="topbar" style={TOPBAR_STYLES} role="banner">
      {/* Toggle Hub Sidebar */}
      <button
        data-testid="toggle-sidebar-btn"
        onClick={onToggleSidebar}
        aria-label={sidebarOpen ? 'Cerrar Hub' : 'Abrir Hub'}
        aria-expanded={sidebarOpen}
        style={{
          background: sidebarOpen ? 'rgba(79,195,247,0.15)' : 'transparent',
          border: '1px solid #1E3A5F',
          color: '#90CAF9',
          borderRadius: 6,
          padding: '4px 10px',
          cursor: 'pointer',
          fontSize: 14,
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          whiteSpace: 'nowrap',
        }}
      >
        ≡ Hub
      </button>

      {/* Tabs de nodos abiertos */}
      <div
        data-testid="tabs-container"
        style={{
          display: 'flex',
          gap: 4,
          flex: 1,
          overflow: 'hidden',
          alignItems: 'center',
        }}
      >
        {visibleTabs.map((tab) => (
          <div
            key={tab.id}
            data-testid={`tab-${tab.id}`}
            data-active={tab.activo}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '4px 10px',
              backgroundColor: tab.activo ? '#1E3A5F' : 'transparent',
              border: `1px solid ${tab.activo ? '#4FC3F7' : '#1E3A5F'}`,
              borderRadius: 6,
              cursor: 'pointer',
              color: tab.activo ? '#E0F7FA' : '#90CAF9',
              fontSize: 13,
              maxWidth: 140,
              overflow: 'hidden',
            }}
          >
            <span onClick={() => onTabClick(tab.id)} style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
              {tab.icono && <span style={{ marginRight: 4 }}>{tab.icono}</span>}
              {tab.label}
            </span>
            <button
              data-testid={`close-tab-${tab.id}`}
              onClick={(e) => { e.stopPropagation(); onTabClose(tab.id) }}
              aria-label={`Cerrar ${tab.label}`}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#607D8B',
                cursor: 'pointer',
                padding: 0,
                fontSize: 12,
                lineHeight: 1,
                flexShrink: 0,
              }}
            >
              ✕
            </button>
          </div>
        ))}
        {tabs.length > MAX_TABS && (
          <span style={{ color: '#607D8B', fontSize: 12 }}>+{tabs.length - MAX_TABS}</span>
        )}
      </div>

      {/* Indicador de pipelines activos */}
      <div
        data-testid="pipeline-indicator"
        data-pipeline-activo={pipelineActivo}
        title={pipelineActivo ? 'Pipeline ejecutándose' : 'Sin pipelines activos'}
        style={{
          fontSize: 18,
          animation: pipelineActivo ? 'pulse 1s ease-in-out infinite' : 'none',
          opacity: pipelineActivo ? 1 : 0.3,
          cursor: 'default',
        }}
      >
        ⚡
      </div>

      {/* MicIndicator — Micro-fase 5.27 */}
      <MicIndicator />

      {/* Kill Switch */}
      <button
        data-testid="kill-switch-btn"
        onClick={handleKillSwitch}
        aria-label="Kill Switch — detener toda actividad IA"
        style={{
          backgroundColor: '#B71C1C',
          border: '1px solid #E53935',
          color: '#FFCDD2',
          borderRadius: 6,
          padding: '4px 12px',
          cursor: 'pointer',
          fontSize: 12,
          fontWeight: 700,
          letterSpacing: '0.5px',
          flexShrink: 0,
        }}
      >
        ■ STOP
      </button>
    </header>
  )
}
