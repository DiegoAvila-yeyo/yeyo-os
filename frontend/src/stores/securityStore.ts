/**
 * YeyoOS — securityStore
 * Micro-fase 3.21 — Capa 3: Cuerpo
 *
 * Store Zustand para el sistema de seguridad visual.
 * Gestiona permisos por nodo, historial de accesos y Kill Switch.
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface PermissionRecord {
  permission: string
  permissionLabel: string
  zone: 'green' | 'yellow' | 'red'
  grantedAt?: number
  remember: boolean
}

export interface AccessLogEntry {
  nodeId: string
  permission: string
  permissionLabel: string
  zone: 'green' | 'yellow' | 'red'
  result: 'allowed' | 'denied'
  timestamp: number
  taskDescription?: string
}

interface SecurityState {
  // Map serializado como array de pares para persistencia
  permissionsArray: [string, PermissionRecord[]][]
  permissions: Map<string, PermissionRecord[]>
  history: AccessLogEntry[]
  killSwitchActive: boolean
  cancelledTasks: number
  suspendedProcesses: number
}

interface SecurityActions {
  requestPermission: (nodeId: string, perm: PermissionRecord) => void
  grantPermission: (nodeId: string, permission: string, remember: boolean) => void
  denyPermission: (nodeId: string, permission: string) => void
  logAccess: (entry: Omit<AccessLogEntry, 'timestamp'>) => void
  toggleKillSwitch: () => void
  setKillSwitchCounters: (tasks: number, processes: number) => void
}

export const useSecurityStore = create<SecurityState & SecurityActions>()(
  persist(
    (set, get) => ({
      permissionsArray: [],
      permissions: new Map(),
      history: [],
      killSwitchActive: false,
      cancelledTasks: 0,
      suspendedProcesses: 0,

      requestPermission: (nodeId, perm) => {
        set((state) => {
          const next = new Map(state.permissions)
          const existing = next.get(nodeId) ?? []
          if (!existing.find((p) => p.permission === perm.permission)) {
            next.set(nodeId, [...existing, perm])
          }
          return { permissions: next, permissionsArray: [...next.entries()] }
        })
      },

      grantPermission: (nodeId, permission, remember) => {
        set((state) => {
          const next = new Map(state.permissions)
          const perms = next.get(nodeId) ?? []
          next.set(
            nodeId,
            perms.map((p) =>
              p.permission === permission
                ? { ...p, remember, grantedAt: Date.now() }
                : p
            )
          )
          return { permissions: next, permissionsArray: [...next.entries()] }
        })
      },

      denyPermission: (nodeId, permission) => {
        set((state) => {
          const next = new Map(state.permissions)
          const perms = next.get(nodeId) ?? []
          next.set(
            nodeId,
            perms.filter((p) => p.permission !== permission)
          )
          return { permissions: next, permissionsArray: [...next.entries()] }
        })
      },

      logAccess: (entry) => {
        set((state) => ({
          history: [
            ...state.history.slice(-499), // Mantener máx 500 entradas
            { ...entry, timestamp: Date.now() },
          ],
        }))
      },

      toggleKillSwitch: () => {
        set((state) => ({
          killSwitchActive: !state.killSwitchActive,
          // Resetear contadores al reanudar
          cancelledTasks: state.killSwitchActive ? 0 : state.cancelledTasks,
          suspendedProcesses: state.killSwitchActive ? 0 : state.suspendedProcesses,
        }))
      },

      setKillSwitchCounters: (tasks, processes) => {
        set({ cancelledTasks: tasks, suspendedProcesses: processes })
      },
    }),
    {
      name: 'yeyo-security',
      // Map no es serializable por JSON — persistimos el array y reconstruimos
      onRehydrateStorage: () => (state) => {
        if (state) {
          state.permissions = new Map(state.permissionsArray)
        }
      },
    }
  )
)
