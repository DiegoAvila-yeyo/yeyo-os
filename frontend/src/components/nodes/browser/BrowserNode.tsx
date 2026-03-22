/**
 * YeyoOS — Browser Node Frontend
 * Micro-fase 5.13 — Capa 5: Órganos
 *
 * Webview sandboxed con navegación y resumen IA.
 */

'use client';

import React, { useState } from 'react';
import NodeWrapper from '../NodeWrapper';

interface BrowserNodeProps {
  nodeId: string;
  currentUrl: string;
  canGoBack: boolean;
  canGoForward: boolean;
  bookmarks: { id: string; title: string; url: string }[];
  onNavigate: (url: string) => void;
  onBack: () => void;
  onForward: () => void;
  onBookmark: () => void;
  onSummarize: () => void;
  onClose: (nodeId: string) => void;
}

export default function BrowserNode({
  nodeId, currentUrl, canGoBack, canGoForward, bookmarks,
  onNavigate, onBack, onForward, onBookmark, onSummarize, onClose,
}: BrowserNodeProps) {
  const [urlInput, setUrlInput] = useState(currentUrl);

  const handleNavigate = () => {
    if (urlInput.trim()) onNavigate(urlInput.trim());
  };

  return (
    <NodeWrapper nodeId={nodeId} title="Browser" icon="🌐" onClose={onClose}
                 initialWidth={800} initialHeight={600}>
      <div className="flex flex-col h-full">
        <div className="flex items-center gap-2 px-2 py-2 bg-gray-800
                        border-b border-gray-700 shrink-0">
          <button onClick={onBack} disabled={!canGoBack}
            className="px-2 py-1 text-xs bg-gray-700 rounded disabled:opacity-30">
            ←
          </button>
          <button onClick={onForward} disabled={!canGoForward}
            className="px-2 py-1 text-xs bg-gray-700 rounded disabled:opacity-30">
            →
          </button>
          <input
            type="text"
            value={urlInput}
            onChange={(e) => setUrlInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleNavigate()}
            className="flex-1 px-3 py-1 text-sm bg-gray-700 text-white
                       rounded-full border border-gray-600 focus:border-blue-500
                       focus:outline-none"
          />
          <button onClick={onBookmark}
            className="px-2 py-1 text-xs text-yellow-400 hover:text-yellow-300">
            ⭐
          </button>
          <button onClick={onSummarize}
            className="px-2 py-1 text-xs bg-blue-600 text-white rounded
                       hover:bg-blue-500">
            📝 Resumir
          </button>
        </div>
        <div className="flex-1 bg-white">
          <iframe
            src={currentUrl}
            className="w-full h-full border-none"
            sandbox="allow-scripts allow-same-origin allow-forms"
            title="Browser content"
            referrerPolicy="no-referrer"
          />
        </div>
      </div>
    </NodeWrapper>
  );
}
