/**
 * Tests para Zustand State Architecture — Micro-fase 3.11
 */

import { act } from '@testing-library/react';
import { useUIStore } from '@/lib/store/ui-store';
import { useSystemStore, DEFAULT_GPU, DEFAULT_HEALTH } from '@/lib/store/system-store';

describe('Zustand State Architecture', () => {
  describe('UIStore', () => {
    beforeEach(() => {
      act(() => {
        useUIStore.setState({
          activePanel: null,
          theme: 'dark',
          sidebarCollapsed: false,
          miniChatVisible: false,
          commandPaletteOpen: false,
        });
      });
    });

    it('estado inicial correcto', () => {
      const state = useUIStore.getState();
      expect(state.activePanel).toBeNull();
      expect(state.theme).toBe('dark');
      expect(state.sidebarCollapsed).toBe(false);
      expect(state.miniChatVisible).toBe(false);
    });

    it('setActivePanel cambia el panel activo', () => {
      act(() => {
        useUIStore.getState().setActivePanel('chat');
      });
      expect(useUIStore.getState().activePanel).toBe('chat');
    });

    it('setActivePanel acepta files y settings', () => {
      act(() => { useUIStore.getState().setActivePanel('files'); });
      expect(useUIStore.getState().activePanel).toBe('files');
      act(() => { useUIStore.getState().setActivePanel('settings'); });
      expect(useUIStore.getState().activePanel).toBe('settings');
    });

    it('closeActivePanel pone null', () => {
      act(() => {
        useUIStore.getState().setActivePanel('settings');
        useUIStore.getState().closeActivePanel();
      });
      expect(useUIStore.getState().activePanel).toBeNull();
    });

    it('toggleSidebar alterna collapsed', () => {
      act(() => { useUIStore.getState().toggleSidebar(); });
      expect(useUIStore.getState().sidebarCollapsed).toBe(true);
      act(() => { useUIStore.getState().toggleSidebar(); });
      expect(useUIStore.getState().sidebarCollapsed).toBe(false);
    });

    it('setMiniChatVisible establece visibilidad directa', () => {
      act(() => { useUIStore.getState().setMiniChatVisible(true); });
      expect(useUIStore.getState().miniChatVisible).toBe(true);
      act(() => { useUIStore.getState().setMiniChatVisible(false); });
      expect(useUIStore.getState().miniChatVisible).toBe(false);
    });

    it('toggleMiniChat alterna visibilidad', () => {
      act(() => { useUIStore.getState().toggleMiniChat(); });
      expect(useUIStore.getState().miniChatVisible).toBe(true);
      act(() => { useUIStore.getState().toggleMiniChat(); });
      expect(useUIStore.getState().miniChatVisible).toBe(false);
    });

    it('setCommandPaletteOpen funciona', () => {
      act(() => { useUIStore.getState().setCommandPaletteOpen(true); });
      expect(useUIStore.getState().commandPaletteOpen).toBe(true);
      act(() => { useUIStore.getState().setCommandPaletteOpen(false); });
      expect(useUIStore.getState().commandPaletteOpen).toBe(false);
    });

    it('tema siempre es dark', () => {
      expect(useUIStore.getState().theme).toBe('dark');
    });
  });

  describe('SystemStore', () => {
    beforeEach(() => {
      act(() => {
        useSystemStore.setState({
          connectionStatus: 'disconnected',
          gpuStatus: { ...DEFAULT_GPU },
          serviceHealth: { ...DEFAULT_HEALTH },
          killSwitchActive: false,
          lastHealthCheck: null,
        });
      });
    });

    it('estado inicial con GPU GTX 1060 3GB', () => {
      const { gpuStatus } = useSystemStore.getState();
      expect(gpuStatus.vramTotalMB).toBe(3072);
      expect(gpuStatus.available).toBe(false);
      expect(gpuStatus.temperature).toBeNull();
    });

    it('estado inicial con servicios desconectados', () => {
      const { serviceHealth } = useSystemStore.getState();
      expect(serviceHealth.ollama).toBe(false);
      expect(serviceHealth.postgres).toBe(false);
      expect(serviceHealth.redis).toBe(false);
      expect(serviceHealth.api).toBe(false);
    });

    it('setConnectionStatus cambia a connected', () => {
      act(() => { useSystemStore.getState().setConnectionStatus('connected'); });
      expect(useSystemStore.getState().connectionStatus).toBe('connected');
    });

    it('setConnectionStatus cambia a error', () => {
      act(() => { useSystemStore.getState().setConnectionStatus('error'); });
      expect(useSystemStore.getState().connectionStatus).toBe('error');
    });

    it('updateGPUStatus actualiza parcialmente', () => {
      act(() => {
        useSystemStore.getState().updateGPUStatus({
          available: true,
          vramUsedMB: 1500,
        });
      });
      const { gpuStatus } = useSystemStore.getState();
      expect(gpuStatus.available).toBe(true);
      expect(gpuStatus.vramUsedMB).toBe(1500);
      expect(gpuStatus.vramTotalMB).toBe(3072);
    });

    it('updateGPUStatus preserva temperatura al actualizar VRAM', () => {
      act(() => {
        useSystemStore.getState().updateGPUStatus({ temperature: 72 });
        useSystemStore.getState().updateGPUStatus({ vramUsedMB: 2000 });
      });
      expect(useSystemStore.getState().gpuStatus.temperature).toBe(72);
    });

    it('updateServiceHealth actualiza parcialmente', () => {
      act(() => {
        useSystemStore.getState().updateServiceHealth({ ollama: true, postgres: true });
      });
      const { serviceHealth } = useSystemStore.getState();
      expect(serviceHealth.ollama).toBe(true);
      expect(serviceHealth.postgres).toBe(true);
      expect(serviceHealth.redis).toBe(false);
    });

    it('setKillSwitchActive activa', () => {
      act(() => { useSystemStore.getState().setKillSwitchActive(true); });
      expect(useSystemStore.getState().killSwitchActive).toBe(true);
    });

    it('setLastHealthCheck guarda timestamp', () => {
      const now = Date.now();
      act(() => { useSystemStore.getState().setLastHealthCheck(now); });
      expect(useSystemStore.getState().lastHealthCheck).toBe(now);
    });

    it('DEFAULT_GPU tiene 3072MB (GTX 1060 3GB)', () => {
      expect(DEFAULT_GPU.vramTotalMB).toBe(3072);
    });

    it('DEFAULT_HEALTH tiene todos los servicios en false', () => {
      expect(DEFAULT_HEALTH.ollama).toBe(false);
      expect(DEFAULT_HEALTH.postgres).toBe(false);
      expect(DEFAULT_HEALTH.redis).toBe(false);
      expect(DEFAULT_HEALTH.api).toBe(false);
    });
  });
});
