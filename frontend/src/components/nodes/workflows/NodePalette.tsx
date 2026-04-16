/**
 * YeyoOS — NodePalette
 * Sidebar listing available node types grouped by category.
 * Nodes are draggable onto the designer canvas.
 */

import React from 'react'
import { useWorkflowStore } from '@/stores/workflowStore'

const CATEGORY_LABELS: Record<string, string> = {
  'ia_media': '🤖 IA & Media',
  'code_files': '💻 Code & Files',
  'memory': '🧠 Memory',
  'logic': '🔀 Logic',
  'external': '🌐 External',
}

const CATEGORY_ORDER = ['ia_media', 'code_files', 'memory', 'logic', 'external']

export function NodePalette() {
  const nodeTypes = useWorkflowStore((s) => s.nodeTypes)
  const nodeCategories = useWorkflowStore((s) => s.nodeCategories)

  const handleDragStart = (e: React.DragEvent, nodeType: string) => {
    e.dataTransfer.setData('application/yeyo-node-type', nodeType)
    e.dataTransfer.effectAllowed = 'copy'
  }

  const sortedCategories = CATEGORY_ORDER.filter((c) => nodeCategories[c]?.length > 0)
  // Include categories returned by the API that aren't in our predefined order
  Object.keys(nodeCategories).forEach((c) => {
    if (!sortedCategories.includes(c) && nodeCategories[c]?.length > 0) {
      sortedCategories.push(c)
    }
  })

  return (
    <div
      data-testid="node-palette"
      style={{
        width: 200,
        flexShrink: 0,
        borderRight: '1px solid #1E3A5F',
        overflowY: 'auto',
        backgroundColor: '#080D1C',
      }}
    >
      <div
        style={{
          padding: '12px 14px',
          borderBottom: '1px solid #1E3A5F',
          color: '#4FC3F7',
          fontSize: 12,
          fontWeight: 600,
          letterSpacing: '0.5px',
        }}
      >
        🧩 Node Types
      </div>

      {sortedCategories.length === 0 && (
        <div style={{ padding: 14, color: '#607D8B', fontSize: 12 }}>
          Loading node types…
        </div>
      )}

      {sortedCategories.map((catKey) => (
        <div key={catKey} style={{ marginBottom: 4 }}>
          <div
            style={{
              padding: '8px 14px 4px',
              color: '#607D8B',
              fontSize: 10,
              fontWeight: 600,
              letterSpacing: '1px',
              textTransform: 'uppercase',
            }}
          >
            {CATEGORY_LABELS[catKey] ?? catKey}
          </div>

          {nodeCategories[catKey].map((nt) => {
            const info = nodeTypes[nt]
            if (!info) return null
            const icon = info.label.split(' ')[0]

            return (
              <div
                key={nt}
                draggable
                onDragStart={(e) => handleDragStart(e, nt)}
                data-testid={`palette-node-${nt}`}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '6px 14px',
                  cursor: 'grab',
                  fontSize: 12,
                  color: '#B0BEC5',
                  transition: 'background-color 0.15s',
                }}
                onMouseEnter={(e) => {
                  ;(e.currentTarget as HTMLDivElement).style.backgroundColor = '#1E3A5F33'
                }}
                onMouseLeave={(e) => {
                  ;(e.currentTarget as HTMLDivElement).style.backgroundColor = 'transparent'
                }}
              >
                <span style={{ fontSize: 14 }}>{icon}</span>
                <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {info.label}
                </span>
                <span
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    backgroundColor: info.color,
                    flexShrink: 0,
                  }}
                />
              </div>
            )
          })}
        </div>
      ))}
    </div>
  )
}
