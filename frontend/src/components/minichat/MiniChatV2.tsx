/**
 * YeyoOS — MiniChat v2 (Node Context)
 * Micro-fase 5.18 — Capa 5: Órganos
 *
 * MiniChat contextual: sabe en qué nodo está y sugiere acciones relevantes.
 */

'use client';

import React, { useState, useRef, useEffect } from 'react';

interface MiniChatV2Props {
  isOpen: boolean;
  nodeType: string;
  nodeId: string;
  messages: { role: string; content: string }[];
  suggestions: string[];
  onSend: (message: string) => void;
  onSuggestionClick: (suggestion: string) => void;
  onClose: () => void;
  isLoading?: boolean;
}

export default function MiniChatV2({
  isOpen, nodeType, nodeId, messages, suggestions,
  onSend, onSuggestionClick, onClose, isLoading = false,
}: MiniChatV2Props) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (!isOpen) return null;

  const handleSend = () => {
    if (!input.trim() || isLoading) return;
    onSend(input.trim());
    setInput('');
  };

  return (
    <div className="fixed bottom-4 right-4 w-80 bg-gray-900 border border-gray-600
                    rounded-xl shadow-2xl flex flex-col z-50"
         style={{ maxHeight: '450px' }}>
      <div className="flex items-center justify-between px-3 py-2
                      bg-gray-800 rounded-t-xl border-b border-gray-700">
        <div>
          <span className="text-sm font-medium text-gray-200">💬 MiniChat</span>
          <span className="text-[10px] text-gray-500 ml-2">📍 {nodeType}</span>
        </div>
        <button onClick={onClose} className="text-gray-400 hover:text-white text-xs">✕</button>
      </div>

      {messages.length === 0 && (
        <div className="px-3 py-2 flex flex-wrap gap-1">
          {suggestions.map((s, i) => (
            <button
              key={i}
              onClick={() => onSuggestionClick(s)}
              className="px-2 py-1 text-[10px] bg-gray-700 text-gray-300
                         rounded-full hover:bg-gray-600"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-2"
           style={{ maxHeight: '300px' }}>
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] px-2 py-1 rounded-lg text-xs
              ${msg.role === 'user' ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-200'}`}>
              {msg.content}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="text-xs text-gray-400 animate-pulse">Pensando...</div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="flex items-center gap-1 px-2 py-2 border-t border-gray-700">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder={`Pregunta sobre ${nodeType}...`}
          className="flex-1 px-2 py-1 text-xs bg-gray-700 text-white rounded
                     border border-gray-600 focus:border-blue-500 focus:outline-none"
        />
        <button onClick={handleSend} disabled={!input.trim() || isLoading}
          className="px-2 py-1 bg-blue-600 text-white rounded text-xs disabled:opacity-50">
          →
        </button>
      </div>
    </div>
  );
}
