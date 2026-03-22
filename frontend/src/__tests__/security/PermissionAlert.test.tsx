/**
 * Tests para PermissionAlert — Micro-fase 3.21
 */

import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { PermissionAlert } from '../../components/security/PermissionAlert'

const baseProps = {
  nodeName: 'NodoTest',
  nodeIcon: '🤖',
  permission: 'fs.write',
  permissionLabel: 'Escribir archivos',
  taskDescription: 'Guardar configuración',
  onAllow: jest.fn(),
  onAllowAlways: jest.fn(),
  onDeny: jest.fn(),
  onAskMore: jest.fn(),
}

describe('PermissionAlert — zona verde', () => {
  it('no renderiza nada en zona verde', () => {
    const { container } = render(<PermissionAlert {...baseProps} zone="green" />)
    expect(container.firstChild).toBeNull()
  })
})

describe('PermissionAlert — zona amarilla', () => {
  it('muestra overlay y popup en zona amarilla', () => {
    render(<PermissionAlert {...baseProps} zone="yellow" />)
    expect(screen.getByTestId('permission-alert-overlay')).toBeInTheDocument()
    expect(screen.getByTestId('permission-alert-popup')).toBeInTheDocument()
  })

  it('muestra chat inline en zona amarilla', () => {
    render(<PermissionAlert {...baseProps} zone="yellow" />)
    expect(screen.getByTestId('inline-chat')).toBeInTheDocument()
  })

  it('muestra los 4 botones en zona amarilla', () => {
    render(<PermissionAlert {...baseProps} zone="yellow" />)
    expect(screen.getByTestId('btn-allow-once')).toBeInTheDocument()
    expect(screen.getByTestId('btn-allow-always')).toBeInTheDocument()
    expect(screen.getByTestId('btn-deny')).toBeInTheDocument()
    expect(screen.getByTestId('btn-details')).toBeInTheDocument()
  })

  it('llama onAllow al hacer click en Permitir esta vez', () => {
    const onAllow = jest.fn()
    render(<PermissionAlert {...baseProps} zone="yellow" onAllow={onAllow} />)
    fireEvent.click(screen.getByTestId('btn-allow-once'))
    expect(onAllow).toHaveBeenCalledTimes(1)
  })

  it('llama onDeny al hacer click en Denegar', () => {
    const onDeny = jest.fn()
    render(<PermissionAlert {...baseProps} zone="yellow" onDeny={onDeny} />)
    fireEvent.click(screen.getByTestId('btn-deny'))
    expect(onDeny).toHaveBeenCalledTimes(1)
  })

  it('envía mensaje al chat y llama onAskMore', () => {
    const onAskMore = jest.fn()
    render(<PermissionAlert {...baseProps} zone="yellow" onAskMore={onAskMore} />)
    const chatInput = screen.getByTestId('chat-input')
    fireEvent.change(chatInput, { target: { value: '¿Para qué necesitas este permiso?' } })
    fireEvent.keyDown(chatInput, { key: 'Enter' })
    expect(onAskMore).toHaveBeenCalledWith('¿Para qué necesitas este permiso?')
  })
})

describe('PermissionAlert — zona roja', () => {
  it('muestra overlay y popup en zona roja', () => {
    render(<PermissionAlert {...baseProps} zone="red" />)
    expect(screen.getByTestId('permission-alert-overlay')).toBeInTheDocument()
    expect(screen.getByTestId('permission-alert-popup')).toBeInTheDocument()
  })

  it('muestra badge ACCIÓN DE ALTO RIESGO en zona roja', () => {
    render(<PermissionAlert {...baseProps} zone="red" />)
    expect(screen.getByTestId('high-risk-badge')).toBeInTheDocument()
    expect(screen.getByTestId('high-risk-badge')).toHaveTextContent('ACCIÓN DE ALTO RIESGO')
  })

  it('muestra advertencia de irreversibilidad en zona roja', () => {
    render(<PermissionAlert {...baseProps} zone="red" />)
    expect(screen.getByTestId('irreversible-warning')).toBeInTheDocument()
    expect(screen.getByTestId('irreversible-warning')).toHaveTextContent('NO SE PUEDE DESHACER')
  })

  it('botón "Entiendo, proceder" está deshabilitado sin "confirmo"', () => {
    render(<PermissionAlert {...baseProps} zone="red" />)
    const btn = screen.getByTestId('btn-proceed-red')
    expect(btn).toBeDisabled()
  })

  it('"confirmo" habilita el botón de proceder', () => {
    render(<PermissionAlert {...baseProps} zone="red" />)
    fireEvent.change(screen.getByTestId('confirm-input'), { target: { value: 'confirmo' } })
    expect(screen.getByTestId('btn-proceed-red')).not.toBeDisabled()
  })

  it('"CONFIRMO" en mayúsculas también habilita el botón', () => {
    render(<PermissionAlert {...baseProps} zone="red" />)
    fireEvent.change(screen.getByTestId('confirm-input'), { target: { value: 'CONFIRMO' } })
    expect(screen.getByTestId('btn-proceed-red')).not.toBeDisabled()
  })

  it('texto parcial "confir" no habilita el botón', () => {
    render(<PermissionAlert {...baseProps} zone="red" />)
    fireEvent.change(screen.getByTestId('confirm-input'), { target: { value: 'confir' } })
    expect(screen.getByTestId('btn-proceed-red')).toBeDisabled()
  })

  it('muestra info de paquete si se pasa packageInfo', () => {
    render(
      <PermissionAlert
        {...baseProps}
        zone="red"
        packageInfo={{ name: 'rm-rf', origin: 'unknown', size: '4KB' }}
      />
    )
    expect(screen.getByTestId('package-info')).toBeInTheDocument()
  })
})
