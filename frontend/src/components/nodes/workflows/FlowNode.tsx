/**
 * YeyoOS — FlowNode
 * Single draggable node rendered on the workflow designer canvas.
 */

import React, { useCallback, useRef } from 'react'

export interface FlowNodeData {
  id: string
  node_type: string
  label: string
  config: Record<string, unknown>
  position_x: number
  position_y: number
}

export interface FlowNodeProps {
  node: FlowNodeData
  selected: boolean
  color: string
  onSelect: (nodeId: string) => void
  onDragStart: (nodeId: string, e: React.MouseEvent) => void
  onDrag: (nodeId: string, e: React.MouseEvent) => void
  onDragEnd: (nodeId: string) => void
}

const NODE_WIDTH = 160
const NODE_HEIGHT = 72
const DOT_SIZE = 10

export { NODE_WIDTH, NODE_HEIGHT }

export function FlowNode({
  node,
  selected,
  color,
  onSelect,
  onDragStart,
  onDrag,
  onDragEnd,
}: FlowNodeProps) {
  const dragging = useRef(false)

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation()
      dragging.current = true
      onSelect(node.id)
      onDragStart(node.id, e)

      const onMove = (ev: MouseEvent) => {
        if (dragging.current) onDrag(node.id, ev as unknown as React.MouseEvent)
      }
      const onUp = () => {
        dragging.current = false
        onDragEnd(node.id)
        window.removeEventListener('mousemove', onMove)
        window.removeEventListener('mouseup', onUp)
      }

      window.addEventListener('mousemove', onMove)
      window.addEventListener('mouseup', onUp)
    },
    [node.id, onSelect, onDragStart, onDrag, onDragEnd],
  )

  const configKeys = Object.keys(node.config ?? {})
  const configSummary =
    configKeys.length > 0
      ? configKeys.slice(0, 2).join(', ') + (configKeys.length > 2 ? '…' : '')
      : 'No config'

  return (
    <div
      data-testid={`flow-node-${node.id}`}
      onMouseDown={handleMouseDown}
      style={{
        position: 'absolute',
        left: node.position_x,
        top: node.position_y,
        width: NODE_WIDTH,
        minHeight: NODE_HEIGHT,
        backgroundColor: '#0A0E1A',
        border: `2px solid ${selected ? color : '#1E3A5F'}`,
        borderRadius: 8,
        padding: '8px 10px',
        cursor: 'grab',
        userSelect: 'none',
        boxShadow: selected ? `0 0 12px ${color}44` : 'none',
        transition: 'border-color 0.15s, box-shadow 0.15s',
        zIndex: selected ? 10 : 1,
      }}
    >
      {/* Header: icon + label */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
        <span style={{ fontSize: 14 }}>{node.label.split(' ')[0]}</span>
        <span
          style={{
            color: '#E0F7FA',
            fontSize: 12,
            fontWeight: 600,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            flex: 1,
          }}
        >
          {node.label}
        </span>
      </div>

      {/* Node type badge */}
      <div
        style={{
          display: 'inline-block',
          backgroundColor: color + '22',
          color,
          fontSize: 9,
          fontWeight: 600,
          padding: '1px 6px',
          borderRadius: 4,
          letterSpacing: '0.5px',
          textTransform: 'uppercase',
          marginBottom: 4,
        }}
      >
        {node.node_type}
      </div>

      {/* Config summary */}
      <div style={{ color: '#607D8B', fontSize: 10 }}>{configSummary}</div>

      {/* Input dot (left center) */}
      <div
        data-testid={`dot-in-${node.id}`}
        style={{
          position: 'absolute',
          left: -(DOT_SIZE / 2),
          top: '50%',
          transform: 'translateY(-50%)',
          width: DOT_SIZE,
          height: DOT_SIZE,
          borderRadius: '50%',
          backgroundColor: '#1E3A5F',
          border: '2px solid #4FC3F7',
        }}
      />

      {/* Output dot (right center) */}
      <div
        data-testid={`dot-out-${node.id}`}
        style={{
          position: 'absolute',
          right: -(DOT_SIZE / 2),
          top: '50%',
          transform: 'translateY(-50%)',
          width: DOT_SIZE,
          height: DOT_SIZE,
          borderRadius: '50%',
          backgroundColor: '#1E3A5F',
          border: '2px solid #4FC3F7',
        }}
      />
    </div>
  )
}
