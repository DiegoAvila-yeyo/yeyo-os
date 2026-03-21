/**
 * YeyoOS — MiniChat (Widget Flotante de Chat Rápido)
 * Micro-fase 3.6 — Capa 3: Cuerpo
 *
 * Widget compacto flotante sobre el canvas.
 * Ctrl+Space para toggle. Click expandir para ChatPanel.
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
import { useChatStore } from '@/lib/store/chat-store';

export const DEFAULT_WIDTH = 300;
export const DEFAULT_HEIGHT = 200;
export const MIN_WIDTH = 250;
export const MIN_HEIGHT = 150;
export const MAX_WIDTH = 500;
export const MAX_HEIGHT = 400;
export const MAX_VISIBLE_MESSAGES = 3;

export interface MiniChatProps {
  initialX?: number;
  initialY?: number;
}

export default function MiniChat({ initialX = 20, initialY = 20 }: MiniChatProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [position, setPosition] = useState({ x: initialX, y: initialY });
  const [size, setSize] = useState({ width: DEFAULT_WIDTH, height: DEFAULT_HEIGHT });
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const [input, setInput] = useState('');

  const dragOffsetRef = useRef({ x: 0, y: 0 });
  const resizeStartRef = useRef({ x: 0, y: 0, w: 0, h: 0 });

  const { messages, isStreaming, addMessage, setPanelOpen } = useChatStore();
  const visibleMessages = messages.slice(-MAX_VISIBLE_MESSAGES);

  // Ctrl+Space toggle
  useEffect(() => {
    const handleKeyDown = (e: globalThis.KeyboardEvent) => {
      if (e.ctrlKey && e.code === 'Space') {
        e.preventDefault();
        setIsVisible((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Drag
  const handleDragStart = useCallback(
    (e: React.MouseEvent) => {
      if ((e.target as HTMLElement).dataset.resize) return;
      setIsDragging(true);
      dragOffsetRef.current = { x: e.clientX - position.x, y: e.clientY - position.y };
    },
    [position]
  );

  useEffect(() => {
    if (!isDragging) return;
    const handleMove = (e: MouseEvent) => {
      setPosition({
        x: Math.max(0, e.clientX - dragOffsetRef.current.x),
        y: Math.max(0, e.clientY - dragOffsetRef.current.y),
      });
    };
    const handleUp = () => setIsDragging(false);
    window.addEventListener('mousemove', handleMove);
    window.addEventListener('mouseup', handleUp);
    return () => {
      window.removeEventListener('mousemove', handleMove);
      window.removeEventListener('mouseup', handleUp);
    };
  }, [isDragging]);

  // Resize
  const handleResizeStart = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      setIsResizing(true);
      resizeStartRef.current = { x: e.clientX, y: e.clientY, w: size.width, h: size.height };
    },
    [size]
  );

  useEffect(() => {
    if (!isResizing) return;
    const handleMove = (e: MouseEvent) => {
      const ref = resizeStartRef.current;
      setSize({
        width: Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, ref.w + (e.clientX - ref.x))),
        height: Math.min(MAX_HEIGHT, Math.max(MIN_HEIGHT, ref.h + (e.clientY - ref.y))),
      });
    };
    const handleUp = () => setIsResizing(false);
    window.addEventListener('mousemove', handleMove);
    window.addEventListener('mouseup', handleUp);
    return () => {
      window.removeEventListener('mousemove', handleMove);
      window.removeEventListener('mouseup', handleUp);
    };
  }, [isResizing]);

  const handleExpand = useCallback(() => {
    setIsVisible(false);
    setPanelOpen(true);
  }, [setPanelOpen]);

  const handleSend = useCallback(
    (e: FormEvent) => {
      e.preventDefault();
      if (!input.trim() || isStreaming) return;
      addMessage({
        id: `mini-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
        role: 'user',
        content: input.trim(),
        timestamp: Date.now(),
      });
      setInput('');
    },
    [input, isStreaming, addMessage]
  );

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend(e as unknown as FormEvent);
    }
  };

  if (!isVisible) return null;

  return (
    <div
      data-testid="minichat"
      className="fixed bg-[#0d0d14] border border-[#333355] rounded-xl shadow-2xl flex flex-col z-[60] select-none"
      style={{
        left: `${position.x}px`,
        top: `${position.y}px`,
        width: `${size.width}px`,
        height: `${size.height}px`,
      }}
    >
      {/* Header / drag handle */}
      <div
        data-testid="minichat-header"
        className="flex items-center justify-between px-3 py-2 border-b border-[#1a1a2e] cursor-move"
        onMouseDown={handleDragStart}
      >
        <span className="text-gray-300 text-xs font-medium">⚡ MiniChat</span>
        <div className="flex gap-2">
          <button
            data-testid="minichat-expand"
            onClick={handleExpand}
            className="text-gray-400 hover:text-blue-400 text-xs transition-colors"
            title="Expandir a ChatPanel"
          >
            ⤢
          </button>
          <button
            data-testid="minichat-close"
            onClick={() => setIsVisible(false)}
            className="text-gray-400 hover:text-white text-xs transition-colors"
          >
            ✕
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-3 py-2 text-xs space-y-1.5">
        {visibleMessages.length === 0 ? (
          <p className="text-gray-500 text-center mt-4">Sin mensajes aún</p>
        ) : (
          visibleMessages.map((msg) => (
            <div
              key={msg.id}
              data-testid={`minichat-msg-${msg.id}`}
              className={`rounded px-2 py-1 ${
                msg.role === 'user'
                  ? 'bg-blue-600/20 text-blue-200 text-right'
                  : 'bg-[#1a1a2e] text-gray-300'
              }`}
            >
              <p className="truncate">{msg.content}</p>
            </div>
          ))
        )}
      </div>

      {/* Input */}
      <form
        onSubmit={handleSend}
        className="flex items-center gap-1.5 px-3 py-2 border-t border-[#1a1a2e]"
      >
        <input
          data-testid="minichat-input"
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Mensaje rápido..."
          disabled={isStreaming}
          className="flex-1 bg-[#1a1a2e] text-gray-200 rounded px-2 py-1 text-xs placeholder-gray-500 border border-[#333355] focus:border-blue-500 focus:outline-none disabled:opacity-50"
        />
        <button
          data-testid="minichat-send"
          type="submit"
          disabled={isStreaming || !input.trim()}
          className="bg-blue-600 text-white rounded px-2 py-1 text-xs hover:bg-blue-500 disabled:opacity-40 transition-colors"
        >
          ➤
        </button>
      </form>

      {/* Resize handle */}
      <div
        data-resize="true"
        data-testid="minichat-resize"
        onMouseDown={handleResizeStart}
        className="absolute bottom-0 right-0 w-4 h-4 cursor-se-resize"
      />
    </div>
  );
}
