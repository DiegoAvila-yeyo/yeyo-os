/**
 * YeyoOS — MiniChat v1 Overlay
 * Micro-fase 5.4 — Capa 5: Órganos
 *
 * Overlay de chat que aparece al hacer click en una imagen.
 * v1: Q&A básico sobre la imagen usando LLaVA.
 */

'use client';

import React, { useState, useRef, useEffect } from 'react';

interface MiniChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

interface MiniChatOverlayProps {
  isOpen: boolean;
  imageId: string;
  messages: MiniChatMessage[];
  onAsk: (question: string) => void;
  onClose: () => void;
  isLoading?: boolean;
}

export default function MiniChatOverlay({
  isOpen,
  imageId,
  messages,
  onAsk,
  onClose,
  isLoading = false,
}: MiniChatOverlayProps) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (!isOpen) return null;

  const handleSend = () => {
    if (!input.trim() || isLoading) return;
    onAsk(input.trim());
    setInput('');
  };

  return (
    <div className="fixed bottom-4 right-4 w-80 bg-gray-900 border border-gray-600
                    rounded-xl shadow-2xl flex flex-col z-50"
         style={{ maxHeight: '400px' }}>
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2
                      bg-gray-800 rounded-t-xl border-b border-gray-700">
        <span className="text-sm font-medium text-gray-200">
          💬 MiniChat — Imagen
        </span>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-white text-xs"
        >
          ✕
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-2"
           style={{ maxHeight: '280px' }}>
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] px-2 py-1 rounded-lg text-xs
              ${msg.role === 'user'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-200'}`}>
              {msg.content}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="text-xs text-gray-400 animate-pulse">Analizando...</div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="flex items-center gap-1 px-2 py-2 border-t border-gray-700">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Pregunta sobre la imagen..."
          className="flex-1 px-2 py-1 text-xs bg-gray-700 text-white rounded
                     border border-gray-600 focus:border-blue-500 focus:outline-none"
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || isLoading}
          className="px-2 py-1 bg-blue-600 text-white rounded text-xs
                     disabled:opacity-50"
        >
          →
        </button>
      </div>
    </div>
  );
}
