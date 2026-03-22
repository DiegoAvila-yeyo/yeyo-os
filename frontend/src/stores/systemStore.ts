/**
 * YeyoOS — System Store
 * Micro-fase 3.18 — Capa 3: Cuerpo
 *
 * Estado global del sistema: kill switch, onboarding completado, etc.
 */

import { create } from 'zustand'

export interface SystemStoreState {
  killSwitchRegistered: boolean
  onboardingComplete: boolean
  userName: string | null
  setKillSwitchRegistered: (registered: boolean) => void
  setOnboardingComplete: (complete: boolean) => void
  setUserName: (name: string | null) => void
}

export const useSystemStore = create<SystemStoreState>((set) => ({
  killSwitchRegistered: false,
  onboardingComplete: false,
  userName: null,
  setKillSwitchRegistered: (registered) => set({ killSwitchRegistered: registered }),
  setOnboardingComplete: (complete) => set({ onboardingComplete: complete }),
  setUserName: (name) => set({ userName: name }),
}))
