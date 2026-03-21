/**
 * YeyoOS — Chat Store (Estado del Chat)
 * Micro-fase 3.5 — Capa 3: Cuerpo
 */

import { create } from 'zustand';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
  isStreaming?: boolean;
}

export interface ChatState {
  messages: ChatMessage[];
  isStreaming: boolean;
  isPanelOpen: boolean;
  error: string | null;

  addMessage: (message: ChatMessage) => void;
  updateStreamingMessage: (id: string, content: string) => void;
  finalizeStreamingMessage: (id: string) => void;
  setStreaming: (streaming: boolean) => void;
  setPanelOpen: (open: boolean) => void;
  togglePanel: () => void;
  setError: (error: string | null) => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  isStreaming: false,
  isPanelOpen: false,
  error: null,

  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),

  updateStreamingMessage: (id, content) =>
    set((state) => ({
      messages: state.messages.map((m) => (m.id === id ? { ...m, content } : m)),
    })),

  finalizeStreamingMessage: (id) =>
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id ? { ...m, isStreaming: false } : m
      ),
      isStreaming: false,
    })),

  setStreaming: (streaming) => set({ isStreaming: streaming }),
  setPanelOpen: (open) => set({ isPanelOpen: open }),
  togglePanel: () => set((state) => ({ isPanelOpen: !state.isPanelOpen })),
  setError: (error) => set({ error }),
  clearMessages: () => set({ messages: [] }),
}));
