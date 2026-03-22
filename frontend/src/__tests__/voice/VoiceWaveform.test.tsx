/**
 * Tests para VoiceWaveform — Micro-fase 5.27
 */

import React from 'react'
import { render, screen } from '@testing-library/react'
import { VoiceWaveform } from '../../components/voice/VoiceWaveform'
import { useVoiceStore } from '../../stores/voiceStore'

// Mock Web Audio API
const mockAnalyser = {
  fftSize: 64,
  frequencyBinCount: 32,
  getByteFrequencyData: jest.fn(),
  connect: jest.fn(),
}
const mockSource = { connect: jest.fn() }
const mockAudioContext = {
  createAnalyser: jest.fn(() => mockAnalyser),
  createMediaStreamSource: jest.fn(() => mockSource),
  close: jest.fn(),
}
global.AudioContext = jest.fn(() => mockAudioContext) as any

// Mock getUserMedia
global.navigator.mediaDevices = {
  getUserMedia: jest.fn().mockRejectedValue(new Error('no mic in tests')),
} as any

beforeEach(() => {
  jest.clearAllMocks()
  useVoiceStore.setState({
    micState: 'idle',
    isEnabled: true,
    transcript: '',
  })
})

describe('VoiceWaveform', () => {
  it('no renderiza nada en estado idle', () => {
    const { container } = render(<VoiceWaveform />)
    expect(screen.queryByTestId('voice-waveform')).not.toBeInTheDocument()
  })

  it('no renderiza nada en estado listening', () => {
    useVoiceStore.setState({ micState: 'listening' })
    render(<VoiceWaveform />)
    expect(screen.queryByTestId('voice-waveform')).not.toBeInTheDocument()
  })

  it('renderiza en estado recording', () => {
    useVoiceStore.setState({ micState: 'recording' })
    render(<VoiceWaveform />)
    expect(screen.getByTestId('voice-waveform')).toBeInTheDocument()
  })

  it('renderiza en estado processing', () => {
    useVoiceStore.setState({ micState: 'processing' })
    render(<VoiceWaveform />)
    expect(screen.getByTestId('voice-waveform')).toBeInTheDocument()
  })

  it('muestra "Te escucho..." en recording', () => {
    useVoiceStore.setState({ micState: 'recording' })
    render(<VoiceWaveform />)
    expect(screen.getByTestId('waveform-status')).toHaveTextContent('Te escucho')
  })

  it('muestra "Procesando..." en processing', () => {
    useVoiceStore.setState({ micState: 'processing' })
    render(<VoiceWaveform />)
    expect(screen.getByTestId('waveform-status')).toHaveTextContent('Procesando')
  })

  it('muestra canvas en recording', () => {
    useVoiceStore.setState({ micState: 'recording' })
    render(<VoiceWaveform />)
    expect(screen.getByTestId('waveform-canvas')).toBeInTheDocument()
  })

  it('muestra transcripción si hay texto', () => {
    useVoiceStore.setState({ micState: 'recording', transcript: 'genera una imagen' })
    render(<VoiceWaveform />)
    expect(screen.getByTestId('waveform-transcript')).toHaveTextContent('genera una imagen')
  })

  it('no muestra transcripción si no hay texto', () => {
    useVoiceStore.setState({ micState: 'recording', transcript: '' })
    render(<VoiceWaveform />)
    expect(screen.queryByTestId('waveform-transcript')).not.toBeInTheDocument()
  })

  it('desaparece al volver a idle', () => {
    useVoiceStore.setState({ micState: 'recording' })
    const { rerender } = render(<VoiceWaveform />)
    expect(screen.getByTestId('voice-waveform')).toBeInTheDocument()
    useVoiceStore.setState({ micState: 'idle' })
    rerender(<VoiceWaveform />)
    expect(screen.queryByTestId('voice-waveform')).not.toBeInTheDocument()
  })
})
