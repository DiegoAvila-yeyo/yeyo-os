/**
 * Tests para KillSwitchOverlay — Micro-fase 3.21
 */

import React from 'react'
import { render, screen, fireEvent, act } from '@testing-library/react'
import { KillSwitchOverlay } from '../../components/security/KillSwitchOverlay'
import { useSecurityStore } from '../../stores/securityStore'

beforeEach(() => {
  useSecurityStore.setState({
    killSwitchActive: false,
    cancelledTasks: 0,
    suspendedProcesses: 0,
    permissions: new Map(),
    permissionsArray: [],
    history: [],
  })
})

describe('KillSwitchOverlay', () => {
  it('no renderiza nada cuando killSwitchActive=false', () => {
    const { container } = render(<KillSwitchOverlay />)
    expect(screen.queryByTestId('kill-switch-overlay')).not.toBeInTheDocument()
  })

  it('renderiza el overlay cuando killSwitchActive=true', () => {
    useSecurityStore.setState({ killSwitchActive: true })
    render(<KillSwitchOverlay />)
    expect(screen.getByTestId('kill-switch-overlay')).toBeInTheDocument()
  })

  it('muestra el título SISTEMA EN PAUSA', () => {
    useSecurityStore.setState({ killSwitchActive: true })
    render(<KillSwitchOverlay />)
    expect(screen.getByTestId('kill-switch-title')).toHaveTextContent('SISTEMA EN PAUSA')
  })

  it('muestra los contadores', () => {
    useSecurityStore.setState({ killSwitchActive: true, cancelledTasks: 3, suspendedProcesses: 2 })
    render(<KillSwitchOverlay />)
    expect(screen.getByTestId('kill-switch-counters')).toBeInTheDocument()
    expect(screen.getByTestId('kill-switch-counters')).toHaveTextContent('3')
    expect(screen.getByTestId('kill-switch-counters')).toHaveTextContent('2')
  })

  it('muestra borde rojo cuando activo', () => {
    useSecurityStore.setState({ killSwitchActive: true })
    render(<KillSwitchOverlay />)
    expect(screen.getByTestId('kill-switch-border')).toBeInTheDocument()
  })

  it('botón Reanudar desactiva el overlay', () => {
    useSecurityStore.setState({ killSwitchActive: true })
    render(<KillSwitchOverlay />)
    fireEvent.click(screen.getByTestId('resume-btn'))
    expect(useSecurityStore.getState().killSwitchActive).toBe(false)
  })

  it('Ctrl+Alt+K activa el Kill Switch', () => {
    render(<KillSwitchOverlay />)
    act(() => {
      fireEvent.keyDown(window, { key: 'k', ctrlKey: true, altKey: true })
    })
    expect(useSecurityStore.getState().killSwitchActive).toBe(true)
  })

  it('Ctrl+Alt+K con overlay activo lo desactiva (toggle)', () => {
    useSecurityStore.setState({ killSwitchActive: true })
    render(<KillSwitchOverlay />)
    act(() => {
      fireEvent.keyDown(window, { key: 'k', ctrlKey: true, altKey: true })
    })
    expect(useSecurityStore.getState().killSwitchActive).toBe(false)
  })
})
