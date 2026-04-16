/**
 * YeyoOS — FlowDesigner
 * Visual workflow designer with drag-and-drop canvas, node palette, and config panel.
 */

import React, { useState, useCallback, useRef } from 'react'
import { useWorkflowStore } from '@/stores/workflowStore'
import { NodePalette } from './NodePalette'
import { FlowNode, NODE_WIDTH, NODE_HEIGHT } from './FlowNode'
import { FlowEdge } from './FlowEdge'

interface DragState {
  nodeId: string
  offsetX: number
  offsetY: number
}

export function FlowDesigner() {
  const {
    designerNodes,
    designerEdges,
    selectedNodeId,
    nodeTypes,
    currentWorkflow,
    isLoading,
    addDesignerNode,
    updateDesignerNode,
    removeDesignerEdge,
    addDesignerEdge,
    selectNode,
    clearDesigner,
    createWorkflow,
    updateWorkflow,
    executeWorkflow,
    setActiveTab,
  } = useWorkflowStore()

  const [connectingFrom, setConnectingFrom] = useState<string | null>(null)
  const [dragState, setDragState] = useState<DragState | null>(null)
  const canvasRef = useRef<HTMLDivElement>(null)

  // --- Config panel state for selected node ---
  const selectedNode = designerNodes.find((n) => n.id === selectedNodeId) ?? null
  const selectedInfo = selectedNode ? nodeTypes[selectedNode.node_type] : null

  // --- Node color lookup ---
  const getColor = useCallback(
    (nodeType: string) => nodeTypes[nodeType]?.color ?? '#4FC3F7',
    [nodeTypes],
  )

  // --- Canvas drop handler (new node from palette) ---
  const handleCanvasDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      const nodeType = e.dataTransfer.getData('application/yeyo-node-type')
      if (!nodeType || !canvasRef.current) return

      const rect = canvasRef.current.getBoundingClientRect()
      const x = e.clientX - rect.left
      const y = e.clientY - rect.top
      const info = nodeTypes[nodeType]

      addDesignerNode({
        id: `node_${Date.now()}`,
        node_type: nodeType,
        label: info?.label ?? nodeType,
        config: {},
        position_x: x,
        position_y: y,
        next_node_ids: [],
        true_branch: null,
        false_branch: null,
        loop_body: [],
        loop_count: 0,
      })
    },
    [addDesignerNode, nodeTypes],
  )

  // --- Node drag handlers ---
  const handleNodeDragStart = useCallback(
    (nodeId: string, e: React.MouseEvent) => {
      const node = designerNodes.find((n) => n.id === nodeId)
      if (!node) return
      setDragState({ nodeId, offsetX: e.clientX - node.position_x, offsetY: e.clientY - node.position_y })
    },
    [designerNodes],
  )

  const handleNodeDrag = useCallback(
    (nodeId: string, e: React.MouseEvent) => {
      if (!dragState || dragState.nodeId !== nodeId) return
      updateDesignerNode(nodeId, {
        position_x: e.clientX - dragState.offsetX,
        position_y: e.clientY - dragState.offsetY,
      })
    },
    [dragState, updateDesignerNode],
  )

  const handleNodeDragEnd = useCallback(() => {
    setDragState(null)
  }, [])

  // --- Connection between nodes (click output dot → click input dot) ---
  const handleCanvasClick = useCallback(
    (e: React.MouseEvent) => {
      // If clicking on the canvas background, deselect
      if ((e.target as HTMLElement) === canvasRef.current) {
        selectNode(null)
        setConnectingFrom(null)
      }
    },
    [selectNode],
  )

  const handleNodeSelect = useCallback(
    (nodeId: string) => {
      if (connectingFrom && connectingFrom !== nodeId) {
        // Complete connection
        addDesignerEdge({
          id: `edge_${Date.now()}`,
          source_id: connectingFrom,
          target_id: nodeId,
          label: '',
          edge_type: 'default',
        })
        setConnectingFrom(null)
      } else {
        selectNode(nodeId)
      }
    },
    [connectingFrom, addDesignerEdge, selectNode],
  )

  const handleStartConnect = useCallback((nodeId: string) => {
    setConnectingFrom(nodeId)
  }, [])

  // --- Edge positions ---
  const getNodeCenter = (nodeId: string, side: 'left' | 'right') => {
    const node = designerNodes.find((n) => n.id === nodeId)
    if (!node) return { x: 0, y: 0 }
    return {
      x: side === 'right' ? node.position_x + NODE_WIDTH : node.position_x,
      y: node.position_y + NODE_HEIGHT / 2,
    }
  }

  // --- Save workflow ---
  const handleSave = useCallback(async () => {
    const data = {
      name: currentWorkflow?.name ?? 'Untitled Workflow',
      description: currentWorkflow?.description ?? '',
      nodes: designerNodes,
      edges: designerEdges,
      trigger_type: currentWorkflow?.trigger_type ?? 'manual',
      trigger_config: currentWorkflow?.trigger_config ?? {},
      variables: currentWorkflow?.variables ?? {},
      status: 'active',
    }

    if (currentWorkflow?.id) {
      await updateWorkflow(currentWorkflow.id, data)
    } else {
      await createWorkflow(data)
    }
  }, [currentWorkflow, designerNodes, designerEdges, createWorkflow, updateWorkflow])

  // --- Run workflow ---
  const handleRun = useCallback(async () => {
    if (!currentWorkflow?.id) return
    const exec = await executeWorkflow(currentWorkflow.id)
    if (exec) setActiveTab('executions')
  }, [currentWorkflow, executeWorkflow, setActiveTab])

  // --- Config panel update ---
  const handleConfigChange = useCallback(
    (key: string, value: string) => {
      if (!selectedNodeId) return
      const node = designerNodes.find((n) => n.id === selectedNodeId)
      if (!node) return
      updateDesignerNode(selectedNodeId, { config: { ...node.config, [key]: value } })
    },
    [selectedNodeId, designerNodes, updateDesignerNode],
  )

  return (
    <div data-testid="flow-designer" style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
      {/* Left sidebar: Node palette */}
      <NodePalette />

      {/* Center: Canvas */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', position: 'relative' }}>
        <div
          ref={canvasRef}
          data-testid="designer-canvas"
          onClick={handleCanvasClick}
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleCanvasDrop}
          style={{
            flex: 1,
            position: 'relative',
            overflow: 'hidden',
            backgroundColor: '#060B18',
            backgroundImage:
              'radial-gradient(circle, #1E3A5F 1px, transparent 1px)',
            backgroundSize: '20px 20px',
          }}
        >
          {/* SVG layer for edges */}
          <svg
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              pointerEvents: 'none',
              zIndex: 0,
            }}
          >
            <defs>
              <style>{`
                @keyframes dash-flow {
                  to { stroke-dashoffset: -20; }
                }
              `}</style>
            </defs>
            <g style={{ pointerEvents: 'auto' }}>
              {designerEdges.map((edge) => (
                <FlowEdge
                  key={edge.id}
                  edge={edge}
                  sourcePos={getNodeCenter(edge.source_id, 'right')}
                  targetPos={getNodeCenter(edge.target_id, 'left')}
                  onDelete={removeDesignerEdge}
                />
              ))}
            </g>
          </svg>

          {/* Nodes */}
          {designerNodes.map((node) => (
            <FlowNode
              key={node.id}
              node={node}
              selected={node.id === selectedNodeId}
              color={getColor(node.node_type)}
              onSelect={handleNodeSelect}
              onDragStart={handleNodeDragStart}
              onDrag={handleNodeDrag}
              onDragEnd={handleNodeDragEnd}
            />
          ))}

          {/* Empty state */}
          {designerNodes.length === 0 && (
            <div
              style={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                color: '#607D8B',
                fontSize: 14,
                textAlign: 'center',
              }}
            >
              Drag nodes from the palette to start designing
            </div>
          )}

          {/* Connecting state indicator */}
          {connectingFrom && (
            <div
              style={{
                position: 'absolute',
                top: 8,
                left: '50%',
                transform: 'translateX(-50%)',
                backgroundColor: '#4FC3F733',
                color: '#4FC3F7',
                padding: '4px 12px',
                borderRadius: 6,
                fontSize: 11,
                zIndex: 20,
              }}
            >
              Click a target node to connect — or click canvas to cancel
            </div>
          )}
        </div>

        {/* Bottom bar */}
        <div
          data-testid="designer-toolbar"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '8px 14px',
            borderTop: '1px solid #1E3A5F',
            backgroundColor: '#080D1C',
          }}
        >
          <button
            onClick={handleSave}
            disabled={isLoading}
            style={{
              backgroundColor: '#1E3A5F',
              color: '#E0F7FA',
              border: 'none',
              borderRadius: 6,
              padding: '6px 14px',
              fontSize: 12,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            💾 Save
          </button>
          <button
            onClick={handleRun}
            disabled={isLoading || !currentWorkflow?.id}
            style={{
              backgroundColor: '#1B5E20',
              color: '#A5D6A7',
              border: 'none',
              borderRadius: 6,
              padding: '6px 14px',
              fontSize: 12,
              fontWeight: 600,
              cursor: 'pointer',
              opacity: currentWorkflow?.id ? 1 : 0.5,
            }}
          >
            ▶️ Run
          </button>
          <button
            onClick={clearDesigner}
            style={{
              backgroundColor: '#37474F',
              color: '#B0BEC5',
              border: 'none',
              borderRadius: 6,
              padding: '6px 14px',
              fontSize: 12,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            🔄 Clear
          </button>

          {/* Right-click connect shortcut */}
          {selectedNodeId && !connectingFrom && (
            <button
              onClick={() => handleStartConnect(selectedNodeId)}
              style={{
                marginLeft: 'auto',
                backgroundColor: '#0D47A1',
                color: '#90CAF9',
                border: 'none',
                borderRadius: 6,
                padding: '6px 14px',
                fontSize: 12,
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              🔗 Connect from selected
            </button>
          )}
        </div>
      </div>

      {/* Right sidebar: config panel (visible when a node is selected) */}
      {selectedNode && (
        <aside
          data-testid="config-panel"
          style={{
            width: 250,
            flexShrink: 0,
            borderLeft: '1px solid #1E3A5F',
            backgroundColor: '#080D1C',
            display: 'flex',
            flexDirection: 'column',
            overflowY: 'auto',
          }}
        >
          <div
            style={{
              padding: '12px 14px',
              borderBottom: '1px solid #1E3A5F',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <span style={{ color: '#4FC3F7', fontSize: 12, fontWeight: 600 }}>
              ⚙️ Node Config
            </span>
            <button
              onClick={() => selectNode(null)}
              style={{
                background: 'none',
                border: 'none',
                color: '#607D8B',
                cursor: 'pointer',
                fontSize: 14,
              }}
            >
              ✕
            </button>
          </div>

          <div style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
            {/* Node info */}
            <div>
              <div style={{ color: '#E0F7FA', fontSize: 13, fontWeight: 600, marginBottom: 2 }}>
                {selectedNode.label}
              </div>
              <div
                style={{
                  display: 'inline-block',
                  backgroundColor: (selectedInfo?.color ?? '#4FC3F7') + '22',
                  color: selectedInfo?.color ?? '#4FC3F7',
                  fontSize: 9,
                  fontWeight: 600,
                  padding: '1px 6px',
                  borderRadius: 4,
                  textTransform: 'uppercase',
                }}
              >
                {selectedNode.node_type}
              </div>
              {selectedInfo?.description && (
                <div style={{ color: '#607D8B', fontSize: 11, marginTop: 4 }}>
                  {selectedInfo.description}
                </div>
              )}
            </div>

            {/* Label edit */}
            <div>
              <label style={{ color: '#607D8B', fontSize: 10, fontWeight: 600, display: 'block', marginBottom: 3 }}>
                LABEL
              </label>
              <input
                value={selectedNode.label}
                onChange={(e) =>
                  updateDesignerNode(selectedNodeId!, { label: e.target.value })
                }
                style={{
                  width: '100%',
                  backgroundColor: '#0A0E1A',
                  border: '1px solid #1E3A5F',
                  borderRadius: 4,
                  color: '#E0F7FA',
                  padding: '6px 8px',
                  fontSize: 12,
                  boxSizing: 'border-box',
                }}
              />
            </div>

            {/* Config key-value editor */}
            <div>
              <label style={{ color: '#607D8B', fontSize: 10, fontWeight: 600, display: 'block', marginBottom: 3 }}>
                CONFIG
              </label>
              {Object.entries(selectedNode.config ?? {}).map(([key, val]) => (
                <div key={key} style={{ display: 'flex', gap: 4, marginBottom: 4 }}>
                  <span style={{ color: '#90CAF9', fontSize: 11, minWidth: 60, paddingTop: 5 }}>{key}</span>
                  <input
                    value={String(val ?? '')}
                    onChange={(e) => handleConfigChange(key, e.target.value)}
                    style={{
                      flex: 1,
                      backgroundColor: '#0A0E1A',
                      border: '1px solid #1E3A5F',
                      borderRadius: 4,
                      color: '#E0F7FA',
                      padding: '4px 6px',
                      fontSize: 11,
                      boxSizing: 'border-box',
                    }}
                  />
                </div>
              ))}
              {/* Add new config key */}
              <button
                onClick={() => {
                  const key = prompt('Config key:')
                  if (key) handleConfigChange(key, '')
                }}
                style={{
                  backgroundColor: '#1E3A5F33',
                  color: '#4FC3F7',
                  border: '1px dashed #1E3A5F',
                  borderRadius: 4,
                  padding: '4px 8px',
                  fontSize: 10,
                  cursor: 'pointer',
                  width: '100%',
                  marginTop: 4,
                }}
              >
                + Add config
              </button>
            </div>

            {/* Delete node */}
            <button
              onClick={() => {
                useWorkflowStore.getState().removeDesignerNode(selectedNode.id)
              }}
              style={{
                backgroundColor: '#B71C1C22',
                color: '#EF9A9A',
                border: '1px solid #B71C1C44',
                borderRadius: 6,
                padding: '6px 10px',
                fontSize: 11,
                fontWeight: 600,
                cursor: 'pointer',
                marginTop: 8,
              }}
            >
              🗑️ Delete Node
            </button>
          </div>
        </aside>
      )}
    </div>
  )
}
