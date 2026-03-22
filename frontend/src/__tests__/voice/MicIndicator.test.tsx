/**
 * Tests para MicIndicator — Micro-fase 5.27
 */

import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { MicIndicator } from '../../components/voice/MicIndicator'
import { useVoiceStore } from '../../stores/voiceStore'

// Mock WebSocket
const mockWs = {
  onmessage: null as any,
  onclose: null as any,
  close: jest.fn(),
  readyState: WebSocket.OPEN,
}
global.WebSocket = jest.fn(() => mockWs) as any

// Mock fetch para toggle
global.fetch = jest.fn().mockResolvedValue({ ok: true })

beforeEach(() => {
  jest.clearAllMocks()
  useVoiceStore.setState({
    micState: 'idle',
    isEnabled: true,
    transcript: '',
  })
})

describe('MicIndicator', () => {
  it('renderiza el indicador de micrófono', () => {
    render(<MicIndicator />)
    expect(screen.getByTestId('mic-indicator')).toBeInTheDocument()
  })

  it('tiene data-state="idle" por defecto', () => {
    render(<MicIndicator />)
    expect(screen.getByTestId('mic-indicator')).toHaveAttribute('data-state', 'idle')
  })

  it('cambia data-state cuando el store cambia', () => {
    render(<MicIndicator />)
    useVoiceStore.setState({ micState: 'listening' })
    // Forzar re-render verificando que el componente reacciona al store
    const { rerender } = render(<MicIndicator />)
    rerender(<MicIndicator />)
    expect(screen.getAllByTestId('mic-indicator')[0]).toHaveAttribute('data-state', 'listening')
  })

  it('cambia color al estado recording', () => {
    useVoiceStore.setState({ micState: 'recording' })
    render(<MicIndicator />)
    const indicator = screen.getByTestId('mic-indicator')
    expect(indicator).toHaveAttribute('data-state', 'recording')
  })

  it('cambia color al estado disabled', () => {
    useVoiceStore.setState({ micState: 'disabled' })
    render(<MicIndicator />)
    expect(screen.getByTestId('mic-indicator')).toHaveAttribute('data-state', 'disabled')
  })

  it('click llama a toggleMic y hace fetch a /api/voice/toggle', () => {
    render(<MicIndicator />)
    fireEvent.click(screen.getByTestId('mic-indicator'))
    expect(global.fetch).toHaveBeenCalledWith('/api/voice/toggle', { method: 'POST' })
  })

  it('actualiza estado desde mensaje WebSocket', () => {
    render(<MicIndicator />)
    // Simular mensaje WS
    if (mockWs.onmessage) {
      mockWs.onmessage({ data: JSON.stringify({ type: 'mic_state', state: 'speaking' }) })
    }
    expect(useVoiceStore.getState().micState).toBe('speaking')
  })
})
