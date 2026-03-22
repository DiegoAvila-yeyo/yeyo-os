/**
 * YeyoOS — Chat Node Frontend
 * Micro-fase 5.1 — Capa 5: Órganos
 *
 * Chat completo con tabs de conversación, búsqueda,
 * export y botones de enviar/voz.
 */

'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import NodeWrapper from '../NodeWrapper';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

interface ConversationTab {
  id: string;
  title: string;
  messageCount: number;
}

interface ChatNodeProps {
  nodeId: string;
  conversations: ConversationTab[];
  activeConversationId: string | null;
  onSendMessage: (message: string, conversationId: string) => void;
  onNewConversation: () => void;
  onSwitchConversation: (id: string) => void;
  onSearch: (query: string) => void;
  onExport: (conversationId: string) => void;
  onClose: (nodeId: string) => void;
  messages: Message[];
  isStreaming?: boolean;
}

export default function ChatNode({
  nodeId,
  conversations,
  activeConversationId,
  onSendMessage,
  onNewConversation,
  onSwitchConversation,
  onSearch,
  onExport,
  onClose,
  messages,
  isStreaming = false,
}: ChatNodeProps) {
  const [input, setInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [showSearch, setShowSearch] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = useCallback(() => {
    if (!input.trim() || !activeConversationId) return;
    onSendMessage(input.trim(), activeConversationId);
    setInput('');
  }, [input, activeConversationId, onSendMessage]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  return (
    <NodeWrapper nodeId={nodeId} title="Chat" icon="💬" onClose={onClose}>
      <div className="flex flex-col h-full">
        {/* Conversation tabs */}
        <div className="flex items-center gap-1 px-2 py-1 bg-gray-800
                        border-b border-gray-700 overflow-x-auto shrink-0">
          {conversations.map((conv) => (
            <button
              key={conv.id}
              onClick={() => onSwitchConversation(conv.id)}
              className={`px-3 py-1 text-xs rounded-t whitespace-nowrap
                ${conv.id === activeConversationId
                  ? 'bg-gray-900 text-white'
                  : 'bg-gray-700 text-gray-400 hover:text-white'}`}
            >
              {conv.title}
            </button>
          ))}
          <button
            onClick={onNewConversation}
            className="px-2 py-1 text-xs text-gray-400 hover:text-green-400"
          >
            +
          </button>
        </div>

        {/* Search bar */}
        {showSearch && (
          <div className="px-2 py-1 bg-gray-800 border-b border-gray-700">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && onSearch(searchQuery)}
              placeholder="Buscar mensajes..."
              className="w-full px-2 py-1 text-sm bg-gray-700 text-white
                         rounded border border-gray-600 focus:border-blue-500
                         focus:outline-none"
            />
          </div>
        )}

        {/* Toolbar */}
        <div className="flex items-center gap-2 px-2 py-1
                        border-b border-gray-700 shrink-0">
          <button
            onClick={() => setShowSearch(!showSearch)}
            className="text-xs text-gray-400 hover:text-white"
            title="Buscar"
          >
            🔍
          </button>
          <button
            onClick={() => activeConversationId && onExport(activeConversationId)}
            className="text-xs text-gray-400 hover:text-white"
            title="Exportar a Markdown"
          >
            📥
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-3 py-2 space-y-3">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] px-3 py-2 rounded-lg text-sm
                  ${msg.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-700 text-gray-200'}`}
              >
                {msg.content}
              </div>
            </div>
          ))}
          {isStreaming && (
            <div className="flex justify-start">
              <div className="bg-gray-700 px-3 py-2 rounded-lg text-sm text-gray-400">
                <span className="animate-pulse">●●●</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="flex items-center gap-2 px-3 py-2 bg-gray-800
                        border-t border-gray-700 shrink-0">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Escribe un mensaje..."
            rows={1}
            className="flex-1 px-3 py-2 text-sm bg-gray-700 text-white
                       rounded-lg border border-gray-600 focus:border-blue-500
                       focus:outline-none resize-none"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
            className="px-3 py-2 bg-blue-600 text-white rounded-lg text-sm
                       hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Enviar
          </button>
          <button
            className="px-3 py-2 bg-gray-700 text-gray-400 rounded-lg text-sm
                       hover:text-white cursor-not-allowed"
            title="Voz (próximamente)"
            disabled
          >
            🎤
          </button>
        </div>
      </div>
    </NodeWrapper>
  );
}
