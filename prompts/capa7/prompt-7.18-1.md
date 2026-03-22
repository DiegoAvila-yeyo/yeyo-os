## ═══════════════════════════════════════
## MICRO-FASE 7.18 — YeyoNet UI (Frontend)
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 7.18-1 [VSCODE] — Frontend React/TypeScript completo para YeyoNet: panel de satélites, modal de invitación, pantalla de conexión y estado de red

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 7.18 de Capa 7 (Evolución): implementar la UI completa de YeyoNet — el panel de satélites del Central, el modal de generación de invitaciones con QR, la pantalla de conexión para satélites, y el indicador de estado de red en el topbar.

CONTEXTO:
- Micro-fase 7.17 completada: backend YeyoNet funcionando con endpoints POST /api/yeyonet/invite, GET/DELETE /api/yeyonet/satellites, POST /api/yeyonet/connect, GET /api/yeyonet/status
- Stack: Next.js + React + TypeScript, Zustand para estado global, Tailwind CSS para estilos
- Hub principal (Capa 3) ya tiene topbar — NetworkStatus se agrega como widget en él
- Dependencias a instalar: qrcode.react (QR generator), html5-qrcode (QR scanner), zustand (ya existe)
- Diseño: fondo oscuro (#050A14), acentos en #4FC3F7 (azul YeyoOS), estados: 🟢 online, 🟡 idle, ⭘ offline
- API URL base: /api/yeyonet (proxy a FastAPI en Next.js config)
- Node type (central/satellite) viene de variable de entorno NEXT_PUBLIC_NODE_TYPE

Abre el directorio ~/yeyo-os en VS Code.

INSTALAR (ejecutar en ~/yeyo-os/frontend/):

   npm install qrcode.react html5-qrcode
   npm install --save-dev @types/qrcode

CREAR:

1. Crear archivo frontend/src/stores/yeyonetStore.ts:

   Ruta: ~/yeyo-os/frontend/src/stores/yeyonetStore.ts
   Contenido:

   /**
    * YeyoNet — Zustand Store
    * Micro-fase 7.18 — Capa 7: Evolución
    *
    * Estado global para la red YeyoNet.
    * Maneja satélites, tipo de nodo, estado de conexión y cola pendiente.
    */

   import { create } from 'zustand'
   import { devtools } from 'zustand/middleware'

   export type SatelliteStatus = 'online' | 'idle' | 'offline'

   export interface Satellite {
     satellite_id: string
     name: string
     permissions: string[]
     visibility_level: number
     status: SatelliteStatus
     last_seen: string | null
     connected_at: string | null
     node_mode: number
   }

   export type NodeType = 'central' | 'satellite'

   interface YeyoNetState {
     satellites: Satellite[]
     nodeType: NodeType
     isConnected: boolean
     pendingSyncCount: number
     isLoading: boolean
     error: string | null

     // Actions
     setSatellites: (satellites: Satellite[]) => void
     addSatellite: (satellite: Satellite) => void
     removeSatellite: (satellite_id: string) => void
     setNodeType: (type: NodeType) => void
     setIsConnected: (connected: boolean) => void
     setPendingSyncCount: (count: number) => void
     setLoading: (loading: boolean) => void
     setError: (error: string | null) => void
     fetchSatellites: () => Promise<void>
     fetchStatus: () => Promise<void>
     disconnectSatellite: (satellite_id: string) => Promise<void>
   }

   export const useYeyoNetStore = create<YeyoNetState>()(
     devtools(
       (set, get) => ({
         satellites: [],
         nodeType: (process.env.NEXT_PUBLIC_NODE_TYPE as NodeType) ?? 'satellite',
         isConnected: false,
         pendingSyncCount: 0,
         isLoading: false,
         error: null,

         setSatellites: (satellites) => set({ satellites }),
         addSatellite: (satellite) =>
           set((state) => ({
             satellites: [...state.satellites.filter((s) => s.satellite_id !== satellite.satellite_id), satellite],
           })),
         removeSatellite: (satellite_id) =>
           set((state) => ({
             satellites: state.satellites.filter((s) => s.satellite_id !== satellite_id),
           })),
         setNodeType: (nodeType) => set({ nodeType }),
         setIsConnected: (isConnected) => set({ isConnected }),
         setPendingSyncCount: (pendingSyncCount) => set({ pendingSyncCount }),
         setLoading: (isLoading) => set({ isLoading }),
         setError: (error) => set({ error }),

         fetchSatellites: async () => {
           set({ isLoading: true, error: null })
           try {
             const res = await fetch('/api/yeyonet/satellites')
             if (!res.ok) throw new Error(`HTTP ${res.status}`)
             const data: Satellite[] = await res.json()
             set({ satellites: data, isLoading: false })
           } catch (err) {
             set({ error: (err as Error).message, isLoading: false })
           }
         },

         fetchStatus: async () => {
           try {
             const res = await fetch('/api/yeyonet/status')
             if (!res.ok) return
             const data = await res.json()
             set({
               nodeType: data.node_type as NodeType,
               isConnected: data.is_connected,
               pendingSyncCount: data.pending_sync_count,
             })
           } catch {
             // Status fetch falla silenciosamente
           }
         },

         disconnectSatellite: async (satellite_id) => {
           const res = await fetch(`/api/yeyonet/satellites/${satellite_id}`, {
             method: 'DELETE',
           })
           if (res.ok || res.status === 204) {
             get().removeSatellite(satellite_id)
           } else {
             throw new Error(`Error al desconectar: HTTP ${res.status}`)
           }
         },
       }),
       { name: 'YeyoNetStore' }
     )
   )

2. Crear archivo frontend/src/components/yeyonet/SatellitePanel.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/yeyonet/SatellitePanel.tsx
   Contenido:

   /**
    * YeyoNet — Panel de Satélites (Central)
    * Micro-fase 7.18 — Capa 7: Evolución
    *
    * Muestra todos los satélites conectados con:
    * - Estado: 🟢 online, 🟡 idle, ⭘ offline
    * - Última conexión
    * - Permisos activos
    * - Botones editar/desconectar
    * - Botón "Invitar nuevo satélite"
    */

   import React, { useEffect, useState } from 'react'
   import { useYeyoNetStore, Satellite, SatelliteStatus } from '../../stores/yeyonetStore'
   import { InviteModal } from './InviteModal'

   const STATUS_ICONS: Record<SatelliteStatus, string> = {
     online: '🟢',
     idle: '🟡',
     offline: '⭘',
   }

   const STATUS_LABELS: Record<SatelliteStatus, string> = {
     online: 'En línea',
     idle: 'Inactivo',
     offline: 'Desconectado',
   }

   function formatLastSeen(lastSeen: string | null): string {
     if (!lastSeen) return 'Nunca'
     const diff = Date.now() - new Date(lastSeen).getTime()
     const minutes = Math.floor(diff / 60_000)
     if (minutes < 1) return 'Justo ahora'
     if (minutes < 60) return `Hace ${minutes} min`
     const hours = Math.floor(minutes / 60)
     if (hours < 24) return `Hace ${hours}h`
     const days = Math.floor(hours / 24)
     return `Hace ${days}d`
   }

   function SatelliteRow({
     satellite,
     onDisconnect,
   }: {
     satellite: Satellite
     onDisconnect: (id: string) => void
   }) {
     const [confirming, setConfirming] = useState(false)

     return (
       <div
         data-testid={`satellite-row-${satellite.satellite_id}`}
         style={{
           display: 'flex',
           alignItems: 'center',
           justifyContent: 'space-between',
           padding: '12px 16px',
           borderBottom: '1px solid rgba(79, 195, 247, 0.1)',
           gap: 12,
         }}
       >
         {/* Estado + nombre */}
         <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 200 }}>
           <span
             data-testid={`satellite-status-${satellite.satellite_id}`}
             title={STATUS_LABELS[satellite.status]}
             style={{ fontSize: 16 }}
           >
             {STATUS_ICONS[satellite.status]}
           </span>
           <div>
             <div style={{ color: '#E0F7FA', fontWeight: 500, fontSize: 14 }}>
               {satellite.name}
             </div>
             <div style={{ color: '#78909C', fontSize: 12 }}>
               Modo {satellite.node_mode} · {formatLastSeen(satellite.last_seen)}
             </div>
           </div>
         </div>

         {/* Permisos */}
         <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', flex: 1 }}>
           {satellite.permissions.map((perm) => (
             <span
               key={perm}
               style={{
                 fontSize: 11,
                 padding: '2px 8px',
                 borderRadius: 10,
                 backgroundColor: 'rgba(79, 195, 247, 0.15)',
                 color: '#4FC3F7',
                 border: '1px solid rgba(79, 195, 247, 0.3)',
               }}
             >
               {perm}
             </span>
           ))}
         </div>

         {/* Acciones */}
         <div style={{ display: 'flex', gap: 8 }}>
           {confirming ? (
             <>
               <button
                 data-testid={`confirm-disconnect-${satellite.satellite_id}`}
                 onClick={() => onDisconnect(satellite.satellite_id)}
                 style={dangerBtnStyle}
               >
                 Confirmar
               </button>
               <button
                 onClick={() => setConfirming(false)}
                 style={secondaryBtnStyle}
               >
                 Cancelar
               </button>
             </>
           ) : (
             <button
               data-testid={`disconnect-${satellite.satellite_id}`}
               onClick={() => setConfirming(true)}
               style={secondaryBtnStyle}
             >
               Desconectar
             </button>
           )}
         </div>
       </div>
     )
   }

   export function SatellitePanel() {
     const { satellites, isLoading, error, fetchSatellites, disconnectSatellite } = useYeyoNetStore()
     const [showInvite, setShowInvite] = useState(false)

     useEffect(() => {
       fetchSatellites()
       const interval = setInterval(fetchSatellites, 30_000)
       return () => clearInterval(interval)
     }, [fetchSatellites])

     const handleDisconnect = async (id: string) => {
       try {
         await disconnectSatellite(id)
       } catch (err) {
         console.error('Error al desconectar satélite:', err)
       }
     }

     const onlineCount = satellites.filter((s) => s.status === 'online').length

     return (
       <div
         data-testid="satellite-panel"
         style={{
           backgroundColor: '#0A1628',
           border: '1px solid rgba(79, 195, 247, 0.2)',
           borderRadius: 12,
           overflow: 'hidden',
           fontFamily: 'Inter, system-ui, sans-serif',
           minWidth: 600,
         }}
       >
         {/* Header */}
         <div
           style={{
             display: 'flex',
             alignItems: 'center',
             justifyContent: 'space-between',
             padding: '16px 20px',
             borderBottom: '1px solid rgba(79, 195, 247, 0.15)',
             backgroundColor: 'rgba(79, 195, 247, 0.05)',
           }}
         >
           <div>
             <h2 style={{ margin: 0, color: '#E0F7FA', fontSize: 16, fontWeight: 600 }}>
               YeyoNet — Satélites
             </h2>
             <div style={{ color: '#78909C', fontSize: 12, marginTop: 2 }}>
               {satellites.length} registrados · {onlineCount} en línea
             </div>
           </div>
           <button
             data-testid="invite-button"
             onClick={() => setShowInvite(true)}
             style={primaryBtnStyle}
           >
             + Invitar satélite
           </button>
         </div>

         {/* Contenido */}
         {isLoading && satellites.length === 0 ? (
           <div
             data-testid="loading-state"
             style={{ padding: 40, textAlign: 'center', color: '#78909C' }}
           >
             Cargando satélites...
           </div>
         ) : error ? (
           <div
             data-testid="error-state"
             style={{ padding: 40, textAlign: 'center', color: '#EF9A9A' }}
           >
             Error: {error}
           </div>
         ) : satellites.length === 0 ? (
           <div
             data-testid="empty-state"
             style={{ padding: 40, textAlign: 'center', color: '#78909C' }}
           >
             No hay satélites conectados. Invita uno para comenzar.
           </div>
         ) : (
           <div>
             {satellites.map((sat) => (
               <SatelliteRow
                 key={sat.satellite_id}
                 satellite={sat}
                 onDisconnect={handleDisconnect}
               />
             ))}
           </div>
         )}

         {showInvite && <InviteModal onClose={() => setShowInvite(false)} />}
       </div>
     )
   }

   // ── Estilos ──────────────────────────────────────────────────────────────────

   const primaryBtnStyle: React.CSSProperties = {
     backgroundColor: '#4FC3F7',
     color: '#050A14',
     border: 'none',
     borderRadius: 8,
     padding: '8px 16px',
     fontSize: 13,
     fontWeight: 600,
     cursor: 'pointer',
   }

   const secondaryBtnStyle: React.CSSProperties = {
     backgroundColor: 'transparent',
     color: '#78909C',
     border: '1px solid rgba(120, 144, 156, 0.4)',
     borderRadius: 8,
     padding: '6px 12px',
     fontSize: 12,
     cursor: 'pointer',
   }

   const dangerBtnStyle: React.CSSProperties = {
     backgroundColor: 'transparent',
     color: '#EF9A9A',
     border: '1px solid rgba(239, 154, 154, 0.5)',
     borderRadius: 8,
     padding: '6px 12px',
     fontSize: 12,
     cursor: 'pointer',
   }

3. Crear archivo frontend/src/components/yeyonet/InviteModal.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/yeyonet/InviteModal.tsx
   Contenido:

   /**
    * YeyoNet — Modal de Generación de Invitación
    * Micro-fase 7.18 — Capa 7: Evolución
    *
    * Permite al Central crear una invitación con:
    * - Nombre del satélite
    * - Checkboxes de permisos (chat, grafos, memoria, control)
    * - Selector de expiración (1, 7, 30 días)
    * Muestra código YEYO-XXXX y QR (qrcode.react).
    * Botones copiar código y cerrar.
    */

   import React, { useState } from 'react'
   import QRCode from 'qrcode.react'

   const PERMISSIONS = [
     { id: 'chat', label: 'Chat', description: 'Acceso a conversaciones con YEYO' },
     { id: 'grafos', label: 'Grafos', description: 'Ver y recibir grafos de IA' },
     { id: 'memoria', label: 'Memoria', description: 'Acceso a Flash Memory (nivel 3)' },
     { id: 'control', label: 'Control total', description: 'Ejecutar tareas remotamente (nivel 4)' },
   ]

   const EXPIRY_OPTIONS = [
     { value: 1, label: '1 día' },
     { value: 7, label: '7 días (recomendado)' },
     { value: 30, label: '30 días' },
   ]

   interface GeneratedInvite {
     code: string
     expires_at: string
   }

   interface InviteModalProps {
     onClose: () => void
   }

   export function InviteModal({ onClose }: InviteModalProps) {
     const [satelliteName, setSatelliteName] = useState('')
     const [selectedPerms, setSelectedPerms] = useState<string[]>(['chat'])
     const [expiryDays, setExpiryDays] = useState(7)
     const [generating, setGenerating] = useState(false)
     const [generated, setGenerated] = useState<GeneratedInvite | null>(null)
     const [copied, setCopied] = useState(false)
     const [error, setError] = useState<string | null>(null)

     const togglePerm = (perm: string) => {
       setSelectedPerms((prev) =>
         prev.includes(perm) ? prev.filter((p) => p !== perm) : [...prev, perm]
       )
     }

     const handleGenerate = async () => {
       if (!satelliteName.trim()) {
         setError('El nombre del satélite es requerido')
         return
       }
       setGenerating(true)
       setError(null)
       try {
         const res = await fetch('/api/yeyonet/invite', {
           method: 'POST',
           headers: { 'Content-Type': 'application/json' },
           body: JSON.stringify({
             satellite_name: satelliteName.trim(),
             permissions: selectedPerms,
             expires_in_days: expiryDays,
           }),
         })
         if (!res.ok) {
           const data = await res.json().catch(() => ({}))
           throw new Error(data.detail || `Error HTTP ${res.status}`)
         }
         const data = await res.json()
         setGenerated({ code: data.code, expires_at: data.expires_at })
       } catch (err) {
         setError((err as Error).message)
       } finally {
         setGenerating(false)
       }
     }

     const handleCopy = async () => {
       if (!generated) return
       try {
         await navigator.clipboard.writeText(generated.code)
         setCopied(true)
         setTimeout(() => setCopied(false), 2000)
       } catch {
         // Clipboard no disponible — fallback manual
       }
     }

     return (
       <div
         data-testid="invite-modal-overlay"
         style={{
           position: 'fixed',
           inset: 0,
           backgroundColor: 'rgba(0, 0, 0, 0.7)',
           display: 'flex',
           alignItems: 'center',
           justifyContent: 'center',
           zIndex: 2000,
         }}
         onClick={(e) => {
           if (e.target === e.currentTarget) onClose()
         }}
       >
         <div
           data-testid="invite-modal"
           style={{
             backgroundColor: '#0D1B2A',
             border: '1px solid rgba(79, 195, 247, 0.3)',
             borderRadius: 16,
             padding: 32,
             width: 480,
             maxWidth: '90vw',
             fontFamily: 'Inter, system-ui, sans-serif',
           }}
         >
           <h2 style={{ margin: '0 0 24px', color: '#E0F7FA', fontSize: 18 }}>
             Invitar nuevo satélite
           </h2>

           {!generated ? (
             <>
               {/* Nombre del satélite */}
               <div style={{ marginBottom: 20 }}>
                 <label style={labelStyle}>Nombre del satélite</label>
                 <input
                   data-testid="satellite-name-input"
                   type="text"
                   value={satelliteName}
                   onChange={(e) => setSatelliteName(e.target.value)}
                   placeholder="Ej: Laptop Viaje, PC Estudio"
                   style={inputStyle}
                 />
               </div>

               {/* Permisos */}
               <div style={{ marginBottom: 20 }}>
                 <label style={labelStyle}>Permisos</label>
                 <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                   {PERMISSIONS.map((perm) => (
                     <label
                       key={perm.id}
                       data-testid={`perm-${perm.id}`}
                       style={{
                         display: 'flex',
                         alignItems: 'center',
                         gap: 10,
                         cursor: 'pointer',
                         padding: '8px 12px',
                         borderRadius: 8,
                         backgroundColor: selectedPerms.includes(perm.id)
                           ? 'rgba(79, 195, 247, 0.1)'
                           : 'transparent',
                         border: `1px solid ${
                           selectedPerms.includes(perm.id)
                             ? 'rgba(79, 195, 247, 0.4)'
                             : 'rgba(79, 195, 247, 0.1)'
                         }`,
                       }}
                     >
                       <input
                         type="checkbox"
                         checked={selectedPerms.includes(perm.id)}
                         onChange={() => togglePerm(perm.id)}
                         style={{ accentColor: '#4FC3F7' }}
                       />
                       <div>
                         <div style={{ color: '#E0F7FA', fontSize: 13, fontWeight: 500 }}>
                           {perm.label}
                         </div>
                         <div style={{ color: '#78909C', fontSize: 11 }}>
                           {perm.description}
                         </div>
                       </div>
                     </label>
                   ))}
                 </div>
               </div>

               {/* Expiración */}
               <div style={{ marginBottom: 24 }}>
                 <label style={labelStyle}>Expiración</label>
                 <select
                   data-testid="expiry-select"
                   value={expiryDays}
                   onChange={(e) => setExpiryDays(Number(e.target.value))}
                   style={inputStyle}
                 >
                   {EXPIRY_OPTIONS.map((opt) => (
                     <option key={opt.value} value={opt.value}>
                       {opt.label}
                     </option>
                   ))}
                 </select>
               </div>

               {error && (
                 <div
                   data-testid="invite-error"
                   style={{ color: '#EF9A9A', fontSize: 13, marginBottom: 16 }}
                 >
                   {error}
                 </div>
               )}

               <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
                 <button onClick={onClose} style={secondaryBtnStyle}>
                   Cancelar
                 </button>
                 <button
                   data-testid="generate-button"
                   onClick={handleGenerate}
                   disabled={generating}
                   style={{
                     ...primaryBtnStyle,
                     opacity: generating ? 0.6 : 1,
                   }}
                 >
                   {generating ? 'Generando...' : 'Generar invitación'}
                 </button>
               </div>
             </>
           ) : (
             /* Vista del código generado */
             <div style={{ textAlign: 'center' }}>
               <div
                 data-testid="generated-code"
                 style={{
                   fontFamily: 'monospace',
                   fontSize: 22,
                   color: '#4FC3F7',
                   letterSpacing: 2,
                   marginBottom: 24,
                   padding: '16px 20px',
                   backgroundColor: 'rgba(79, 195, 247, 0.08)',
                   borderRadius: 8,
                   border: '1px solid rgba(79, 195, 247, 0.3)',
                 }}
               >
                 {generated.code}
               </div>

               {/* QR Code */}
               <div
                 data-testid="qr-code"
                 style={{
                   display: 'inline-block',
                   padding: 16,
                   backgroundColor: '#FFFFFF',
                   borderRadius: 8,
                   marginBottom: 20,
                 }}
               >
                 <QRCode value={generated.code} size={180} />
               </div>

               <div style={{ color: '#78909C', fontSize: 12, marginBottom: 24 }}>
                 Expira: {new Date(generated.expires_at).toLocaleDateString('es-MX', {
                   day: 'numeric', month: 'long', year: 'numeric',
                 })}
               </div>

               <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
                 <button
                   data-testid="copy-button"
                   onClick={handleCopy}
                   style={secondaryBtnStyle}
                 >
                   {copied ? '✓ Copiado' : 'Copiar código'}
                 </button>
                 <button onClick={onClose} style={primaryBtnStyle}>
                   Cerrar
                 </button>
               </div>
             </div>
           )}
         </div>
       </div>
     )
   }

   // ── Estilos ──────────────────────────────────────────────────────────────────

   const labelStyle: React.CSSProperties = {
     display: 'block',
     color: '#90CAF9',
     fontSize: 12,
     fontWeight: 500,
     marginBottom: 8,
     textTransform: 'uppercase',
     letterSpacing: 0.5,
   }

   const inputStyle: React.CSSProperties = {
     width: '100%',
     padding: '10px 14px',
     backgroundColor: 'rgba(79, 195, 247, 0.05)',
     border: '1px solid rgba(79, 195, 247, 0.2)',
     borderRadius: 8,
     color: '#E0F7FA',
     fontSize: 14,
     outline: 'none',
     boxSizing: 'border-box',
   }

   const primaryBtnStyle: React.CSSProperties = {
     backgroundColor: '#4FC3F7',
     color: '#050A14',
     border: 'none',
     borderRadius: 8,
     padding: '10px 20px',
     fontSize: 14,
     fontWeight: 600,
     cursor: 'pointer',
   }

   const secondaryBtnStyle: React.CSSProperties = {
     backgroundColor: 'transparent',
     color: '#90CAF9',
     border: '1px solid rgba(144, 202, 249, 0.4)',
     borderRadius: 8,
     padding: '10px 20px',
     fontSize: 14,
     cursor: 'pointer',
   }

4. Crear archivo frontend/src/components/yeyonet/ConnectScreen.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/yeyonet/ConnectScreen.tsx
   Contenido:

   /**
    * YeyoNet — Pantalla de Conexión (Satélite)
    * Micro-fase 7.18 — Capa 7: Evolución
    *
    * Pantalla para que el satélite se conecte al Central.
    * - Input del código YEYO-XXXX-XXXX-XXXX
    * - Botón escanear QR (html5-qrcode)
    * - Feedback de conexión en tiempo real
    * - Al conectar exitosamente, llama onConnected(satellite_id)
    */

   import React, { useEffect, useRef, useState } from 'react'

   interface ConnectScreenProps {
     onConnected?: (satelliteId: string) => void
   }

   type ConnectStep = 'idle' | 'scanning' | 'connecting' | 'success' | 'error'

   export function ConnectScreen({ onConnected }: ConnectScreenProps) {
     const [code, setCode] = useState('')
     const [step, setStep] = useState<ConnectStep>('idle')
     const [errorMsg, setErrorMsg] = useState<string | null>(null)
     const [connectedName, setConnectedName] = useState<string | null>(null)
     const [showScanner, setShowScanner] = useState(false)
     const scannerRef = useRef<HTMLDivElement>(null)
     const html5QrRef = useRef<any>(null)

     useEffect(() => {
       return () => {
         if (html5QrRef.current) {
           html5QrRef.current.stop().catch(() => {})
         }
       }
     }, [])

     const startScanner = async () => {
       setShowScanner(true)
       setStep('scanning')
       try {
         const { Html5Qrcode } = await import('html5-qrcode')
         html5QrRef.current = new Html5Qrcode('yeyonet-qr-reader')
         await html5QrRef.current.start(
           { facingMode: 'environment' },
           { fps: 10, qrbox: { width: 250, height: 250 } },
           (decodedText: string) => {
             // QR escaneado
             if (decodedText.startsWith('YEYO-')) {
               setCode(decodedText)
               stopScanner()
               setStep('idle')
             }
           },
           undefined // onScanFailure — ignorar
         )
       } catch (err) {
         setStep('error')
         setErrorMsg('No se pudo iniciar la cámara')
         setShowScanner(false)
       }
     }

     const stopScanner = () => {
       if (html5QrRef.current) {
         html5QrRef.current.stop().catch(() => {})
         html5QrRef.current = null
       }
       setShowScanner(false)
       if (step === 'scanning') setStep('idle')
     }

     const handleConnect = async () => {
       const trimmedCode = code.trim().toUpperCase()
       if (!trimmedCode.startsWith('YEYO-') || trimmedCode.length < 18) {
         setErrorMsg('Formato inválido. Usa: YEYO-XXXX-XXXX-XXXX')
         return
       }
       setStep('connecting')
       setErrorMsg(null)
       try {
         const res = await fetch('/api/yeyonet/connect', {
           method: 'POST',
           headers: { 'Content-Type': 'application/json' },
           body: JSON.stringify({ code: trimmedCode, node_mode: 1 }),
         })
         if (!res.ok) {
           const data = await res.json().catch(() => ({}))
           throw new Error(data.detail || `Error HTTP ${res.status}`)
         }
         const data = await res.json()
         setConnectedName(data.satellite_name)
         setStep('success')
         if (onConnected) onConnected(data.satellite_id)
       } catch (err) {
         setStep('error')
         setErrorMsg((err as Error).message)
       }
     }

     return (
       <div
         data-testid="connect-screen"
         data-step={step}
         style={{
           display: 'flex',
           flexDirection: 'column',
           alignItems: 'center',
           justifyContent: 'center',
           minHeight: '100vh',
           backgroundColor: '#050A14',
           fontFamily: 'Inter, system-ui, sans-serif',
           padding: 32,
         }}
       >
         <div
           style={{
             width: 420,
             maxWidth: '100%',
             backgroundColor: '#0A1628',
             border: '1px solid rgba(79, 195, 247, 0.2)',
             borderRadius: 16,
             padding: 40,
           }}
         >
           {/* Logo */}
           <div style={{ textAlign: 'center', marginBottom: 32 }}>
             <div style={{
               width: 56,
               height: 56,
               borderRadius: '50%',
               backgroundColor: '#4FC3F7',
               display: 'inline-flex',
               alignItems: 'center',
               justifyContent: 'center',
               fontSize: 24,
               marginBottom: 12,
             }}>
               ✦
             </div>
             <h1 style={{ margin: 0, color: '#E0F7FA', fontSize: 22, fontWeight: 600 }}>
               Conectar a YeyoNet
             </h1>
             <p style={{ margin: '8px 0 0', color: '#78909C', fontSize: 14 }}>
               Ingresa el código de invitación del Central
             </p>
           </div>

           {step === 'success' ? (
             <div data-testid="success-state" style={{ textAlign: 'center' }}>
               <div style={{ fontSize: 48, marginBottom: 16 }}>🟢</div>
               <h2 style={{ color: '#E0F7FA', fontSize: 18 }}>
                 ¡Conectado!
               </h2>
               <p style={{ color: '#78909C', fontSize: 14 }}>
                 Este satélite ahora es parte de YeyoNet
                 {connectedName && ` como "${connectedName}"`}.
               </p>
             </div>
           ) : (
             <>
               {/* Input de código */}
               <div style={{ marginBottom: 16 }}>
                 <input
                   data-testid="code-input"
                   type="text"
                   value={code}
                   onChange={(e) => {
                     setCode(e.target.value.toUpperCase())
                     setErrorMsg(null)
                   }}
                   placeholder="YEYO-XXXX-XXXX-XXXX"
                   disabled={step === 'connecting'}
                   style={{
                     width: '100%',
                     padding: '14px 16px',
                     backgroundColor: 'rgba(79, 195, 247, 0.05)',
                     border: `1px solid ${errorMsg ? 'rgba(239, 154, 154, 0.5)' : 'rgba(79, 195, 247, 0.25)'}`,
                     borderRadius: 10,
                     color: '#E0F7FA',
                     fontSize: 16,
                     fontFamily: 'monospace',
                     letterSpacing: 1,
                     outline: 'none',
                     boxSizing: 'border-box',
                   }}
                 />
               </div>

               {errorMsg && (
                 <div
                   data-testid="error-message"
                   style={{ color: '#EF9A9A', fontSize: 13, marginBottom: 16 }}
                 >
                   {errorMsg}
                 </div>
               )}

               {/* Botones */}
               <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                 <button
                   data-testid="connect-button"
                   onClick={handleConnect}
                   disabled={step === 'connecting' || !code.trim()}
                   style={{
                     backgroundColor: '#4FC3F7',
                     color: '#050A14',
                     border: 'none',
                     borderRadius: 10,
                     padding: '14px 20px',
                     fontSize: 15,
                     fontWeight: 700,
                     cursor: step === 'connecting' || !code.trim() ? 'not-allowed' : 'pointer',
                     opacity: step === 'connecting' || !code.trim() ? 0.6 : 1,
                   }}
                 >
                   {step === 'connecting' ? 'Conectando...' : 'Conectar'}
                 </button>

                 {!showScanner && (
                   <button
                     data-testid="scan-qr-button"
                     onClick={startScanner}
                     disabled={step === 'connecting'}
                     style={{
                       backgroundColor: 'transparent',
                       color: '#90CAF9',
                       border: '1px solid rgba(144, 202, 249, 0.3)',
                       borderRadius: 10,
                       padding: '12px 20px',
                       fontSize: 14,
                       cursor: 'pointer',
                     }}
                   >
                     📷 Escanear QR
                   </button>
                 )}

                 {showScanner && (
                   <button
                     onClick={stopScanner}
                     style={{
                       backgroundColor: 'transparent',
                       color: '#EF9A9A',
                       border: '1px solid rgba(239, 154, 154, 0.3)',
                       borderRadius: 10,
                       padding: '10px 20px',
                       fontSize: 13,
                       cursor: 'pointer',
                     }}
                   >
                     Cancelar escáner
                   </button>
                 )}
               </div>

               {/* QR Scanner area */}
               {showScanner && (
                 <div
                   data-testid="qr-scanner"
                   id="yeyonet-qr-reader"
                   ref={scannerRef}
                   style={{
                     marginTop: 20,
                     borderRadius: 8,
                     overflow: 'hidden',
                     border: '1px solid rgba(79, 195, 247, 0.3)',
                   }}
                 />
               )}
             </>
           )}
         </div>
       </div>
     )
   }

5. Crear archivo frontend/src/components/yeyonet/NetworkStatus.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/yeyonet/NetworkStatus.tsx
   Contenido:

   /**
    * YeyoNet — Indicador de Estado de Red (Topbar Widget)
    * Micro-fase 7.18 — Capa 7: Evolución
    *
    * Widget pequeño para el topbar del Hub.
    * Muestra: punto de color + número de satélites activos.
    * Verde si hay satélites online, gris si solo/offline.
    * Al hacer click, abre el SatellitePanel (si es Central).
    */

   import React, { useEffect, useRef, useState } from 'react'
   import { useYeyoNetStore } from '../../stores/yeyonetStore'
   import { SatellitePanel } from './SatellitePanel'

   export function NetworkStatus() {
     const { satellites, nodeType, fetchSatellites, fetchStatus } = useYeyoNetStore()
     const [panelOpen, setPanelOpen] = useState(false)
     const panelRef = useRef<HTMLDivElement>(null)

     const onlineCount = satellites.filter((s) => s.status === 'online').length
     const hasOnline = onlineCount > 0
     const isCentral = nodeType === 'central'

     useEffect(() => {
       fetchStatus()
       if (isCentral) {
         fetchSatellites()
         const interval = setInterval(fetchSatellites, 30_000)
         return () => clearInterval(interval)
       }
     }, [isCentral, fetchSatellites, fetchStatus])

     useEffect(() => {
       const handleClickOutside = (e: MouseEvent) => {
         if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
           setPanelOpen(false)
         }
       }
       if (panelOpen) {
         document.addEventListener('mousedown', handleClickOutside)
       }
       return () => document.removeEventListener('mousedown', handleClickOutside)
     }, [panelOpen])

     return (
       <div
         data-testid="network-status"
         style={{ position: 'relative', display: 'inline-block' }}
       >
         <button
           data-testid="network-status-button"
           onClick={() => isCentral && setPanelOpen((prev) => !prev)}
           title={isCentral
             ? `YeyoNet: ${onlineCount} satélite${onlineCount !== 1 ? 's' : ''} en línea`
             : 'YeyoNet: modo satélite'
           }
           style={{
             display: 'flex',
             alignItems: 'center',
             gap: 6,
             backgroundColor: 'transparent',
             border: '1px solid rgba(79, 195, 247, 0.2)',
             borderRadius: 20,
             padding: '4px 10px',
             cursor: isCentral ? 'pointer' : 'default',
             color: '#90CAF9',
             fontSize: 12,
             fontFamily: 'Inter, system-ui, sans-serif',
           }}
         >
           {/* Punto de estado */}
           <span
             data-testid="status-dot"
             style={{
               width: 8,
               height: 8,
               borderRadius: '50%',
               backgroundColor: hasOnline ? '#66BB6A' : '#546E7A',
               display: 'inline-block',
               boxShadow: hasOnline ? '0 0 6px rgba(102, 187, 106, 0.6)' : 'none',
             }}
           />
           {/* Texto */}
           <span data-testid="satellite-count">
             {isCentral
               ? onlineCount > 0
                 ? `${onlineCount} satélite${onlineCount !== 1 ? 's' : ''}`
                 : 'Sin satélites'
               : 'Satélite'
             }
           </span>
         </button>

         {/* Panel desplegable */}
         {panelOpen && isCentral && (
           <div
             ref={panelRef}
             data-testid="network-status-panel"
             style={{
               position: 'absolute',
               top: 'calc(100% + 8px)',
               right: 0,
               zIndex: 1500,
             }}
           >
             <SatellitePanel />
           </div>
         )}
       </div>
     )
   }

6. Crear archivo frontend/src/__tests__/yeyonet/SatellitePanel.test.tsx:

   Ruta: ~/yeyo-os/frontend/src/__tests__/yeyonet/SatellitePanel.test.tsx
   Contenido:

   /**
    * Tests para SatellitePanel — Micro-fase 7.18
    */

   import React from 'react'
   import { render, screen, waitFor, fireEvent } from '@testing-library/react'
   import { SatellitePanel } from '../../components/yeyonet/SatellitePanel'
   import { useYeyoNetStore } from '../../stores/yeyonetStore'

   // Mock del store
   jest.mock('../../stores/yeyonetStore')
   jest.mock('../../components/yeyonet/InviteModal', () => ({
     InviteModal: ({ onClose }: { onClose: () => void }) => (
       <div data-testid="invite-modal-mock">
         <button onClick={onClose}>Cerrar</button>
       </div>
     ),
   }))

   const mockStore = useYeyoNetStore as jest.MockedFunction<typeof useYeyoNetStore>

   const baseSatellite = {
     satellite_id: 'sat-001',
     name: 'Laptop Viaje',
     permissions: ['chat', 'grafos'],
     visibility_level: 1,
     status: 'online' as const,
     last_seen: new Date().toISOString(),
     connected_at: new Date().toISOString(),
     node_mode: 2,
   }

   function setupStore(overrides = {}) {
     const defaults = {
       satellites: [],
       nodeType: 'central',
       isConnected: true,
       pendingSyncCount: 0,
       isLoading: false,
       error: null,
       setSatellites: jest.fn(),
       addSatellite: jest.fn(),
       removeSatellite: jest.fn(),
       setNodeType: jest.fn(),
       setIsConnected: jest.fn(),
       setPendingSyncCount: jest.fn(),
       setLoading: jest.fn(),
       setError: jest.fn(),
       fetchSatellites: jest.fn().mockResolvedValue(undefined),
       fetchStatus: jest.fn().mockResolvedValue(undefined),
       disconnectSatellite: jest.fn().mockResolvedValue(undefined),
     }
     mockStore.mockReturnValue({ ...defaults, ...overrides } as any)
   }

   beforeEach(() => {
     jest.clearAllMocks()
   })

   describe('SatellitePanel', () => {
     it('renderiza el panel con título', () => {
       setupStore()
       render(<SatellitePanel />)
       expect(screen.getByTestId('satellite-panel')).toBeInTheDocument()
       expect(screen.getByText(/YeyoNet — Satélites/i)).toBeInTheDocument()
     })

     it('muestra estado vacío cuando no hay satélites', () => {
       setupStore({ satellites: [] })
       render(<SatellitePanel />)
       expect(screen.getByTestId('empty-state')).toBeInTheDocument()
     })

     it('muestra satélites cuando existen', () => {
       setupStore({ satellites: [baseSatellite] })
       render(<SatellitePanel />)
       expect(screen.getByTestId(`satellite-row-${baseSatellite.satellite_id}`)).toBeInTheDocument()
       expect(screen.getByText('Laptop Viaje')).toBeInTheDocument()
     })

     it('muestra estado 🟢 para satélite online', () => {
       setupStore({ satellites: [baseSatellite] })
       render(<SatellitePanel />)
       expect(screen.getByTestId(`satellite-status-${baseSatellite.satellite_id}`).textContent).toBe('🟢')
     })

     it('muestra estado ⭘ para satélite offline', () => {
       const offlineSat = { ...baseSatellite, status: 'offline' as const }
       setupStore({ satellites: [offlineSat] })
       render(<SatellitePanel />)
       expect(screen.getByTestId(`satellite-status-${offlineSat.satellite_id}`).textContent).toBe('⭘')
     })

     it('muestra botón de invitar', () => {
       setupStore()
       render(<SatellitePanel />)
       expect(screen.getByTestId('invite-button')).toBeInTheDocument()
     })

     it('abre InviteModal al hacer click en invitar', () => {
       setupStore()
       render(<SatellitePanel />)
       fireEvent.click(screen.getByTestId('invite-button'))
       expect(screen.getByTestId('invite-modal-mock')).toBeInTheDocument()
     })

     it('llama disconnectSatellite al confirmar desconexión', async () => {
       const disconnectSatellite = jest.fn().mockResolvedValue(undefined)
       setupStore({ satellites: [baseSatellite], disconnectSatellite })
       render(<SatellitePanel />)
       fireEvent.click(screen.getByTestId(`disconnect-${baseSatellite.satellite_id}`))
       fireEvent.click(screen.getByTestId(`confirm-disconnect-${baseSatellite.satellite_id}`))
       await waitFor(() => {
         expect(disconnectSatellite).toHaveBeenCalledWith(baseSatellite.satellite_id)
       })
     })

     it('muestra estado de loading', () => {
       setupStore({ isLoading: true, satellites: [] })
       render(<SatellitePanel />)
       expect(screen.getByTestId('loading-state')).toBeInTheDocument()
     })

     it('muestra error cuando hay error', () => {
       setupStore({ error: 'Connection failed', satellites: [] })
       render(<SatellitePanel />)
       expect(screen.getByTestId('error-state')).toBeInTheDocument()
     })

     it('llama fetchSatellites al montar', () => {
       const fetchSatellites = jest.fn().mockResolvedValue(undefined)
       setupStore({ fetchSatellites })
       render(<SatellitePanel />)
       expect(fetchSatellites).toHaveBeenCalledTimes(1)
     })
   })

7. Crear archivo frontend/src/__tests__/yeyonet/InviteModal.test.tsx:

   Ruta: ~/yeyo-os/frontend/src/__tests__/yeyonet/InviteModal.test.tsx
   Contenido:

   /**
    * Tests para InviteModal — Micro-fase 7.18
    */

   import React from 'react'
   import { render, screen, fireEvent, waitFor } from '@testing-library/react'
   import { InviteModal } from '../../components/yeyonet/InviteModal'

   // Mock qrcode.react
   jest.mock('qrcode.react', () => ({
     __esModule: true,
     default: ({ value }: { value: string }) => (
       <div data-testid="qr-code-mock" data-value={value}>QR</div>
     ),
   }))

   // Mock fetch
   global.fetch = jest.fn()

   const mockOnClose = jest.fn()

   beforeEach(() => {
     jest.clearAllMocks()
   })

   describe('InviteModal', () => {
     it('renderiza el modal correctamente', () => {
       render(<InviteModal onClose={mockOnClose} />)
       expect(screen.getByTestId('invite-modal')).toBeInTheDocument()
       expect(screen.getByTestId('satellite-name-input')).toBeInTheDocument()
     })

     it('muestra error cuando se intenta generar sin nombre', async () => {
       render(<InviteModal onClose={mockOnClose} />)
       fireEvent.click(screen.getByTestId('generate-button'))
       await waitFor(() => {
         expect(screen.getByTestId('invite-error')).toBeInTheDocument()
       })
     })

     it('tiene checkbox de permisos', () => {
       render(<InviteModal onClose={mockOnClose} />)
       expect(screen.getByTestId('perm-chat')).toBeInTheDocument()
       expect(screen.getByTestId('perm-grafos')).toBeInTheDocument()
       expect(screen.getByTestId('perm-memoria')).toBeInTheDocument()
       expect(screen.getByTestId('perm-control')).toBeInTheDocument()
     })

     it('tiene selector de expiración', () => {
       render(<InviteModal onClose={mockOnClose} />)
       expect(screen.getByTestId('expiry-select')).toBeInTheDocument()
     })

     it('llama onClose al hacer click en cancelar', () => {
       render(<InviteModal onClose={mockOnClose} />)
       fireEvent.click(screen.getByText('Cancelar'))
       expect(mockOnClose).toHaveBeenCalledTimes(1)
     })

     it('muestra código generado y QR al generar exitosamente', async () => {
       const mockFetch = global.fetch as jest.Mock
       mockFetch.mockResolvedValueOnce({
         ok: true,
         json: async () => ({
           code: 'YEYO-ABCD-EFGH-IJKL',
           satellite_name: 'Test Sat',
           permissions: ['chat'],
           expires_at: new Date(Date.now() + 7 * 86400000).toISOString(),
           created_at: new Date().toISOString(),
         }),
       })

       render(<InviteModal onClose={mockOnClose} />)
       fireEvent.change(screen.getByTestId('satellite-name-input'), {
         target: { value: 'Test Sat' },
       })
       fireEvent.click(screen.getByTestId('generate-button'))

       await waitFor(() => {
         expect(screen.getByTestId('generated-code')).toBeInTheDocument()
       })
       expect(screen.getByTestId('generated-code').textContent).toBe('YEYO-ABCD-EFGH-IJKL')
       expect(screen.getByTestId('qr-code')).toBeInTheDocument()
     })

     it('muestra error cuando la API falla', async () => {
       const mockFetch = global.fetch as jest.Mock
       mockFetch.mockResolvedValueOnce({
         ok: false,
         status: 500,
         json: async () => ({ detail: 'Internal Server Error' }),
       })

       render(<InviteModal onClose={mockOnClose} />)
       fireEvent.change(screen.getByTestId('satellite-name-input'), {
         target: { value: 'Test Sat' },
       })
       fireEvent.click(screen.getByTestId('generate-button'))

       await waitFor(() => {
         expect(screen.getByTestId('invite-error')).toBeInTheDocument()
       })
     })

     it('muestra botón de copiar después de generar', async () => {
       const mockFetch = global.fetch as jest.Mock
       mockFetch.mockResolvedValueOnce({
         ok: true,
         json: async () => ({
           code: 'YEYO-ABCD-EFGH-IJKL',
           satellite_name: 'Sat',
           permissions: ['chat'],
           expires_at: new Date().toISOString(),
           created_at: new Date().toISOString(),
         }),
       })

       render(<InviteModal onClose={mockOnClose} />)
       fireEvent.change(screen.getByTestId('satellite-name-input'), {
         target: { value: 'Sat' },
       })
       fireEvent.click(screen.getByTestId('generate-button'))

       await waitFor(() => {
         expect(screen.getByTestId('copy-button')).toBeInTheDocument()
       })
     })
   })

8. Crear archivo frontend/src/__tests__/yeyonet/ConnectScreen.test.tsx:

   Ruta: ~/yeyo-os/frontend/src/__tests__/yeyonet/ConnectScreen.test.tsx
   Contenido:

   /**
    * Tests para ConnectScreen — Micro-fase 7.18
    */

   import React from 'react'
   import { render, screen, fireEvent, waitFor } from '@testing-library/react'
   import { ConnectScreen } from '../../components/yeyonet/ConnectScreen'

   global.fetch = jest.fn()

   beforeEach(() => {
     jest.clearAllMocks()
   })

   describe('ConnectScreen', () => {
     it('renderiza en step idle inicialmente', () => {
       render(<ConnectScreen />)
       const screen_el = screen.getByTestId('connect-screen')
       expect(screen_el).toBeInTheDocument()
       expect(screen_el).toHaveAttribute('data-step', 'idle')
     })

     it('muestra input de código', () => {
       render(<ConnectScreen />)
       expect(screen.getByTestId('code-input')).toBeInTheDocument()
     })

     it('muestra botón de conectar', () => {
       render(<ConnectScreen />)
       expect(screen.getByTestId('connect-button')).toBeInTheDocument()
     })

     it('muestra botón de escanear QR', () => {
       render(<ConnectScreen />)
       expect(screen.getByTestId('scan-qr-button')).toBeInTheDocument()
     })

     it('conecta exitosamente con código válido', async () => {
       const mockFetch = global.fetch as jest.Mock
       mockFetch.mockResolvedValueOnce({
         ok: true,
         json: async () => ({
           ok: true,
           satellite_id: 'sat-123',
           satellite_name: 'Mi PC',
           permissions: ['chat'],
           visibility_level: 1,
           central_url: 'ws://localhost:8765',
         }),
       })

       const onConnected = jest.fn()
       render(<ConnectScreen onConnected={onConnected} />)

       fireEvent.change(screen.getByTestId('code-input'), {
         target: { value: 'YEYO-ABCD-EFGH-IJKL' },
       })
       fireEvent.click(screen.getByTestId('connect-button'))

       await waitFor(() => {
         expect(screen.getByTestId('success-state')).toBeInTheDocument()
       })
       expect(onConnected).toHaveBeenCalledWith('sat-123')
     })

     it('muestra error con código inválido (formato incorrecto)', async () => {
       render(<ConnectScreen />)
       fireEvent.change(screen.getByTestId('code-input'), {
         target: { value: 'CODIGO-MALO' },
       })
       fireEvent.click(screen.getByTestId('connect-button'))
       await waitFor(() => {
         expect(screen.getByTestId('error-message')).toBeInTheDocument()
       })
     })

     it('muestra error cuando la API rechaza el código', async () => {
       const mockFetch = global.fetch as jest.Mock
       mockFetch.mockResolvedValueOnce({
         ok: false,
         status: 400,
         json: async () => ({ detail: 'Código inválido o ya utilizado' }),
       })

       render(<ConnectScreen />)
       fireEvent.change(screen.getByTestId('code-input'), {
         target: { value: 'YEYO-FAKE-FAKE-FAKE' },
       })
       fireEvent.click(screen.getByTestId('connect-button'))

       await waitFor(() => {
         expect(screen.getByTestId('error-message')).toBeInTheDocument()
       })
     })

     it('convierte el código a mayúsculas al escribir', () => {
       render(<ConnectScreen />)
       const input = screen.getByTestId('code-input')
       fireEvent.change(input, { target: { value: 'yeyo-abcd-efgh-ijkl' } })
       expect((input as HTMLInputElement).value).toBe('YEYO-ABCD-EFGH-IJKL')
     })
   })

9. Crear archivo frontend/src/__tests__/yeyonet/NetworkStatus.test.tsx:

   Ruta: ~/yeyo-os/frontend/src/__tests__/yeyonet/NetworkStatus.test.tsx
   Contenido:

   /**
    * Tests para NetworkStatus — Micro-fase 7.18
    */

   import React from 'react'
   import { render, screen, fireEvent } from '@testing-library/react'
   import { NetworkStatus } from '../../components/yeyonet/NetworkStatus'
   import { useYeyoNetStore } from '../../stores/yeyonetStore'

   jest.mock('../../stores/yeyonetStore')
   jest.mock('../../components/yeyonet/SatellitePanel', () => ({
     SatellitePanel: () => <div data-testid="satellite-panel-mock">Panel</div>,
   }))

   const mockStore = useYeyoNetStore as jest.MockedFunction<typeof useYeyoNetStore>

   function setupStore(overrides = {}) {
     const defaults = {
       satellites: [],
       nodeType: 'central',
       isConnected: false,
       pendingSyncCount: 0,
       isLoading: false,
       error: null,
       setSatellites: jest.fn(),
       addSatellite: jest.fn(),
       removeSatellite: jest.fn(),
       setNodeType: jest.fn(),
       setIsConnected: jest.fn(),
       setPendingSyncCount: jest.fn(),
       setLoading: jest.fn(),
       setError: jest.fn(),
       fetchSatellites: jest.fn().mockResolvedValue(undefined),
       fetchStatus: jest.fn().mockResolvedValue(undefined),
       disconnectSatellite: jest.fn().mockResolvedValue(undefined),
     }
     mockStore.mockReturnValue({ ...defaults, ...overrides } as any)
   }

   describe('NetworkStatus', () => {
     it('renderiza el widget', () => {
       setupStore()
       render(<NetworkStatus />)
       expect(screen.getByTestId('network-status')).toBeInTheDocument()
     })

     it('muestra punto gris cuando no hay satélites online', () => {
       setupStore({ satellites: [] })
       render(<NetworkStatus />)
       const dot = screen.getByTestId('status-dot')
       expect(dot).toHaveStyle({ backgroundColor: '#546E7A' })
     })

     it('muestra punto verde cuando hay satélites online', () => {
       setupStore({
         satellites: [
           {
             satellite_id: 's1',
             name: 'Sat',
             status: 'online',
             permissions: [],
             visibility_level: 1,
             last_seen: null,
             connected_at: null,
             node_mode: 1,
           },
         ],
       })
       render(<NetworkStatus />)
       const dot = screen.getByTestId('status-dot')
       expect(dot).toHaveStyle({ backgroundColor: '#66BB6A' })
     })

     it('muestra conteo de satélites activos', () => {
       setupStore({
         satellites: [
           { satellite_id: 's1', name: 'S1', status: 'online', permissions: [], visibility_level: 1, last_seen: null, connected_at: null, node_mode: 1 },
           { satellite_id: 's2', name: 'S2', status: 'online', permissions: [], visibility_level: 1, last_seen: null, connected_at: null, node_mode: 1 },
         ],
       })
       render(<NetworkStatus />)
       expect(screen.getByTestId('satellite-count').textContent).toContain('2')
     })

     it('abre SatellitePanel al hacer click (Central)', () => {
       setupStore({ nodeType: 'central' })
       render(<NetworkStatus />)
       fireEvent.click(screen.getByTestId('network-status-button'))
       expect(screen.getByTestId('network-status-panel')).toBeInTheDocument()
     })

     it('no abre panel si es satélite (no es Central)', () => {
       setupStore({ nodeType: 'satellite' })
       render(<NetworkStatus />)
       fireEvent.click(screen.getByTestId('network-status-button'))
       expect(screen.queryByTestId('network-status-panel')).not.toBeInTheDocument()
     })

     it('llama fetchStatus al montar', () => {
       const fetchStatus = jest.fn().mockResolvedValue(undefined)
       setupStore({ fetchStatus })
       render(<NetworkStatus />)
       expect(fetchStatus).toHaveBeenCalledTimes(1)
     })
   })

VERIFICAR:
- [ ] npm install qrcode.react html5-qrcode sin errores
- [ ] frontend/src/stores/yeyonetStore.ts exporta useYeyoNetStore con fetchSatellites, fetchStatus, disconnectSatellite
- [ ] SatellitePanel.tsx renderiza lista con 🟢/🟡/⭘ según status, botones desconectar con confirmación
- [ ] InviteModal.tsx genera invitación vía POST /api/yeyonet/invite y muestra QR con qrcode.react
- [ ] ConnectScreen.tsx conecta vía POST /api/yeyonet/connect, convierte código a mayúsculas, muestra success state
- [ ] NetworkStatus.tsx muestra punto verde/gris, abre SatellitePanel al hacer click (solo Central)
- [ ] Tests Jest pasan: SatellitePanel (10 tests), InviteModal (7 tests), ConnectScreen (5 tests), NetworkStatus (7 tests)

SI FALLA:
- qrcode.react import error: verificar que el import usa default export (import QRCode from 'qrcode.react')
- html5-qrcode import en tests: está dentro de import() dinámico, no afecta tests unitarios
- Tests fallan por useYeyoNetStore: el mock con jest.mock('../../stores/yeyonetStore') debe estar al top del test
- TypeScript error en QRCode: npm install --save-dev @types/qrcode (o usar // @ts-ignore si no hay types)
- fetch not defined en tests: agregar global.fetch = jest.fn() en beforeEach
- NEXT_PUBLIC_NODE_TYPE no definida: el store usa ?? 'satellite' como default, no falla

NO HACER:
- No implementar WebRTC en el frontend (solo WebSocket sobre Tailscale en Capa 7)
- No mostrar pantalla en tiempo real del satélite — ni capturas, ni screenshare
- No guardar el auth_token en localStorage — solo en memoria del store o cookies httpOnly
- No hacer polling más frecuente que 30s para lista de satélites (no es crítico)
- No implementar edición de permisos de satélite existente (futuro — solo crear/desconectar en Capa 7)

GATE: Central ve sus satélites con estado 🟢/🟡/⭘ en tiempo real (polling 30s), puede generar invitación con QR usando qrcode.react, satélite puede conectar con código YEYO-XXXX-XXXX-XXXX y llega a success state, NetworkStatus en topbar muestra punto verde con conteo cuando hay satélites online. Todos los tests pasan (≥29 tests Jest).
```
