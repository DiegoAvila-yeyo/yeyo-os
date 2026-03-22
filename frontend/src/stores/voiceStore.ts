/**
 * YeyoOS — voiceStore
 * Micro-fase 5.27 — Capa 5: Órganos
 *
 * Store Zustand para el estado del sistema de voz.
 */

import { create } from 'zustand'

export type MicState =
  | 'idle'
  | 'listening'
  | 'recording'
  | 'processing'
  | 'speaking'
  | 'disabled'

interface VoiceState {
  micState: MicState
  isEnabled: boolean
  transcript: string
}

interface VoiceActions {
  setMicState: (state: MicState) => void
  toggleMic: () => void
  setTranscript: (text: string) => void
}

export const useVoiceStore = create<VoiceState & VoiceActions>()((set, get) => ({
  micState: 'idle',
  isEnabled: true,
  transcript: '',

  setMicState: (state) => {
    set({
      micState: state,
      isEnabled: state !== 'disabled',
      // Limpiar transcripción cuando termina de procesar
      transcript: state === 'idle' || state === 'listening' ? '' : get().transcript,
    })
  },

  toggleMic: () => {
    const { micState } = get()
    if (micState === 'disabled') {
      set({ micState: 'idle', isEnabled: true })
      // Notificar al backend via REST
      fetch('/api/voice/toggle', { method: 'POST' }).catch(() => {})
    } else {
      set({ micState: 'disabled', isEnabled: false })
      fetch('/api/voice/toggle', { method: 'POST' }).catch(() => {})
    }
  },

  setTranscript: (text) => set({ transcript: text }),
}))
