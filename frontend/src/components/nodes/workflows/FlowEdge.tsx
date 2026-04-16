/**
 * YeyoOS — FlowEdge
 * SVG bezier edge between two nodes in the workflow designer canvas.
 */

import React from 'react'

export interface EdgePosition {
  x: number
  y: number
}

export interface FlowEdgeProps {
  edge: {
    id: string
    source_id: string
    target_id: string
    label: string
    edge_type: string
  }
  sourcePos: EdgePosition
  targetPos: EdgePosition
  onDelete?: (edgeId: string) => void
  running?: boolean
}

export function FlowEdge({ edge, sourcePos, targetPos, onDelete, running = false }: FlowEdgeProps) {
  const dx = targetPos.x - sourcePos.x
  const cp = Math.max(Math.abs(dx) * 0.5, 50)

  const path = [
    `M ${sourcePos.x} ${sourcePos.y}`,
    `C ${sourcePos.x + cp} ${sourcePos.y},`,
    `${targetPos.x - cp} ${targetPos.y},`,
    `${targetPos.x} ${targetPos.y}`,
  ].join(' ')

  const midX = (sourcePos.x + targetPos.x) / 2
  const midY = (sourcePos.y + targetPos.y) / 2

  return (
    <g data-testid={`edge-${edge.id}`}>
      <path
        d={path}
        fill="none"
        stroke="#555"
        strokeWidth={2}
        strokeDasharray={running ? '6 4' : 'none'}
        style={running ? { animation: 'dash-flow 0.6s linear infinite' } : undefined}
      />

      {/* Invisible wider hit area for easier clicking */}
      <path d={path} fill="none" stroke="transparent" strokeWidth={14} />

      {edge.label && (
        <text
          x={midX}
          y={midY - 10}
          fill="#777"
          fontSize={10}
          textAnchor="middle"
        >
          {edge.label}
        </text>
      )}

      {onDelete && (
        <g
          style={{ cursor: 'pointer' }}
          onClick={(e) => {
            e.stopPropagation()
            onDelete(edge.id)
          }}
        >
          <circle cx={midX} cy={midY} r={8} fill="#1a1a2e" stroke="#555" strokeWidth={1} />
          <text
            x={midX}
            y={midY + 4}
            fill="#EF9A9A"
            fontSize={11}
            fontWeight="bold"
            textAnchor="middle"
          >
            ×
          </text>
        </g>
      )}
    </g>
  )
}
