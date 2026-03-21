/**
 * YeyoOS — System Store (Estado del Sistema)
 * Micro-fase 3.11 — Capa 3: Cuerpo
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

export type ConnectionStatus = 'connected' | 'connecting' | 'disconnected' | 'error';

export interface GPUStatus {
  available: boolean;
  vramUsedMB: number;
  vramTotalMB: number;
  temperature: number | null;
}

export interface ServiceHealth {
  ollama: boolean;
  postgres: boolean;
  redis: boolean;
  api: boolean;
}

export interface SystemState {
  connectionStatus: ConnectionStatus;
  gpuStatus: GPUStatus;
  serviceHealth: ServiceHealth;
  killSwitchActive: boolean;
  lastHealthCheck: number | null;

  setConnectionStatus: (status: ConnectionStatus) => void;
  updateGPUStatus: (status: Partial<GPUStatus>) => void;
  updateServiceHealth: (health: Partial<ServiceHealth>) => void;
  setKillSwitchActive: (active: boolean) => void;
  setLastHealthCheck: (timestamp: number) => void;
}

export const DEFAULT_GPU: GPUStatus = {
  available: false,
  vramUsedMB: 0,
  vramTotalMB: 3072,
  temperature: null,
};

export const DEFAULT_HEALTH: ServiceHealth = {
  ollama: false,
  postgres: false,
  redis: false,
  api: false,
};

export const useSystemStore = create<SystemState>()(
  devtools(
    (set) => ({
      connectionStatus: 'disconnected',
      gpuStatus: { ...DEFAULT_GPU },
      serviceHealth: { ...DEFAULT_HEALTH },
      killSwitchActive: false,
      lastHealthCheck: null,

      setConnectionStatus: (status) => set({ connectionStatus: status }),

      updateGPUStatus: (status) =>
        set((s) => ({
          gpuStatus: { ...s.gpuStatus, ...status },
        })),

      updateServiceHealth: (health) =>
        set((s) => ({
          serviceHealth: { ...s.serviceHealth, ...health },
        })),

      setKillSwitchActive: (active) => set({ killSwitchActive: active }),
      setLastHealthCheck: (timestamp) => set({ lastHealthCheck: timestamp }),
    }),
    { name: 'YeyoOS System Store' }
  )
);
