/**
 * YeyoOS — ExecutionView
 * Execution history and live execution monitoring with WebSocket support.
 */

import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useWorkflowStore } from '@/stores/workflowStore'

const STATUS_STYLES: Record<string, { bg: string; color: string; label: string }> = {
  running: { bg: '#0D47A122', color: '#42A5F5', label: '⏳ Running' },
  completed: { bg: '#1B5E2022', color: '#A5D6A7', label: '✅ Completed' },
  failed: { bg: '#B71C1C22', color: '#EF9A9A', label: '❌ Failed' },
  cancelled: { bg: '#37474F22', color: '#607D8B', label: '🚫 Cancelled' },
  pending: { bg: '#F57F1722', color: '#FFB74D', label: '⏸️ Pending' },
}

const NODE_STATUS_ICONS: Record<string, string> = {
  running: '⏳',
  completed: '✅',
  failed: '❌',
  skipped: '⏭️',
  pending: '⏸️',
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${Math.floor(ms / 60000)}m ${Math.round((ms % 60000) / 1000)}s`
}

function formatTimestamp(ts: string): string {
  try {
    const d = new Date(ts)
    return d.toLocaleString()
  } catch {
    return ts
  }
}

export function ExecutionView() {
  const {
    executions,
    currentExecution,
    currentWorkflow,
    isLoading,
    fetchExecutions,
    fetchExecution,
  } = useWorkflowStore()

  const [expandedId, setExpandedId] = useState<string | null>(null)
  const liveRef = useRef<HTMLDivElement>(null)
  const wsRef = useRef<WebSocket | null>(null)

  // Fetch executions for current workflow on mount
  useEffect(() => {
    if (currentWorkflow?.id) {
      fetchExecutions(currentWorkflow.id)
    }
  }, [currentWorkflow?.id, fetchExecutions])

  // WebSocket for live execution updates
  useEffect(() => {
    if (!currentExecution || currentExecution.status !== 'running') return

    const wsUrl = `ws://localhost:8000/api/v1/workflows/ws/${currentExecution.id}`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        const store = useWorkflowStore.getState()
        if (data.type === 'node_result' && store.currentExecution) {
          // Update current execution with new node result
          const updated = {
            ...store.currentExecution,
            node_results: [...store.currentExecution.node_results, data.result],
            current_node_index: data.current_node_index ?? store.currentExecution.current_node_index,
            progress: data.progress ?? store.currentExecution.progress,
          }
          useWorkflowStore.setState({ currentExecution: updated })
        } else if (data.type === 'execution_complete') {
          const updated = {
            ...store.currentExecution!,
            status: data.status ?? 'completed',
            completed_at: data.completed_at,
            error: data.error,
            progress: 100,
          }
          useWorkflowStore.setState({ currentExecution: updated })
        }
      } catch {
        // ignore parse errors
      }
    }

    ws.onerror = () => ws.close()

    return () => {
      ws.close()
      wsRef.current = null
    }
  }, [currentExecution?.id, currentExecution?.status])

  // Auto-scroll live view
  useEffect(() => {
    if (liveRef.current) {
      liveRef.current.scrollTop = liveRef.current.scrollHeight
    }
  }, [currentExecution?.node_results?.length])

  const handleExpand = useCallback(
    (execId: string) => {
      if (expandedId === execId) {
        setExpandedId(null)
      } else {
        setExpandedId(execId)
        fetchExecution(execId)
      }
    },
    [expandedId, fetchExecution],
  )

  const isLive = currentExecution?.status === 'running'

  return (
    <div data-testid="execution-view" style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Live execution panel */}
      {isLive && currentExecution && (
        <div
          data-testid="live-execution"
          style={{
            borderBottom: '1px solid #1E3A5F',
            backgroundColor: '#080D1C',
            flexShrink: 0,
          }}
        >
          <div style={{ padding: '10px 14px', display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ color: '#42A5F5', fontSize: 12, fontWeight: 600 }}>
              ⚡ Live: {currentExecution.workflow_name}
            </span>
            <div style={{ flex: 1 }} />
            <span style={{ color: '#607D8B', fontSize: 10 }}>
              {currentExecution.current_node_index}/{currentExecution.total_nodes} nodes
            </span>
          </div>

          {/* Progress bar */}
          <div style={{ height: 3, backgroundColor: '#1E3A5F', margin: '0 14px 8px' }}>
            <div
              style={{
                height: '100%',
                width: `${currentExecution.progress}%`,
                backgroundColor: '#42A5F5',
                transition: 'width 0.3s ease',
                borderRadius: 2,
              }}
            />
          </div>

          {/* Node results (live) */}
          <div
            ref={liveRef}
            style={{
              maxHeight: 200,
              overflowY: 'auto',
              padding: '0 14px 10px',
              display: 'flex',
              flexDirection: 'column',
              gap: 4,
            }}
          >
            {currentExecution.node_results.map((nr, i) => (
              <div
                key={`${nr.node_id}-${i}`}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '4px 8px',
                  backgroundColor: '#0A0E1A',
                  borderRadius: 4,
                  fontSize: 11,
                }}
              >
                <span>{NODE_STATUS_ICONS[nr.status] ?? '❓'}</span>
                <span style={{ color: '#B0BEC5', minWidth: 60 }}>{nr.node_type}</span>
                <span
                  style={{
                    fontSize: 9,
                    fontWeight: 600,
                    padding: '0 4px',
                    borderRadius: 3,
                    backgroundColor: (STATUS_STYLES[nr.status]?.bg ?? '#37474F22'),
                    color: (STATUS_STYLES[nr.status]?.color ?? '#607D8B'),
                    textTransform: 'uppercase',
                  }}
                >
                  {nr.status}
                </span>
                <span style={{ color: '#455A64', fontSize: 10 }}>{formatDuration(nr.duration_ms)}</span>
                <span
                  style={{
                    flex: 1,
                    color: '#607D8B',
                    fontSize: 10,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {nr.error ? `⚠️ ${nr.error}` : nr.output ? String(nr.output).slice(0, 80) : ''}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Execution history list */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
        <div style={{ color: '#E0F7FA', fontSize: 14, fontWeight: 600, marginBottom: 12 }}>
          Execution History
        </div>

        {isLoading && executions.length === 0 && (
          <div style={{ textAlign: 'center', padding: 40, color: '#607D8B', fontSize: 13 }}>
            Loading executions…
          </div>
        )}

        {!isLoading && executions.length === 0 && (
          <div style={{ textAlign: 'center', padding: 40, color: '#607D8B', fontSize: 13 }}>
            <div style={{ fontSize: 32, marginBottom: 8 }}>📊</div>
            No executions yet. Run a workflow to see results here.
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {executions.map((exec) => {
            const st = STATUS_STYLES[exec.status] ?? STATUS_STYLES.pending
            const isExpanded = expandedId === exec.id
            const duration = exec.completed_at
              ? new Date(exec.completed_at).getTime() - new Date(exec.started_at).getTime()
              : 0

            return (
              <div key={exec.id} data-testid={`execution-item-${exec.id}`}>
                {/* Summary row */}
                <div
                  onClick={() => handleExpand(exec.id)}
                  style={{
                    backgroundColor: '#0A0E1A',
                    border: `1px solid ${isExpanded ? '#1E3A5F' : '#1E3A5F88'}`,
                    borderRadius: isExpanded ? '8px 8px 0 0' : 8,
                    padding: '10px 14px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    cursor: 'pointer',
                    transition: 'border-color 0.15s',
                  }}
                >
                  <span
                    style={{
                      fontSize: 9,
                      fontWeight: 600,
                      padding: '2px 8px',
                      borderRadius: 4,
                      backgroundColor: st.bg,
                      color: st.color,
                      textTransform: 'uppercase',
                      flexShrink: 0,
                    }}
                  >
                    {st.label}
                  </span>
                  <span style={{ color: '#B0BEC5', fontSize: 12, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {exec.workflow_name}
                  </span>
                  {duration > 0 && (
                    <span style={{ color: '#455A64', fontSize: 10 }}>{formatDuration(duration)}</span>
                  )}
                  <span style={{ color: '#37474F', fontSize: 10 }}>{formatTimestamp(exec.started_at)}</span>
                  <span style={{ color: '#607D8B', fontSize: 12 }}>{isExpanded ? '▾' : '▸'}</span>
                </div>

                {/* Expanded detail */}
                {isExpanded && (
                  <div
                    style={{
                      backgroundColor: '#080D1C',
                      border: '1px solid #1E3A5F',
                      borderTop: 'none',
                      borderRadius: '0 0 8px 8px',
                      padding: 12,
                    }}
                  >
                    {exec.error && (
                      <div style={{ color: '#EF9A9A', fontSize: 11, marginBottom: 8, padding: '4px 8px', backgroundColor: '#B71C1C22', borderRadius: 4 }}>
                        ⚠️ {exec.error}
                      </div>
                    )}

                    <div style={{ color: '#607D8B', fontSize: 10, fontWeight: 600, marginBottom: 6, letterSpacing: '0.5px' }}>
                      NODE RESULTS ({exec.node_results.length})
                    </div>

                    {exec.node_results.map((nr, i) => (
                      <div
                        key={`${nr.node_id}-${i}`}
                        style={{
                          display: 'flex',
                          alignItems: 'flex-start',
                          gap: 8,
                          padding: '6px 8px',
                          marginBottom: 4,
                          backgroundColor: '#0A0E1A',
                          borderRadius: 4,
                          fontSize: 11,
                        }}
                      >
                        <span style={{ flexShrink: 0 }}>{NODE_STATUS_ICONS[nr.status] ?? '❓'}</span>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
                            <span style={{ color: '#B0BEC5', fontWeight: 600 }}>{nr.node_type}</span>
                            <span
                              style={{
                                fontSize: 9,
                                padding: '0 4px',
                                borderRadius: 3,
                                backgroundColor: (STATUS_STYLES[nr.status]?.bg ?? '#37474F22'),
                                color: (STATUS_STYLES[nr.status]?.color ?? '#607D8B'),
                                textTransform: 'uppercase',
                              }}
                            >
                              {nr.status}
                            </span>
                            <span style={{ color: '#455A64', fontSize: 10 }}>{formatDuration(nr.duration_ms)}</span>
                          </div>
                          {nr.error && (
                            <div style={{ color: '#EF9A9A', fontSize: 10, marginTop: 2 }}>⚠️ {nr.error}</div>
                          )}
                          {nr.output && (
                            <div
                              style={{
                                color: '#607D8B',
                                fontSize: 10,
                                marginTop: 2,
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                whiteSpace: 'nowrap',
                                maxWidth: '100%',
                              }}
                            >
                              {typeof nr.output === 'string' ? nr.output.slice(0, 120) : JSON.stringify(nr.output).slice(0, 120)}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}

                    {exec.node_results.length === 0 && (
                      <div style={{ color: '#455A64', fontSize: 11 }}>No node results available.</div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
