/**
 * YeyoOS — ChatPanel (Panel de Chat Principal)
 * Micro-fase 3.5 — Capa 3: Cuerpo
 *
 * Panel slide-in con chat streaming, markdown rendering
 * y batch flush de 50ms.
 */

'use client';

import {
  useState,
  useRef,
  useEffect,
  useCallback,
  type FormEvent,
  type KeyboardEvent,
} from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useChatStore, type ChatMessage } from '@/lib/store/chat-store';

export const PANEL_WIDTH = 400;
export const BATCH_FLUSH_MS = 50;

function generateId(): string {
  return `msg-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user';

  return (
    <div
      data-testid={`message-${message.id}`}
      className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}
    >
      <div
        className={`max-w-[85%] rounded-xl px-4 py-2.5 text-sm ${
          isUser
            ? 'bg-blue-600 text-white rounded-br-sm'
            : 'bg-[#1a1a2e] text-gray-200 rounded-bl-sm border border-[#333355]'
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className="prose prose-invert prose-sm max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
          </div>
        )}
        {message.isStreaming && (
          <span
            data-testid="streaming-indicator"
            className="inline-block w-2 h-4 bg-blue-400 animate-pulse ml-1"
          />
        )}
      </div>
    </div>
  );
}

function LoadingIndicator() {
  return (
    <div data-testid="loading-indicator" className="flex justify-start mb-3">
      <div className="bg-[#1a1a2e] rounded-xl px-4 py-3 border border-[#333355]">
        <div className="flex space-x-1.5">
          <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
          <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
          <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
      </div>
    </div>
  );
}

export default function ChatPanel() {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const {
    messages,
    isStreaming,
    isPanelOpen,
    error,
    addMessage,
    updateStreamingMessage,
    finalizeStreamingMessage,
    setStreaming,
    setError,
  } = useChatStore();

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  useEffect(() => {
    if (isPanelOpen) inputRef.current?.focus();
  }, [isPanelOpen]);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || isStreaming) return;

      const userMessage: ChatMessage = {
        id: generateId(),
        role: 'user',
        content: text.trim(),
        timestamp: Date.now(),
      };
      addMessage(userMessage);
      setInput('');
      setError(null);
      setStreaming(true);

      const assistantId = generateId();
      addMessage({
        id: assistantId,
        role: 'assistant',
        content: '',
        timestamp: Date.now(),
        isStreaming: true,
      });

      try {
        abortControllerRef.current = new AbortController();

        const response = await fetch('/api/v1/chat/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: text.trim() }),
          signal: abortControllerRef.current.signal,
        });

        if (!response.ok) {
          throw new Error(`Error ${response.status}: ${response.statusText}`);
        }

        const reader = response.body?.getReader();
        if (!reader) throw new Error('No response body');

        const decoder = new TextDecoder();
        let buffer = '';
        let fullContent = '';
        let flushTimer: ReturnType<typeof setTimeout> | null = null;
        let pendingChunks = '';

        const flushBuffer = () => {
          if (buffer) {
            fullContent += buffer;
            updateStreamingMessage(assistantId, fullContent);
            buffer = '';
          }
          flushTimer = null;
        };

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          pendingChunks += decoder.decode(value, { stream: true });

          // Parse SSE: each line is "data: <content>\n\n"
          const lines = pendingChunks.split('\n');
          pendingChunks = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const chunk = line.slice(6);
              if (chunk === '[DONE]') continue;
              buffer += chunk;
            }
          }

          if (!flushTimer) flushTimer = setTimeout(flushBuffer, BATCH_FLUSH_MS);
        }

        if (flushTimer) clearTimeout(flushTimer);
        flushBuffer();
        finalizeStreamingMessage(assistantId);
      } catch (err) {
        if ((err as Error).name === 'AbortError') return;
        setError((err as Error).message);
        finalizeStreamingMessage(assistantId);
      }
    },
    [isStreaming, addMessage, updateStreamingMessage, finalizeStreamingMessage, setStreaming, setError]
  );

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  if (!isPanelOpen) return null;

  return (
    <div
      data-testid="chat-panel"
      className="fixed top-0 right-0 h-full bg-[#0d0d14] border-l border-[#1a1a2e] shadow-2xl flex flex-col z-50"
      style={{ width: `${PANEL_WIDTH}px` }}
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#1a1a2e]">
        <h2 className="text-white font-semibold text-sm">💬 Chat — YeyoOS</h2>
        <button
          data-testid="close-panel"
          onClick={() => useChatStore.getState().setPanelOpen(false)}
          className="text-gray-400 hover:text-white transition-colors text-lg"
        >
          ✕
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        {isStreaming && messages[messages.length - 1]?.role !== 'assistant' && (
          <LoadingIndicator />
        )}
        <div ref={messagesEndRef} />
      </div>

      {error && (
        <div data-testid="chat-error" className="px-4 py-2 bg-red-900/30 border-t border-red-800 text-red-300 text-xs">
          {error}
        </div>
      )}

      <form
        onSubmit={handleSubmit}
        className="flex items-center gap-2 px-4 py-3 border-t border-[#1a1a2e]"
      >
        <input
          ref={inputRef}
          data-testid="chat-input"
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Escribe un mensaje..."
          disabled={isStreaming}
          className="flex-1 bg-[#1a1a2e] text-gray-200 rounded-lg px-3 py-2 text-sm placeholder-gray-500 border border-[#333355] focus:border-blue-500 focus:outline-none disabled:opacity-50"
        />
        <button
          data-testid="send-button"
          type="submit"
          disabled={isStreaming || !input.trim()}
          className="bg-blue-600 text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          Enviar
        </button>
      </form>
    </div>
  );
}

export { MessageBubble, LoadingIndicator, generateId };
