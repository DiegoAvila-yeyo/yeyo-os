/**
 * YeyoOS — UI Store (Estado de la Interfaz)
 * Micro-fase 3.11 — Capa 3: Cuerpo
 */

import { create } from 'zustand';
import { persist, devtools } from 'zustand/middleware';

export type ActivePanel = 'chat' | 'settings' | 'files' | null;
export type ThemeMode = 'dark';

export interface UIState {
  activePanel: ActivePanel;
  theme: ThemeMode;
  sidebarCollapsed: boolean;
  miniChatVisible: boolean;
  commandPaletteOpen: boolean;

  setActivePanel: (panel: ActivePanel) => void;
  closeActivePanel: () => void;
  toggleSidebar: () => void;
  setMiniChatVisible: (visible: boolean) => void;
  toggleMiniChat: () => void;
  setCommandPaletteOpen: (open: boolean) => void;
}

export const useUIStore = create<UIState>()(
  devtools(
    persist(
      (set) => ({
        activePanel: null,
        theme: 'dark',
        sidebarCollapsed: false,
        miniChatVisible: false,
        commandPaletteOpen: false,

        setActivePanel: (panel) => set({ activePanel: panel }),
        closeActivePanel: () => set({ activePanel: null }),
        toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
        setMiniChatVisible: (visible) => set({ miniChatVisible: visible }),
        toggleMiniChat: () => set((s) => ({ miniChatVisible: !s.miniChatVisible })),
        setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),
      }),
      {
        name: 'yeyo-ui-store',
        partialize: (state) => ({
          theme: state.theme,
          sidebarCollapsed: state.sidebarCollapsed,
        }),
      }
    ),
    { name: 'YeyoOS UI Store' }
  )
);
