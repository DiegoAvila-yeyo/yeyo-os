/**
 * YeyoOS — Files Node Frontend
 * Micro-fase 5.12 — Capa 5: Órganos
 */

'use client';

import React, { useState } from 'react';
import NodeWrapper from '../NodeWrapper';

interface FileTreeItem {
  name: string;
  path: string;
  isDirectory: boolean;
  size?: number;
  extension?: string;
  children?: FileTreeItem[];
}

interface FilesNodeProps {
  nodeId: string;
  rootPath: string;
  tree: FileTreeItem[];
  onNavigate: (path: string) => void;
  onPreview: (path: string) => void;
  onSearch: (query: string) => void;
  onClose: (nodeId: string) => void;
}

function FileTree({ items, onNavigate, onPreview, depth = 0 }: {
  items: FileTreeItem[];
  onNavigate: (path: string) => void;
  onPreview: (path: string) => void;
  depth?: number;
}) {
  return (
    <div style={{ paddingLeft: depth * 16 }}>
      {items.map((item) => (
        <div key={item.path}>
          <div
            onClick={() => item.isDirectory ? onNavigate(item.path) : onPreview(item.path)}
            className="flex items-center gap-1 px-1 py-0.5 text-xs
                       hover:bg-gray-700 rounded cursor-pointer text-gray-300"
          >
            <span>{item.isDirectory ? '📁' : '📄'}</span>
            <span className="truncate">{item.name}</span>
            {!item.isDirectory && item.size && (
              <span className="text-gray-500 ml-auto text-[10px]">
                {(item.size / 1024).toFixed(1)}KB
              </span>
            )}
          </div>
          {item.isDirectory && item.children && (
            <FileTree items={item.children} onNavigate={onNavigate}
                      onPreview={onPreview} depth={depth + 1} />
          )}
        </div>
      ))}
    </div>
  );
}

export default function FilesNode({
  nodeId, rootPath, tree, onNavigate, onPreview, onSearch, onClose,
}: FilesNodeProps) {
  const [searchQuery, setSearchQuery] = useState('');

  return (
    <NodeWrapper nodeId={nodeId} title="Files" icon="📁" onClose={onClose}>
      <div className="flex flex-col h-full">
        <div className="flex items-center gap-2 px-2 py-2 bg-gray-800
                        border-b border-gray-700 shrink-0">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && onSearch(searchQuery)}
            placeholder="Buscar por significado..."
            className="flex-1 px-2 py-1 text-xs bg-gray-700 text-white
                       rounded border border-gray-600 focus:outline-none"
          />
          <button
            onClick={() => onSearch(searchQuery)}
            className="px-2 py-1 text-xs bg-blue-600 text-white rounded"
          >
            🔍
          </button>
        </div>
        <div className="flex-1 overflow-y-auto py-1">
          <FileTree items={tree} onNavigate={onNavigate} onPreview={onPreview} />
        </div>
      </div>
    </NodeWrapper>
  );
}
