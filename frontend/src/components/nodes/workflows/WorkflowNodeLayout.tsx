/**
 * YeyoOS — WorkflowNodeLayout
 * Main layout for the Workflow Orchestrator node.
 * 3 tabs: Mis Workflows | Diseñador | Ejecuciones
 */

import React, { useEffect } from 'react'
import { useWorkflowStore } from '@/stores/workflowStore'
import { WorkflowList } from './WorkflowList'
import { FlowDesigner } from './FlowDesigner'
import { ExecutionView } from './ExecutionView'

type TabKey = 'list' | 'designer' | 'executions'

const TABS: Array<{ key: TabKey; label: string }> = [
  { key: 'list', label: '📋 Mis Workflows' },
  { key: 'designer', label: '🎨 Diseñador' },
  { key: 'executions', label: '📊 Ejecuciones' },
]

export function WorkflowNodeLayout() {
  const activeTab = useWorkflowStore((s) => s.activeTab)
  const setActiveTab = useWorkflowStore((s) => s.setActiveTab)
  const fetchWorkflows = useWorkflowStore((s) => s.fetchWorkflows)
  const fetchNodeTypes = useWorkflowStore((s) => s.fetchNodeTypes)
  const error = useWorkflowStore((s) => s.error)
  const setError = useWorkflowStore((s) => s.setError)

  useEffect(() => {
    fetchWorkflows()
    fetchNodeTypes()
  }, [fetchWorkflows, fetchNodeTypes])

  return (
    <div
      data-testid="workflow-node-layout"
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        backgroundColor: '#060B18',
        color: '#E0F7FA',
        fontFamily: 'system-ui, -apple-system, sans-serif',
      }}
    >
      {/* Tab bar */}
      <div
        data-testid="workflow-tabs"
        style={{
          display: 'flex',
          borderBottom: '1px solid #1E3A5F',
          backgroundColor: '#080D1C',
          flexShrink: 0,
        }}
      >
        {TABS.map((tab) => {
          const isActive = activeTab === tab.key
          return (
            <button
              key={tab.key}
              data-testid={`tab-${tab.key}`}
              onClick={() => setActiveTab(tab.key)}
              style={{
                flex: 1,
                padding: '10px 0',
                backgroundColor: isActive ? '#060B18' : 'transparent',
                color: isActive ? '#4FC3F7' : '#607D8B',
                border: 'none',
                borderBottom: isActive ? '2px solid #4FC3F7' : '2px solid transparent',
                fontSize: 12,
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'color 0.15s, border-color 0.15s',
              }}
            >
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* Error banner */}
      {error && (
        <div
          style={{
            padding: '6px 14px',
            backgroundColor: '#B71C1C22',
            color: '#EF9A9A',
            fontSize: 11,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexShrink: 0,
          }}
        >
          <span>⚠️ {error}</span>
          <button
            onClick={() => setError(null)}
            style={{ background: 'none', border: 'none', color: '#EF9A9A', cursor: 'pointer', fontSize: 13 }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Tab content */}
      <div style={{ flex: 1, overflow: 'hidden' }}>
        {activeTab === 'list' && <WorkflowList />}
        {activeTab === 'designer' && <FlowDesigner />}
        {activeTab === 'executions' && <ExecutionView />}
      </div>
    </div>
  )
}
