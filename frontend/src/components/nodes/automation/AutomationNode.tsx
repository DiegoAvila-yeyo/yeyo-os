/**
 * YeyoOS — Automation Node Frontend
 * Micro-fase 5.10 — Capa 5: Órganos
 *
 * Canvas visual de pipelines con React Flow.
 */

'use client';

import React, { useState } from 'react';
import NodeWrapper from '../NodeWrapper';

interface FlowNode {
  id: string;
  type: string;
  label: string;
  nodeType: string;
  position: { x: number; y: number };
}

interface FlowEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
}

interface AutomationNodeProps {
  nodeId: string;
  nodes: FlowNode[];
  edges: FlowEdge[];
  savedPipelines: string[];
  onAddNode: (data: any) => void;
  onAddEdge: (source: string, target: string) => void;
  onRemoveNode: (nodeId: string) => void;
  onValidate: () => void;
  onExecute: (inputData?: any) => void;
  onSave: (name: string) => void;
  onClose: (nodeId: string) => void;
}

export default function AutomationNode({
  nodeId,
  nodes,
  edges,
  savedPipelines,
  onAddNode,
  onAddEdge,
  onRemoveNode,
  onValidate,
  onExecute,
  onSave,
  onClose,
}: AutomationNodeProps) {
  const [saveName, setSaveName] = useState('');

  const nodeTypes = [
    { type: 'input', label: '📥 Input', icon: '📥' },
    { type: 'process', label: '⚙️ Process', icon: '⚙️' },
    { type: 'output', label: '📤 Output', icon: '📤' },
  ];

  return (
    <NodeWrapper nodeId={nodeId} title="Automation" icon="🔄" onClose={onClose}
                 initialWidth={900} initialHeight={600}>
      <div className="flex h-full">
        {/* Sidebar: node palette */}
        <div className="w-48 bg-gray-800 border-r border-gray-700 p-2 space-y-2
                        shrink-0 overflow-y-auto">
          <h3 className="text-xs font-medium text-gray-400 uppercase">Pasos</h3>
          {nodeTypes.map((nt) => (
            <button
              key={nt.type}
              onClick={() => onAddNode({ type: nt.type, label: nt.label })}
              className="w-full px-2 py-2 text-xs bg-gray-700 text-gray-300
                         rounded hover:bg-gray-600 text-left"
            >
              {nt.icon} {nt.label}
            </button>
          ))}
          <hr className="border-gray-700" />
          <h3 className="text-xs font-medium text-gray-400 uppercase">Acciones</h3>
          <button onClick={onValidate}
            className="w-full px-2 py-1 text-xs bg-blue-600 text-white rounded">
            ✓ Validar
          </button>
          <button onClick={() => onExecute()}
            className="w-full px-2 py-1 text-xs bg-green-600 text-white rounded">
            ▶ Ejecutar
          </button>
          <div className="flex gap-1">
            <input
              type="text"
              value={saveName}
              onChange={(e) => setSaveName(e.target.value)}
              placeholder="Nombre..."
              className="flex-1 px-1 py-1 text-xs bg-gray-700 text-white rounded
                         border border-gray-600"
            />
            <button onClick={() => { onSave(saveName); setSaveName(''); }}
              className="px-2 py-1 text-xs bg-yellow-600 text-white rounded">
              💾
            </button>
          </div>
        </div>

        {/* Canvas area */}
        <div className="flex-1 bg-gray-950 relative">
          <div className="absolute inset-0 flex items-center justify-center
                          text-gray-600 text-sm">
            {nodes.length === 0
              ? 'Arrastra pasos desde la barra lateral para crear un pipeline'
              : `${nodes.length} nodos · ${edges.length} conexiones`}
          </div>

          {nodes.map((node) => (
            <div
              key={node.id}
              className="absolute bg-gray-800 border border-gray-600 rounded-lg
                         px-3 py-2 text-xs text-white cursor-move
                         hover:border-blue-500"
              style={{ left: node.position.x, top: node.position.y }}
            >
              <div className="flex items-center justify-between gap-2">
                <span>{node.label}</span>
                <button
                  onClick={() => onRemoveNode(node.id)}
                  className="text-gray-500 hover:text-red-400"
                >
                  ×
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </NodeWrapper>
  );
}
