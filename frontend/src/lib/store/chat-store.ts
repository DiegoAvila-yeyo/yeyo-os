/**
 * YeyoOS — Chat Store (Estado del Chat)
 * Micro-fase 3.5 — Capa 3: Cuerpo
 * 
 * Phase 3.1.1: Agregado conversation_id persistence para integración con ChatNode
 * Phase 3.1.2: conversation_id persiste en localStorage para sobrevivir refreshes
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

const STORAGE_KEY = 'yeyoos-conversation-id';

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
  conversationId: string | null;

  addMessage: (message: ChatMessage) => void;
  updateStreamingMessage: (id: string, content: string) => void;
  finalizeStreamingMessage: (id: string) => void;
  setStreaming: (streaming: boolean) => void;
  setPanelOpen: (open: boolean) => void;
  togglePanel: () => void;
  setError: (error: string | null) => void;
  clearMessages: () => void;
  setConversationId: (id: string) => void;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set) => ({
      messages: [],
      isStreaming: false,
      isPanelOpen: false,
      error: null,
      conversationId: null,

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
      clearMessages: () => set({ messages: [], conversationId: null }),
      setConversationId: (id) => set({ conversationId: id }),
    }),
    {
      name: STORAGE_KEY,
      // Only persist conversationId and messages — not UI state
      partialize: (state: ChatState) => ({
        conversationId: state.conversationId,
        messages: state.messages,
      }),
    }
  )
);
