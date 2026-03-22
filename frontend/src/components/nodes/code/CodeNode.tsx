/**
 * YeyoOS — Code Node Frontend
 * Micro-fase 5.7 — Capa 5: Órganos
 */

'use client';

import React, { useState } from 'react';
import NodeWrapper from '../NodeWrapper';

interface CodeTab {
  id: string;
  filename: string;
  language: string;
  isModified: boolean;
}

interface CodeNodeProps {
  nodeId: string;
  tabs: CodeTab[];
  activeTabId: string | null;
  languages: string[];
  onOpenTab: (filename: string) => void;
  onCloseTab: (tabId: string) => void;
  onSaveTab: (tabId: string, content: string) => void;
  onSwitchTab: (tabId: string) => void;
  onRun: (code: string, language: string) => void;
  onExplain: (code: string) => void;
  onClose: (nodeId: string) => void;
  content?: string;
  output?: string;
  isRunning?: boolean;
}

export default function CodeNode({
  nodeId,
  tabs,
  activeTabId,
  languages,
  onOpenTab,
  onCloseTab,
  onSaveTab,
  onSwitchTab,
  onRun,
  onExplain,
  onClose,
  content = '',
  output = '',
  isRunning = false,
}: CodeNodeProps) {
  const [code, setCode] = useState(content);
  const [language, setLanguage] = useState('python');

  return (
    <NodeWrapper
      nodeId={nodeId}
      title="Code"
      icon="💻"
      onClose={onClose}
      initialWidth={700}
      initialHeight={500}
    >
      <div className="flex flex-col h-full gap-2">
        {/* Tabs */}
        <div className="flex items-center gap-1 overflow-x-auto shrink-0">
          {tabs.map((tab) => (
            <div
              key={tab.id}
              className={`flex items-center gap-1 px-2 py-1 text-xs rounded-t cursor-pointer
                ${tab.id === activeTabId
                  ? 'bg-gray-900 text-white'
                  : 'bg-gray-700 text-gray-400 hover:text-white'}`}
            >
              <span onClick={() => onSwitchTab(tab.id)}>
                {tab.filename} {tab.isModified ? '●' : ''}
              </span>
              <button
                onClick={() => onCloseTab(tab.id)}
                className="text-gray-500 hover:text-red-400 ml-1"
              >
                ×
              </button>
            </div>
          ))}
          <button
            onClick={() => onOpenTab('untitled.py')}
            className="px-2 py-1 text-xs text-gray-400 hover:text-green-400"
          >
            +
          </button>
        </div>

        {/* Editor */}
        <div className="flex-1 min-h-0">
          <textarea
            value={code}
            onChange={(e) => setCode(e.target.value)}
            className="w-full h-full px-3 py-2 text-sm font-mono bg-gray-950
                       text-green-400 rounded border border-gray-700
                       focus:border-blue-500 focus:outline-none resize-none"
            spellCheck={false}
          />
        </div>

        {/* Toolbar */}
        <div className="flex items-center gap-2 shrink-0">
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="px-2 py-1 text-xs bg-gray-700 text-white rounded
                       border border-gray-600"
          >
            {languages.map((l) => (
              <option key={l} value={l}>{l}</option>
            ))}
          </select>
          <button
            onClick={() => onRun(code, language)}
            disabled={isRunning}
            className="px-3 py-1 bg-green-600 text-white text-xs rounded
                       hover:bg-green-500 disabled:opacity-50"
          >
            {isRunning ? '⏳ Running...' : '▶ Run'}
          </button>
          <button
            onClick={() => onExplain(code)}
            className="px-3 py-1 bg-blue-600 text-white text-xs rounded
                       hover:bg-blue-500"
          >
            🤖 Explain
          </button>
          <button
            onClick={() => activeTabId && onSaveTab(activeTabId, code)}
            className="px-3 py-1 bg-gray-600 text-white text-xs rounded
                       hover:bg-gray-500"
          >
            💾 Save
          </button>
        </div>

        {/* Output */}
        {output && (
          <div className="max-h-32 overflow-y-auto px-3 py-2 bg-gray-950
                          rounded border border-gray-700 shrink-0">
            <pre className="text-xs text-gray-300 whitespace-pre-wrap font-mono">
              {output}
            </pre>
          </div>
        )}
      </div>
    </NodeWrapper>
  );
}
