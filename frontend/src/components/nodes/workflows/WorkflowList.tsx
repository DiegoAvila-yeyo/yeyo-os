/**
 * YeyoOS — WorkflowList
 * Lists all workflows with action buttons for run, edit, and delete.
 */

import React, { useCallback } from 'react'
import { useWorkflowStore } from '@/stores/workflowStore'

const STATUS_COLORS: Record<string, string> = {
  active: '#A5D6A7',
  inactive: '#607D8B',
  error: '#EF9A9A',
  draft: '#FFD54F',
}

const TRIGGER_LABELS: Record<string, string> = {
  manual: '🖱️ Manual',
  schedule: '⏰ Schedule',
  webhook: '🔗 Webhook',
  event: '⚡ Event',
}

export function WorkflowList() {
  const {
    workflows,
    isLoading,
    loadWorkflowToDesigner,
    setActiveTab,
    deleteWorkflow,
    executeWorkflow,
    createWorkflow,
  } = useWorkflowStore()

  const handleEdit = useCallback(
    (workflow: typeof workflows[number]) => {
      loadWorkflowToDesigner(workflow)
      setActiveTab('designer')
    },
    [loadWorkflowToDesigner, setActiveTab],
  )

  const handleDelete = useCallback(
    async (id: string, name: string) => {
      if (!window.confirm(`Delete workflow "${name}"? This cannot be undone.`)) return
      await deleteWorkflow(id)
    },
    [deleteWorkflow],
  )

  const handleRun = useCallback(
    async (id: string) => {
      await executeWorkflow(id)
      setActiveTab('executions')
    },
    [executeWorkflow, setActiveTab],
  )

  const handleNewWorkflow = useCallback(async () => {
    const created = await createWorkflow({
      name: 'New Workflow',
      description: '',
      nodes: [],
      edges: [],
      trigger_type: 'manual',
      trigger_config: {},
      variables: {},
      status: 'draft',
    })
    if (created) {
      loadWorkflowToDesigner(created)
      setActiveTab('designer')
    }
  }, [createWorkflow, loadWorkflowToDesigner, setActiveTab])

  return (
    <div data-testid="workflow-list" style={{ padding: 16, overflowY: 'auto', height: '100%' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <div style={{ color: '#E0F7FA', fontSize: 14, fontWeight: 600 }}>
          Workflows ({workflows.length})
        </div>
        <button
          onClick={handleNewWorkflow}
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
          ➕ New Workflow
        </button>
      </div>

      {/* Loading */}
      {isLoading && workflows.length === 0 && (
        <div style={{ textAlign: 'center', padding: 40, color: '#607D8B', fontSize: 13 }}>
          <div style={{ fontSize: 24, marginBottom: 8, animation: 'spin 1s linear infinite' }}>⏳</div>
          Loading workflows…
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && workflows.length === 0 && (
        <div style={{ textAlign: 'center', padding: 40, color: '#607D8B', fontSize: 13 }}>
          <div style={{ fontSize: 32, marginBottom: 8 }}>📋</div>
          No workflows yet. Click &quot;➕ New Workflow&quot; to create one.
        </div>
      )}

      {/* Workflow items */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {workflows.map((wf) => (
          <div
            key={wf.id}
            data-testid={`workflow-item-${wf.id}`}
            style={{
              backgroundColor: '#0A0E1A',
              border: '1px solid #1E3A5F',
              borderRadius: 8,
              padding: '12px 14px',
              display: 'flex',
              alignItems: 'center',
              gap: 12,
            }}
          >
            {/* Info */}
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                <span
                  style={{
                    color: '#E0F7FA',
                    fontSize: 13,
                    fontWeight: 600,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {wf.name}
                </span>
                <span
                  style={{
                    display: 'inline-block',
                    fontSize: 9,
                    fontWeight: 600,
                    padding: '1px 6px',
                    borderRadius: 4,
                    backgroundColor: (STATUS_COLORS[wf.status] ?? '#607D8B') + '22',
                    color: STATUS_COLORS[wf.status] ?? '#607D8B',
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px',
                    flexShrink: 0,
                  }}
                >
                  {wf.status}
                </span>
              </div>
              {wf.description && (
                <div
                  style={{
                    color: '#607D8B',
                    fontSize: 11,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                    marginBottom: 4,
                  }}
                >
                  {wf.description}
                </div>
              )}
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: '#455A64', fontSize: 10 }}>
                <span>{TRIGGER_LABELS[wf.trigger_type] ?? wf.trigger_type}</span>
                <span>{wf.nodes.length} nodes</span>
                <span>Updated {new Date(wf.updated_at).toLocaleDateString()}</span>
              </div>
            </div>

            {/* Actions */}
            <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
              <button
                title="Run"
                onClick={() => handleRun(wf.id)}
                disabled={isLoading}
                style={{
                  backgroundColor: '#1B5E2033',
                  color: '#A5D6A7',
                  border: 'none',
                  borderRadius: 4,
                  padding: '4px 8px',
                  fontSize: 12,
                  cursor: 'pointer',
                }}
              >
                ▶️
              </button>
              <button
                title="Edit"
                onClick={() => handleEdit(wf)}
                style={{
                  backgroundColor: '#1E3A5F33',
                  color: '#90CAF9',
                  border: 'none',
                  borderRadius: 4,
                  padding: '4px 8px',
                  fontSize: 12,
                  cursor: 'pointer',
                }}
              >
                ✏️
              </button>
              <button
                title="Delete"
                onClick={() => handleDelete(wf.id, wf.name)}
                style={{
                  backgroundColor: '#B71C1C22',
                  color: '#EF9A9A',
                  border: 'none',
                  borderRadius: 4,
                  padding: '4px 8px',
                  fontSize: 12,
                  cursor: 'pointer',
                }}
              >
                🗑️
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
