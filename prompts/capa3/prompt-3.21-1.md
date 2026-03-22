## ═══════════════════════════════════════
## MICRO-FASE 3.21 — Seguridad Visual: Permission Alerts + Kill Switch + Dashboard
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 3.21-1 [VSCODE] — Popup de permisos por zona, Kill Switch overlay y Security Dashboard

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 3.21 de Capa 3 (Cuerpo): implementar la capa de seguridad visual — popups de permisos con tres zonas de riesgo (verde/amarilla/roja), overlay del Kill Switch, dashboard de seguridad y el backend de permisos con WebSocket.

CONTEXTO:
- Micro-fases 3.0–3.20 completadas: Hub Canvas, nodos, grafos, doble cuadrícula, onboarding, Topbar + Sidebar todos funcionando
- Stack: Next.js + React + TypeScript, Zustand para estado, CSS animations
- Backend: FastAPI en src/api/, Python con asyncio
- Topbar.tsx existe en frontend/src/components/layout/Topbar.tsx (de 3.20)
- Kill Switch (Ctrl+Alt+K) ya tiene registro en systemStore — este overlay lo complementa visualmente
- Las zonas de permisos son: verde (auto-aprueba silencioso), amarilla (popup + chat), roja (confirmación manual)
- Hardware objetivo: GTX 1060 3GB — las animaciones CSS deben ser ligeras (no WebGL)
- La seguridad visual es CRÍTICA: el usuario siempre debe saber qué está pasando

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo frontend/src/components/security/PermissionAlert.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/security/PermissionAlert.tsx
   Contenido:

   /**
    * YeyoOS — PermissionAlert
    * Micro-fase 3.21 — Capa 3: Cuerpo
    *
    * Popup de alerta de permisos con tres zonas de riesgo:
    * - Verde: NO renderiza nada (log silencioso)
    * - Amarilla: overlay semitransparente, borde pulsante amarillo, chat inline, 4 botones
    * - Roja: flash rojo, borde rojo intenso, campo "confirmo" obligatorio, 2 botones
    */

   import React, { useState, useEffect, useRef, useCallback } from 'react'

   export type PermissionZone = 'green' | 'yellow' | 'red'

   export interface PermissionAlertProps {
     nodeName: string
     nodeIcon: string
     permission: string
     permissionLabel: string
     zone: PermissionZone
     taskDescription: string
     packageInfo?: { name: string; origin: string; size: string }
     onAllow: () => void
     onAllowAlways: () => void
     onDeny: () => void
     onAskMore: (question: string) => void
   }

   interface ChatMessage {
     role: 'user' | 'system'
     text: string
   }

   const ZONE_STYLES = {
     yellow: {
       overlay: 'rgba(0,0,0,0.60)',
       borderColor: '#FFD600',
       borderAnimation: 'pulse-yellow',
       borderWidth: 4,
     },
     red: {
       overlay: 'rgba(0,0,0,0.75)',
       borderColor: '#FF1744',
       borderAnimation: 'pulse-red',
       borderWidth: 5,
     },
   }

   export function PermissionAlert({
     nodeName,
     nodeIcon,
     permission,
     permissionLabel,
     zone,
     taskDescription,
     packageInfo,
     onAllow,
     onAllowAlways,
     onDeny,
     onAskMore,
   }: PermissionAlertProps) {
     const [confirmText, setConfirmText] = useState('')
     const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
     const [chatInput, setChatInput] = useState('')
     const [showDetails, setShowDetails] = useState(false)
     const [flashActive, setFlashActive] = useState(false)
     const confirmRef = useRef<HTMLInputElement>(null)
     const chatInputRef = useRef<HTMLInputElement>(null)

     // Zona verde: no renderiza nada
     if (zone === 'green') return null

     // Zona roja: flash inicial 0.5s
     useEffect(() => {
       if (zone === 'red') {
         setFlashActive(true)
         const t = setTimeout(() => setFlashActive(false), 500)
         return () => clearTimeout(t)
       }
     }, [zone])

     const canProceedRed = confirmText.trim().toLowerCase() === 'confirmo'

     const handleChatSend = useCallback(() => {
       const q = chatInput.trim()
       if (!q || chatMessages.length >= 6) return
       const newMessages: ChatMessage[] = [...chatMessages, { role: 'user', text: q }]
       setChatMessages(newMessages)
       setChatInput('')
       onAskMore(q)
     }, [chatInput, chatMessages, onAskMore])

     const handleChatKeyDown = useCallback(
       (e: React.KeyboardEvent<HTMLInputElement>) => {
         if (e.key === 'Enter') handleChatSend()
       },
       [handleChatSend]
     )

     const styles = ZONE_STYLES[zone as 'yellow' | 'red']

     return (
       <>
         {/* Estilos CSS para animaciones */}
         <style>{`
           @keyframes pulse-yellow {
             0%, 100% { box-shadow: inset 0 0 0 4px #FFD600, inset 0 0 20px rgba(255,214,0,0.3); }
             50% { box-shadow: inset 0 0 0 4px #FFD600, inset 0 0 40px rgba(255,214,0,0.7); }
           }
           @keyframes pulse-red {
             0%, 100% { box-shadow: inset 0 0 0 5px #FF1744, inset 0 0 20px rgba(255,23,68,0.4); }
             50% { box-shadow: inset 0 0 0 5px #FF1744, inset 0 0 50px rgba(255,23,68,0.8); }
           }
           @keyframes flash-red-bg {
             0% { background: rgba(255,23,68,0.4); }
             100% { background: rgba(0,0,0,0.75); }
           }
         `}</style>

         {/* Overlay de pantalla completa */}
         <div
           data-testid="permission-alert-overlay"
           data-zone={zone}
           style={{
             position: 'fixed',
             inset: 0,
             background: flashActive
               ? 'rgba(255,23,68,0.4)'
               : styles.overlay,
             animation: flashActive
               ? 'flash-red-bg 0.5s ease forwards'
               : undefined,
             zIndex: 9000,
             display: 'flex',
             alignItems: 'center',
             justifyContent: 'center',
           }}
         />

         {/* Borde pulsante de pantalla */}
         <div
           data-testid="permission-alert-border"
           style={{
             position: 'fixed',
             inset: 0,
             pointerEvents: 'none',
             zIndex: 9001,
             animation: `${styles.borderAnimation} ${zone === 'yellow' ? '2s' : '1s'} ease-in-out infinite`,
           }}
         />

         {/* Popup central */}
         <div
           data-testid="permission-alert-popup"
           style={{
             position: 'fixed',
             top: '50%',
             left: '50%',
             transform: 'translate(-50%, -50%)',
             zIndex: 9002,
             background: '#0D1117',
             border: `2px solid ${styles.borderColor}`,
             borderRadius: 12,
             padding: '28px 32px',
             minWidth: 420,
             maxWidth: 560,
             boxShadow: `0 0 40px ${styles.borderColor}44`,
             fontFamily: 'Inter, system-ui, sans-serif',
             color: '#E0E6ED',
           }}
         >
           {/* Cabecera */}
           <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
             <span style={{ fontSize: 32 }}>{nodeIcon}</span>
             <div>
               <div style={{ fontWeight: 700, fontSize: 16, color: '#fff' }}>{nodeName}</div>
               <div style={{ fontSize: 13, color: '#8B949E' }}>solicita permiso</div>
             </div>
             {zone === 'red' && (
               <div
                 data-testid="high-risk-badge"
                 style={{
                   marginLeft: 'auto',
                   background: '#FF1744',
                   color: '#fff',
                   fontWeight: 800,
                   fontSize: 11,
                   padding: '4px 10px',
                   borderRadius: 4,
                   letterSpacing: 1,
                 }}
               >
                 ACCIÓN DE ALTO RIESGO
               </div>
             )}
           </div>

           {/* Permiso solicitado */}
           <div
             style={{
               background: zone === 'red' ? '#1A0A0A' : '#0F1923',
               border: `1px solid ${styles.borderColor}44`,
               borderRadius: 8,
               padding: '12px 16px',
               marginBottom: 16,
             }}
           >
             <div style={{ fontSize: 12, color: '#8B949E', marginBottom: 4, textTransform: 'uppercase', letterSpacing: 0.8 }}>
               Permiso
             </div>
             <div style={{ fontWeight: 600, fontSize: 15, color: zone === 'red' ? '#FF6B6B' : '#FFD600' }}>
               {permissionLabel}
             </div>
             <div style={{ fontSize: 12, color: '#8B949E', marginTop: 4, fontFamily: 'monospace' }}>
               {permission}
             </div>
           </div>

           {/* Tarea */}
           <div style={{ fontSize: 14, color: '#C9D1D9', marginBottom: 16 }}>
             <span style={{ color: '#8B949E' }}>Para: </span>
             {taskDescription}
           </div>

           {/* Info de paquete (zona roja) */}
           {zone === 'red' && packageInfo && (
             <div
               data-testid="package-info"
               style={{
                 background: '#1A0A0A',
                 border: '1px solid #FF174444',
                 borderRadius: 8,
                 padding: '10px 14px',
                 marginBottom: 16,
                 fontSize: 13,
               }}
             >
               <div style={{ color: '#8B949E', marginBottom: 4, fontSize: 11, textTransform: 'uppercase' }}>Paquete/Origen</div>
               <div>📦 <strong>{packageInfo.name}</strong></div>
               <div style={{ color: '#8B949E' }}>Origen: {packageInfo.origin}</div>
               <div style={{ color: '#8B949E' }}>Tamaño: {packageInfo.size}</div>
             </div>
           )}

           {/* Advertencia irreversible (zona roja) */}
           {zone === 'red' && (
             <div
               data-testid="irreversible-warning"
               style={{
                 background: '#FF174422',
                 border: '1px solid #FF1744',
                 borderRadius: 6,
                 padding: '8px 14px',
                 marginBottom: 20,
                 color: '#FF6B6B',
                 fontWeight: 700,
                 fontSize: 13,
                 textAlign: 'center',
                 letterSpacing: 0.5,
               }}
             >
               ⚠️ ESTO NO SE PUEDE DESHACER FÁCILMENTE
             </div>
           )}

           {/* Chat inline (zona amarilla, máx 3 turnos = 6 mensajes) */}
           {zone === 'yellow' && (
             <div
               data-testid="inline-chat"
               style={{ marginBottom: 20 }}
             >
               {chatMessages.length > 0 && (
                 <div
                   style={{
                     background: '#0F1923',
                     borderRadius: 8,
                     padding: '10px 12px',
                     marginBottom: 10,
                     maxHeight: 140,
                     overflowY: 'auto',
                   }}
                 >
                   {chatMessages.map((msg, i) => (
                     <div
                       key={i}
                       style={{
                         marginBottom: 6,
                         textAlign: msg.role === 'user' ? 'right' : 'left',
                         fontSize: 13,
                         color: msg.role === 'user' ? '#4FC3F7' : '#C9D1D9',
                       }}
                     >
                       {msg.role === 'user' ? '👤 ' : '🤖 '}
                       {msg.text}
                     </div>
                   ))}
                 </div>
               )}
               {chatMessages.length < 6 && (
                 <div style={{ display: 'flex', gap: 8 }}>
                   <input
                     ref={chatInputRef}
                     data-testid="chat-input"
                     type="text"
                     value={chatInput}
                     onChange={(e) => setChatInput(e.target.value)}
                     onKeyDown={handleChatKeyDown}
                     placeholder="¿Por qué necesitas este permiso?"
                     style={{
                       flex: 1,
                       background: '#0F1923',
                       border: '1px solid #FFD60044',
                       borderRadius: 6,
                       color: '#E0E6ED',
                       padding: '7px 10px',
                       fontSize: 13,
                       outline: 'none',
                     }}
                   />
                   <button
                     onClick={handleChatSend}
                     style={{
                       background: '#FFD600',
                       color: '#000',
                       border: 'none',
                       borderRadius: 6,
                       padding: '7px 14px',
                       fontWeight: 700,
                       cursor: 'pointer',
                       fontSize: 13,
                     }}
                   >
                     →
                   </button>
                 </div>
               )}
             </div>
           )}

           {/* Campo "confirmo" (zona roja) */}
           {zone === 'red' && (
             <div style={{ marginBottom: 20 }}>
               <div style={{ fontSize: 13, color: '#8B949E', marginBottom: 8 }}>
                 Escribe <strong style={{ color: '#FF6B6B' }}>confirmo</strong> para continuar:
               </div>
               <input
                 ref={confirmRef}
                 data-testid="confirm-input"
                 type="text"
                 value={confirmText}
                 onChange={(e) => setConfirmText(e.target.value)}
                 placeholder="confirmo"
                 autoFocus
                 style={{
                   width: '100%',
                   background: '#0D0000',
                   border: `1px solid ${canProceedRed ? '#FF1744' : '#FF174444'}`,
                   borderRadius: 6,
                   color: '#FF6B6B',
                   padding: '10px 14px',
                   fontSize: 15,
                   outline: 'none',
                   textAlign: 'center',
                   letterSpacing: 2,
                   fontWeight: 600,
                   boxSizing: 'border-box',
                 }}
               />
             </div>
           )}

           {/* Botones zona amarilla */}
           {zone === 'yellow' && (
             <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
               <button
                 data-testid="btn-allow-once"
                 onClick={onAllow}
                 style={{
                   background: '#FFD60022',
                   border: '1px solid #FFD600',
                   color: '#FFD600',
                   borderRadius: 6,
                   padding: '9px 16px',
                   fontWeight: 600,
                   cursor: 'pointer',
                   fontSize: 13,
                   flex: 1,
                 }}
               >
                 Permitir esta vez
               </button>
               <button
                 data-testid="btn-allow-always"
                 onClick={onAllowAlways}
                 style={{
                   background: '#1B4332',
                   border: '1px solid #2EA043',
                   color: '#2EA043',
                   borderRadius: 6,
                   padding: '9px 16px',
                   fontWeight: 600,
                   cursor: 'pointer',
                   fontSize: 13,
                   flex: 1,
                 }}
               >
                 Siempre permitir
               </button>
               <button
                 data-testid="btn-deny"
                 onClick={onDeny}
                 style={{
                   background: '#1A0A0A',
                   border: '1px solid #FF4444',
                   color: '#FF6B6B',
                   borderRadius: 6,
                   padding: '9px 16px',
                   fontWeight: 600,
                   cursor: 'pointer',
                   fontSize: 13,
                   flex: 1,
                 }}
               >
                 Denegar
               </button>
               <button
                 data-testid="btn-details"
                 onClick={() => setShowDetails(!showDetails)}
                 style={{
                   background: 'transparent',
                   border: '1px solid #30363D',
                   color: '#8B949E',
                   borderRadius: 6,
                   padding: '9px 16px',
                   cursor: 'pointer',
                   fontSize: 13,
                   flex: '0 0 auto',
                 }}
               >
                 Ver detalles técnicos
               </button>
             </div>
           )}

           {/* Botones zona roja */}
           {zone === 'red' && (
             <div style={{ display: 'flex', gap: 10 }}>
               <button
                 data-testid="btn-proceed-red"
                 onClick={onAllow}
                 disabled={!canProceedRed}
                 style={{
                   flex: 1,
                   background: canProceedRed ? '#FF1744' : '#FF174433',
                   border: `1px solid ${canProceedRed ? '#FF1744' : '#FF174444'}`,
                   color: canProceedRed ? '#fff' : '#FF174477',
                   borderRadius: 6,
                   padding: '11px 16px',
                   fontWeight: 700,
                   cursor: canProceedRed ? 'pointer' : 'not-allowed',
                   fontSize: 14,
                   transition: 'all 0.2s',
                 }}
               >
                 Entiendo, proceder
               </button>
               <button
                 data-testid="btn-cancel-red"
                 onClick={onDeny}
                 style={{
                   flex: 1,
                   background: '#161B22',
                   border: '1px solid #30363D',
                   color: '#C9D1D9',
                   borderRadius: 6,
                   padding: '11px 16px',
                   fontWeight: 600,
                   cursor: 'pointer',
                   fontSize: 14,
                 }}
               >
                 Cancelar todo
               </button>
             </div>
           )}

           {/* Detalles técnicos (expandible zona amarilla) */}
           {showDetails && (
             <div
               data-testid="technical-details"
               style={{
                 marginTop: 16,
                 padding: '10px 14px',
                 background: '#0F1923',
                 borderRadius: 8,
                 fontSize: 12,
                 fontFamily: 'monospace',
                 color: '#8B949E',
               }}
             >
               <div><strong>nodo:</strong> {nodeName}</div>
               <div><strong>permiso:</strong> {permission}</div>
               <div><strong>zona:</strong> {zone}</div>
               <div><strong>tarea:</strong> {taskDescription}</div>
               {packageInfo && (
                 <>
                   <div><strong>paquete:</strong> {packageInfo.name}</div>
                   <div><strong>origen:</strong> {packageInfo.origin}</div>
                   <div><strong>tamaño:</strong> {packageInfo.size}</div>
                 </>
               )}
             </div>
           )}
         </div>
       </>
     )
   }

2. Crear archivo frontend/src/components/security/SecurityDashboard.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/security/SecurityDashboard.tsx
   Contenido:

   /**
    * YeyoOS — SecurityDashboard
    * Micro-fase 3.21 — Capa 3: Cuerpo
    *
    * Dashboard de seguridad: resumen de permisos, lista de nodos,
    * historial últimas 24h, drawer lateral por nodo.
    */

   import React, { useState, useMemo } from 'react'
   import { useSecurityStore, PermissionRecord, AccessLogEntry } from '../../stores/securityStore'

   export function SecurityDashboard() {
     const { permissions, history, denyPermission } = useSecurityStore()
     const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
     const [drawerOpen, setDrawerOpen] = useState(false)

     const now = Date.now()
     const last24h = useMemo(
       () => history.filter((e) => now - e.timestamp < 24 * 60 * 60 * 1000),
       [history, now]
     )

     const autoActive = useMemo(
       () => [...permissions.values()].flat().filter((p) => p.zone === 'green').length,
       [permissions]
     )
     const confirmed = useMemo(
       () => last24h.filter((e) => e.result === 'allowed').length,
       [last24h]
     )
     const blocked = useMemo(
       () => last24h.filter((e) => e.result === 'denied').length,
       [last24h]
     )

     const selectedPerms = selectedNodeId ? permissions.get(selectedNodeId) ?? [] : []
     const selectedHistory = useMemo(
       () => last24h.filter((e) => e.nodeId === selectedNodeId),
       [last24h, selectedNodeId]
     )

     const openDrawer = (nodeId: string) => {
       setSelectedNodeId(nodeId)
       setDrawerOpen(true)
     }
     const closeDrawer = () => {
       setDrawerOpen(false)
       setSelectedNodeId(null)
     }

     return (
       <div
         data-testid="security-dashboard"
         style={{
           padding: '24px 32px',
           fontFamily: 'Inter, system-ui, sans-serif',
           color: '#C9D1D9',
           background: '#0D1117',
           minHeight: '100%',
         }}
       >
         <h2 style={{ color: '#fff', marginBottom: 24, fontSize: 22, fontWeight: 700 }}>
           🛡️ Seguridad
         </h2>

         {/* Cards resumen */}
         <div
           data-testid="summary-cards"
           style={{ display: 'flex', gap: 16, marginBottom: 32 }}
         >
           {[
             { label: 'Auto activos', value: autoActive, color: '#2EA043', icon: '🟢' },
             { label: 'Confirmados (24h)', value: confirmed, color: '#FFD600', icon: '✅' },
             { label: 'Bloqueados (24h)', value: blocked, color: '#FF4444', icon: '❌' },
           ].map((card) => (
             <div
               key={card.label}
               data-testid={`card-${card.label.toLowerCase().replace(/\s+/g, '-').replace(/[()\/]/g, '')}`}
               style={{
                 flex: 1,
                 background: '#161B22',
                 border: `1px solid ${card.color}44`,
                 borderRadius: 10,
                 padding: '16px 20px',
               }}
             >
               <div style={{ fontSize: 28, fontWeight: 800, color: card.color }}>
                 {card.icon} {card.value}
               </div>
               <div style={{ fontSize: 13, color: '#8B949E', marginTop: 4 }}>{card.label}</div>
             </div>
           ))}
         </div>

         {/* Lista de nodos con permisos */}
         <div style={{ marginBottom: 32 }}>
           <h3 style={{ fontSize: 15, fontWeight: 600, color: '#8B949E', marginBottom: 14, textTransform: 'uppercase', letterSpacing: 0.8 }}>
             Nodos y Permisos
           </h3>
           <div
             data-testid="nodes-list"
             style={{ display: 'flex', flexDirection: 'column', gap: 8 }}
           >
             {[...permissions.entries()].map(([nodeId, perms]) => (
               <div
                 key={nodeId}
                 data-testid={`node-row-${nodeId}`}
                 onClick={() => openDrawer(nodeId)}
                 style={{
                   background: '#161B22',
                   border: '1px solid #21262D',
                   borderRadius: 8,
                   padding: '12px 16px',
                   cursor: 'pointer',
                   display: 'flex',
                   alignItems: 'center',
                   gap: 12,
                   transition: 'border-color 0.15s',
                 }}
               >
                 <div style={{ fontWeight: 600, flex: 1 }}>{nodeId}</div>
                 <div style={{ display: 'flex', gap: 6 }}>
                   {perms.map((p) => (
                     <span
                       key={p.permission}
                       style={{
                         fontSize: 11,
                         padding: '2px 8px',
                         borderRadius: 12,
                         background:
                           p.zone === 'green' ? '#1B4332' :
                           p.zone === 'yellow' ? '#2E2400' : '#1A0A0A',
                         color:
                           p.zone === 'green' ? '#2EA043' :
                           p.zone === 'yellow' ? '#FFD600' : '#FF6B6B',
                         border: `1px solid ${
                           p.zone === 'green' ? '#2EA04344' :
                           p.zone === 'yellow' ? '#FFD60044' : '#FF174444'
                         }`,
                       }}
                     >
                       {p.zone === 'green' ? '🟢' : p.zone === 'yellow' ? '🟡' : '🔴'} {p.permissionLabel}
                     </span>
                   ))}
                 </div>
                 <span style={{ color: '#8B949E', fontSize: 18 }}>›</span>
               </div>
             ))}
             {permissions.size === 0 && (
               <div style={{ color: '#8B949E', fontSize: 14, padding: '16px 0' }}>
                 Ningún nodo ha solicitado permisos aún.
               </div>
             )}
           </div>
         </div>

         {/* Historial últimas 24h */}
         <div>
           <h3 style={{ fontSize: 15, fontWeight: 600, color: '#8B949E', marginBottom: 14, textTransform: 'uppercase', letterSpacing: 0.8 }}>
             Historial últimas 24h
           </h3>
           <div
             data-testid="access-history"
             style={{
               background: '#161B22',
               border: '1px solid #21262D',
               borderRadius: 8,
               overflow: 'hidden',
             }}
           >
             {last24h.length === 0 ? (
               <div style={{ padding: '16px 20px', color: '#8B949E', fontSize: 14 }}>
                 Sin actividad en las últimas 24 horas.
               </div>
             ) : (
               last24h.slice().reverse().map((entry, i) => (
                 <div
                   key={i}
                   data-testid="history-entry"
                   style={{
                     display: 'flex',
                     alignItems: 'center',
                     gap: 12,
                     padding: '10px 16px',
                     borderBottom: i < last24h.length - 1 ? '1px solid #21262D' : 'none',
                     fontSize: 13,
                   }}
                 >
                   <span style={{ color: '#8B949E', fontFamily: 'monospace', minWidth: 80 }}>
                     {new Date(entry.timestamp).toLocaleTimeString()}
                   </span>
                   <span style={{ fontWeight: 600, minWidth: 100 }}>{entry.nodeId}</span>
                   <span style={{ color: '#8B949E', flex: 1 }}>{entry.permissionLabel}</span>
                   <span>{entry.result === 'allowed' ? '✅' : '❌'}</span>
                 </div>
               ))
             )}
           </div>
         </div>

         {/* Drawer lateral por nodo */}
         {drawerOpen && selectedNodeId && (
           <>
             <div
               data-testid="drawer-backdrop"
               onClick={closeDrawer}
               style={{
                 position: 'fixed',
                 inset: 0,
                 background: 'rgba(0,0,0,0.5)',
                 zIndex: 800,
               }}
             />
             <div
               data-testid="node-drawer"
               style={{
                 position: 'fixed',
                 top: 0,
                 right: 0,
                 bottom: 0,
                 width: 380,
                 background: '#161B22',
                 borderLeft: '1px solid #30363D',
                 zIndex: 801,
                 padding: '24px 24px',
                 overflowY: 'auto',
                 fontFamily: 'Inter, system-ui, sans-serif',
                 color: '#C9D1D9',
               }}
             >
               <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
                 <h3 style={{ margin: 0, fontSize: 18, color: '#fff' }}>{selectedNodeId}</h3>
                 <button
                   data-testid="close-drawer"
                   onClick={closeDrawer}
                   style={{ background: 'none', border: 'none', color: '#8B949E', fontSize: 22, cursor: 'pointer' }}
                 >
                   ✕
                 </button>
               </div>

               {/* Permisos granulares */}
               <div style={{ marginBottom: 24 }}>
                 <div style={{ fontSize: 12, color: '#8B949E', textTransform: 'uppercase', marginBottom: 12, letterSpacing: 0.8 }}>
                   Permisos
                 </div>
                 {selectedPerms.map((p) => (
                   <div
                     key={p.permission}
                     data-testid={`perm-row-${p.permission}`}
                     style={{
                       display: 'flex',
                       alignItems: 'center',
                       gap: 10,
                       padding: '10px 0',
                       borderBottom: '1px solid #21262D',
                     }}
                   >
                     <span style={{ flex: 1, fontSize: 14 }}>{p.permissionLabel}</span>
                     <span style={{ fontFamily: 'monospace', fontSize: 11, color: '#8B949E' }}>{p.permission}</span>
                     <select
                       data-testid={`zone-select-${p.permission}`}
                       defaultValue={p.zone}
                       style={{
                         background: '#0D1117',
                         border: '1px solid #30363D',
                         color: '#C9D1D9',
                         borderRadius: 4,
                         padding: '4px 8px',
                         fontSize: 12,
                         cursor: 'pointer',
                       }}
                     >
                       <option value="green">🟢 Verde</option>
                       <option value="yellow">🟡 Amarilla</option>
                       <option value="red">🔴 Roja</option>
                     </select>
                   </div>
                 ))}
               </div>

               {/* Historial del nodo */}
               <div style={{ marginBottom: 24 }}>
                 <div style={{ fontSize: 12, color: '#8B949E', textTransform: 'uppercase', marginBottom: 12, letterSpacing: 0.8 }}>
                   Historial del nodo
                 </div>
                 {selectedHistory.length === 0 ? (
                   <div style={{ color: '#8B949E', fontSize: 13 }}>Sin historial.</div>
                 ) : (
                   selectedHistory.slice().reverse().map((entry, i) => (
                     <div key={i} style={{ fontSize: 13, padding: '6px 0', borderBottom: '1px solid #21262D22', display: 'flex', gap: 10 }}>
                       <span style={{ color: '#8B949E', fontFamily: 'monospace' }}>{new Date(entry.timestamp).toLocaleTimeString()}</span>
                       <span style={{ flex: 1 }}>{entry.permissionLabel}</span>
                       <span>{entry.result === 'allowed' ? '✅' : '❌'}</span>
                     </div>
                   ))
                 )}
               </div>

               {/* Botón revocar todo */}
               <button
                 data-testid="revoke-all-btn"
                 onClick={() => {
                   selectedPerms.forEach((p) => denyPermission(selectedNodeId, p.permission))
                   closeDrawer()
                 }}
                 style={{
                   width: '100%',
                   background: '#1A0A0A',
                   border: '1px solid #FF4444',
                   color: '#FF6B6B',
                   borderRadius: 6,
                   padding: '11px',
                   fontWeight: 600,
                   cursor: 'pointer',
                   fontSize: 14,
                 }}
               >
                 🚫 Revocar todos los permisos
               </button>
             </div>
           </>
         )}
       </div>
     )
   }

3. Crear archivo frontend/src/components/security/KillSwitchOverlay.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/security/KillSwitchOverlay.tsx
   Contenido:

   /**
    * YeyoOS — KillSwitchOverlay
    * Micro-fase 3.21 — Capa 3: Cuerpo
    *
    * Overlay visual del Kill Switch (Ctrl+Alt+K).
    * Se registra ANTES que cualquier otro componente en el árbol React.
    * Borde rojo fijo (no pulsa), overlay negro semitransparente, ⛔ SISTEMA EN PAUSA.
    */

   import React, { useEffect, useCallback } from 'react'
   import { useSecurityStore } from '../../stores/securityStore'

   export function KillSwitchOverlay() {
     const { killSwitchActive, toggleKillSwitch, cancelledTasks, suspendedProcesses } = useSecurityStore()

     // CRÍTICO: registrar Ctrl+Alt+K con capture=true, antes que cualquier otro listener
     const handleKeyDown = useCallback(
       (e: KeyboardEvent) => {
         if (e.ctrlKey && e.altKey && e.key === 'k') {
           e.preventDefault()
           e.stopImmediatePropagation()
           toggleKillSwitch()
         }
       },
       [toggleKillSwitch]
     )

     useEffect(() => {
       // capture: true asegura que este listener se dispara PRIMERO
       window.addEventListener('keydown', handleKeyDown, { capture: true })
       return () => window.removeEventListener('keydown', handleKeyDown, { capture: true })
     }, [handleKeyDown])

     if (!killSwitchActive) return null

     return (
       <>
         <style>{`
           @keyframes kill-border-pulse {
             0%, 100% { opacity: 1; }
             50% { opacity: 0.6; }
           }
         `}</style>

         {/* Borde rojo fijo alrededor de toda la pantalla */}
         <div
           data-testid="kill-switch-border"
           style={{
             position: 'fixed',
             inset: 0,
             pointerEvents: 'none',
             zIndex: 9998,
             boxShadow: 'inset 0 0 0 5px #FF1744',
             // Borde fijo, sin pulso
           }}
         />

         {/* Overlay semitransparente */}
         <div
           data-testid="kill-switch-overlay"
           style={{
             position: 'fixed',
             inset: 0,
             background: 'rgba(0,0,0,0.82)',
             zIndex: 9999,
             display: 'flex',
             flexDirection: 'column',
             alignItems: 'center',
             justifyContent: 'center',
             fontFamily: 'Inter, system-ui, sans-serif',
             color: '#fff',
             gap: 20,
           }}
         >
           {/* Icono y título */}
           <div style={{ textAlign: 'center' }}>
             <div style={{ fontSize: 72, marginBottom: 12 }}>⛔</div>
             <div
               data-testid="kill-switch-title"
               style={{
                 fontSize: 28,
                 fontWeight: 800,
                 letterSpacing: 4,
                 color: '#FF1744',
                 textTransform: 'uppercase',
               }}
             >
               SISTEMA EN PAUSA
             </div>
           </div>

           {/* Contadores */}
           <div
             data-testid="kill-switch-counters"
             style={{
               display: 'flex',
               gap: 32,
               background: '#1A0A0A',
               border: '1px solid #FF174444',
               borderRadius: 10,
               padding: '16px 32px',
             }}
           >
             <div style={{ textAlign: 'center' }}>
               <div style={{ fontSize: 28, fontWeight: 800, color: '#FF6B6B' }}>{cancelledTasks}</div>
               <div style={{ fontSize: 12, color: '#8B949E', marginTop: 4 }}>Tareas canceladas</div>
             </div>
             <div style={{ width: 1, background: '#FF174433' }} />
             <div style={{ textAlign: 'center' }}>
               <div style={{ fontSize: 28, fontWeight: 800, color: '#FF6B6B' }}>{suspendedProcesses}</div>
               <div style={{ fontSize: 12, color: '#8B949E', marginTop: 4 }}>Procesos suspendidos</div>
             </div>
           </div>

           {/* Botones */}
           <div style={{ display: 'flex', gap: 12, marginTop: 8 }}>
             <button
               data-testid="resume-btn"
               onClick={toggleKillSwitch}
               style={{
                 background: '#FF1744',
                 border: 'none',
                 color: '#fff',
                 borderRadius: 8,
                 padding: '13px 32px',
                 fontWeight: 700,
                 fontSize: 15,
                 cursor: 'pointer',
                 letterSpacing: 0.5,
               }}
             >
               ▶ Reanudar
             </button>
             <button
               data-testid="view-activity-btn"
               onClick={() => {/* abre log de actividad */}}
               style={{
                 background: 'transparent',
                 border: '1px solid #30363D',
                 color: '#C9D1D9',
                 borderRadius: 8,
                 padding: '13px 24px',
                 fontWeight: 500,
                 fontSize: 15,
                 cursor: 'pointer',
               }}
             >
               Ver qué estaba haciendo
             </button>
           </div>

           <div style={{ fontSize: 13, color: '#8B949E', marginTop: 4 }}>
             Ctrl+Alt+K para reanudar
           </div>
         </div>
       </>
     )
   }

4. Crear archivo frontend/src/stores/securityStore.ts:

   Ruta: ~/yeyo-os/frontend/src/stores/securityStore.ts
   Contenido:

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

5. Crear archivo src/security/permission_service.py:

   Ruta: ~/yeyo-os/src/security/permission_service.py
   Contenido:

   """
   YeyoOS — PermissionService
   Micro-fase 3.21 — Capa 3: Cuerpo

   Servicio de permisos con tres zonas de riesgo:
   - Verde: auto-aprueba silenciosamente y loguea.
   - Amarilla/Roja: emite evento WebSocket al frontend y espera respuesta
     (asyncio.Event con timeout de 60 segundos).
   - Timeout → retorna denegado por seguridad.
   """

   from __future__ import annotations

   import asyncio
   import logging
   from dataclasses import dataclass, field
   from enum import Enum
   from typing import Optional, Dict
   import time

   logger = logging.getLogger(__name__)


   class PermissionZone(str, Enum):
       GREEN = "green"
       YELLOW = "yellow"
       RED = "red"


   @dataclass
   class PackageInfo:
       name: str
       origin: str
       size: str


   @dataclass
   class PermissionRequest:
       node_id: str
       permission: str
       permission_label: str
       zone: PermissionZone
       task_description: str
       package_info: Optional[PackageInfo] = None
       request_id: str = field(default_factory=lambda: str(time.time_ns()))


   @dataclass
   class PermissionDecision:
       allowed: bool
       remember: bool
       timestamp: float = field(default_factory=time.time)
       request_id: str = ""


   class PermissionService:
       """
       Servicio central de permisos. Instancia única (singleton) compartida
       entre el endpoint WebSocket y los nodos que solicitan permisos.
       """

       TIMEOUT_SECONDS = 60.0

       def __init__(self) -> None:
           self._pending: Dict[str, asyncio.Event] = {}
           self._decisions: Dict[str, PermissionDecision] = {}
           self._ws_send_callback: Optional[callable] = None

       def set_ws_callback(self, callback: callable) -> None:
           """Registra la función que enviará eventos por WebSocket al frontend."""
           self._ws_send_callback = callback

       async def request(self, req: PermissionRequest) -> PermissionDecision:
           """
           Procesa una solicitud de permiso según la zona:
           - Verde → auto-aprueba inmediatamente.
           - Amarilla/Roja → espera decisión del frontend via WebSocket.
           """
           if req.zone == PermissionZone.GREEN:
               logger.info(f"[security] AUTO-ALLOW {req.node_id}:{req.permission}")
               decision = PermissionDecision(
                   allowed=True,
                   remember=True,
                   request_id=req.request_id,
               )
               return decision

           # Zona amarilla o roja: emitir al frontend y esperar
           event = asyncio.Event()
           self._pending[req.request_id] = event

           if self._ws_send_callback:
               payload = {
                   "type": "permission_request",
                   "request_id": req.request_id,
                   "node_id": req.node_id,
                   "permission": req.permission,
                   "permission_label": req.permission_label,
                   "zone": req.zone.value,
                   "task_description": req.task_description,
                   "package_info": {
                       "name": req.package_info.name,
                       "origin": req.package_info.origin,
                       "size": req.package_info.size,
                   } if req.package_info else None,
               }
               try:
                   await self._ws_send_callback(payload)
               except Exception as e:
                   logger.error(f"[security] WS send error: {e}")
                   self._pending.pop(req.request_id, None)
                   return PermissionDecision(
                       allowed=False, remember=False, request_id=req.request_id
                   )

           logger.info(f"[security] WAITING {req.node_id}:{req.permission} (zone={req.zone.value})")

           try:
               await asyncio.wait_for(event.wait(), timeout=self.TIMEOUT_SECONDS)
               decision = self._decisions.pop(req.request_id, None)
               if decision:
                   logger.info(
                       f"[security] DECISION {req.node_id}:{req.permission} "
                       f"allowed={decision.allowed} remember={decision.remember}"
                   )
                   return decision
           except asyncio.TimeoutError:
               logger.warning(
                   f"[security] TIMEOUT {req.node_id}:{req.permission} → denied"
               )
           finally:
               self._pending.pop(req.request_id, None)

           return PermissionDecision(allowed=False, remember=False, request_id=req.request_id)

       def resolve(self, request_id: str, allowed: bool, remember: bool) -> bool:
           """
           Recibe la decisión del frontend. Llamado desde el WebSocket handler.
           Retorna True si había una solicitud pendiente, False si no.
           """
           event = self._pending.get(request_id)
           if not event:
               logger.warning(f"[security] resolve: no pending request_id={request_id}")
               return False

           self._decisions[request_id] = PermissionDecision(
               allowed=allowed,
               remember=remember,
               request_id=request_id,
           )
           event.set()
           return True


   # Singleton global
   permission_service = PermissionService()

6. Crear archivo src/api/security_ws.py:

   Ruta: ~/yeyo-os/src/api/security_ws.py
   Contenido:

   """
   YeyoOS — Security WebSocket Endpoint
   Micro-fase 3.21 — Capa 3: Cuerpo

   WebSocket /ws/security:
   - Emite eventos {type: "permission_request", ...} al frontend.
   - Recibe decisiones {type: "permission_response", request_id, allowed, remember}.
   - Múltiples clientes soportados (broadcast a todos los conectados).
   """

   from __future__ import annotations

   import asyncio
   import json
   import logging
   from typing import Set

   from fastapi import APIRouter, WebSocket, WebSocketDisconnect

   from src.security.permission_service import permission_service

   logger = logging.getLogger(__name__)

   router = APIRouter(tags=["security"])

   # Conjunto de conexiones activas
   _connections: Set[WebSocket] = set()


   async def _broadcast(payload: dict) -> None:
       """Envía un evento a todos los clientes WebSocket conectados."""
       if not _connections:
           logger.warning("[security_ws] broadcast: no clients connected")
           return
       message = json.dumps(payload)
       dead: Set[WebSocket] = set()
       for ws in _connections.copy():
           try:
               await ws.send_text(message)
           except Exception:
               dead.add(ws)
       for ws in dead:
           _connections.discard(ws)


   # Registrar el callback de broadcast en el servicio de permisos
   permission_service.set_ws_callback(_broadcast)


   @router.websocket("/ws/security")
   async def security_websocket(websocket: WebSocket) -> None:
       await websocket.accept()
       _connections.add(websocket)
       logger.info(f"[security_ws] client connected. total={len(_connections)}")

       try:
           while True:
               raw = await websocket.receive_text()
               try:
                   data = json.loads(raw)
               except json.JSONDecodeError:
                   logger.warning(f"[security_ws] invalid JSON: {raw[:200]}")
                   continue

               msg_type = data.get("type")

               if msg_type == "permission_response":
                   request_id = data.get("request_id", "")
                   allowed = bool(data.get("allowed", False))
                   remember = bool(data.get("remember", False))
                   resolved = permission_service.resolve(request_id, allowed, remember)
                   if not resolved:
                       logger.warning(f"[security_ws] unknown request_id={request_id}")

               elif msg_type == "ping":
                   await websocket.send_text(json.dumps({"type": "pong"}))

               else:
                   logger.debug(f"[security_ws] unhandled type={msg_type}")

       except WebSocketDisconnect:
           logger.info("[security_ws] client disconnected")
       finally:
           _connections.discard(websocket)

7. Crear archivo frontend/src/__tests__/security/PermissionAlert.test.tsx:

   Ruta: ~/yeyo-os/frontend/src/__tests__/security/PermissionAlert.test.tsx
   Contenido:

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

8. Crear archivo frontend/src/__tests__/security/SecurityDashboard.test.tsx:

   Ruta: ~/yeyo-os/frontend/src/__tests__/security/SecurityDashboard.test.tsx
   Contenido:

   /**
    * Tests para SecurityDashboard — Micro-fase 3.21
    */

   import React from 'react'
   import { render, screen, fireEvent } from '@testing-library/react'
   import { SecurityDashboard } from '../../components/security/SecurityDashboard'
   import { useSecurityStore } from '../../stores/securityStore'

   // Reset store antes de cada test
   beforeEach(() => {
     useSecurityStore.setState({
       permissions: new Map(),
       permissionsArray: [],
       history: [],
       killSwitchActive: false,
       cancelledTasks: 0,
       suspendedProcesses: 0,
     })
   })

   describe('SecurityDashboard', () => {
     it('renderiza el dashboard', () => {
       render(<SecurityDashboard />)
       expect(screen.getByTestId('security-dashboard')).toBeInTheDocument()
     })

     it('muestra 3 cards de resumen', () => {
       render(<SecurityDashboard />)
       expect(screen.getByTestId('summary-cards')).toBeInTheDocument()
     })

     it('muestra contadores en 0 cuando no hay actividad', () => {
       render(<SecurityDashboard />)
       // Los contadores están en las cards
       const cards = screen.getAllByText('0')
       expect(cards.length).toBeGreaterThanOrEqual(2)
     })

     it('muestra historial de accesos cuando hay entradas', () => {
       useSecurityStore.setState({
         history: [
           {
             nodeId: 'nodo-chat',
             permission: 'fs.read',
             permissionLabel: 'Leer archivos',
             zone: 'yellow',
             result: 'allowed',
             timestamp: Date.now(),
           },
         ],
       } as any)
       render(<SecurityDashboard />)
       expect(screen.getByTestId('access-history')).toBeInTheDocument()
       expect(screen.getAllByTestId('history-entry').length).toBe(1)
     })

     it('muestra lista de nodos cuando hay permisos registrados', () => {
       const perms = new Map()
       perms.set('nodo-imagen', [
         {
           permission: 'gpu.compute',
           permissionLabel: 'Usar GPU',
           zone: 'yellow',
           remember: false,
         },
       ])
       useSecurityStore.setState({ permissions: perms } as any)
       render(<SecurityDashboard />)
       expect(screen.getByTestId('node-row-nodo-imagen')).toBeInTheDocument()
     })

     it('abre drawer al hacer click en un nodo', () => {
       const perms = new Map()
       perms.set('nodo-video', [
         {
           permission: 'ffmpeg.exec',
           permissionLabel: 'Ejecutar FFmpeg',
           zone: 'red',
           remember: false,
         },
       ])
       useSecurityStore.setState({ permissions: perms } as any)
       render(<SecurityDashboard />)
       fireEvent.click(screen.getByTestId('node-row-nodo-video'))
       expect(screen.getByTestId('node-drawer')).toBeInTheDocument()
     })

     it('cierra drawer al hacer click en la X', () => {
       const perms = new Map()
       perms.set('nodo-code', [
         { permission: 'sandbox.exec', permissionLabel: 'Ejecutar sandbox', zone: 'red', remember: false },
       ])
       useSecurityStore.setState({ permissions: perms } as any)
       render(<SecurityDashboard />)
       fireEvent.click(screen.getByTestId('node-row-nodo-code'))
       expect(screen.getByTestId('node-drawer')).toBeInTheDocument()
       fireEvent.click(screen.getByTestId('close-drawer'))
       expect(screen.queryByTestId('node-drawer')).not.toBeInTheDocument()
     })
   })

9. Crear archivo frontend/src/__tests__/security/KillSwitch.test.tsx:

   Ruta: ~/yeyo-os/frontend/src/__tests__/security/KillSwitch.test.tsx
   Contenido:

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

10. Crear archivo tests/test_permission_service.py:

    Ruta: ~/yeyo-os/tests/test_permission_service.py
    Contenido:

    """
    Tests para PermissionService — Micro-fase 3.21
    """

    import asyncio
    import pytest

    from src.security.permission_service import (
        PermissionService,
        PermissionRequest,
        PermissionZone,
        PackageInfo,
    )


    @pytest.fixture
    def service():
        """Instancia fresca de PermissionService por test."""
        return PermissionService()


    @pytest.mark.asyncio
    async def test_zona_verde_auto_aprueba(service):
        """Zona verde siempre retorna allowed=True sin esperar."""
        req = PermissionRequest(
            node_id="nodo-chat",
            permission="fs.read",
            permission_label="Leer archivos",
            zone=PermissionZone.GREEN,
            task_description="Leer configuración",
        )
        decision = await service.request(req)
        assert decision.allowed is True
        assert decision.remember is True


    @pytest.mark.asyncio
    async def test_zona_verde_no_espera_ws(service):
        """Zona verde retorna inmediatamente aunque no haya WS callback."""
        service.set_ws_callback(None)
        req = PermissionRequest(
            node_id="nodo-img",
            permission="gpu.compute",
            permission_label="GPU",
            zone=PermissionZone.GREEN,
            task_description="Generar imagen",
        )
        # Debe completarse en < 0.1s
        decision = await asyncio.wait_for(service.request(req), timeout=0.1)
        assert decision.allowed is True


    @pytest.mark.asyncio
    async def test_zona_amarilla_espera_respuesta(service):
        """Zona amarilla espera hasta que se llame resolve()."""
        sent_payloads = []

        async def mock_ws(payload):
            sent_payloads.append(payload)

        service.set_ws_callback(mock_ws)

        req = PermissionRequest(
            node_id="nodo-code",
            permission="sandbox.exec",
            permission_label="Ejecutar sandbox",
            zone=PermissionZone.YELLOW,
            task_description="Correr código del usuario",
        )

        # Lanzar request en background
        task = asyncio.create_task(service.request(req))
        await asyncio.sleep(0.05)  # Dar tiempo al task para iniciar

        # Verificar que se envió el evento WS
        assert len(sent_payloads) == 1
        assert sent_payloads[0]["type"] == "permission_request"
        assert sent_payloads[0]["zone"] == "yellow"

        # Resolver desde "frontend"
        service.resolve(req.request_id, allowed=True, remember=False)

        decision = await asyncio.wait_for(task, timeout=1.0)
        assert decision.allowed is True
        assert decision.remember is False


    @pytest.mark.asyncio
    async def test_timeout_retorna_denied(service):
        """Si no hay respuesta en timeout, retorna denegado."""
        async def mock_ws(payload):
            pass  # No resuelve nunca

        service.set_ws_callback(mock_ws)
        service.TIMEOUT_SECONDS = 0.1  # Reducir timeout para el test

        req = PermissionRequest(
            node_id="nodo-test",
            permission="net.external",
            permission_label="Red externa",
            zone=PermissionZone.YELLOW,
            task_description="Llamada a API externa",
        )

        decision = await service.request(req)
        assert decision.allowed is False


    @pytest.mark.asyncio
    async def test_zona_roja_llega_al_frontend(service):
        """Zona roja también emite evento WS con zone=red."""
        sent = []

        async def mock_ws(payload):
            sent.append(payload)

        service.set_ws_callback(mock_ws)

        req = PermissionRequest(
            node_id="nodo-files",
            permission="fs.delete_all",
            permission_label="Borrar todo",
            zone=PermissionZone.RED,
            task_description="Limpiar directorio",
            package_info=PackageInfo(name="rm-tool", origin="pypi", size="2KB"),
        )

        task = asyncio.create_task(service.request(req))
        await asyncio.sleep(0.05)

        assert len(sent) == 1
        assert sent[0]["zone"] == "red"
        assert sent[0]["package_info"]["name"] == "rm-tool"

        service.resolve(req.request_id, allowed=False, remember=False)
        decision = await asyncio.wait_for(task, timeout=1.0)
        assert decision.allowed is False


    def test_resolve_request_inexistente(service):
        """resolve() retorna False para request_id desconocido."""
        result = service.resolve("id-que-no-existe", allowed=True, remember=False)
        assert result is False

VERIFICAR:
- [ ] PermissionAlert.tsx: zona verde no renderiza, zona amarilla muestra popup+chat+4 botones, zona roja muestra badge+advertencia+campo confirmo
- [ ] "confirmo" (case-insensitive) habilita el botón de zona roja
- [ ] SecurityDashboard.tsx: 3 cards resumen, lista de nodos, historial 24h, drawer lateral al click
- [ ] KillSwitchOverlay.tsx: se registra con capture=true, visible solo cuando killSwitchActive=true, Ctrl+Alt+K lo activa
- [ ] securityStore.ts: Map persiste via permissionsArray, historial capped a 500 entradas
- [ ] permission_service.py: zona verde auto-aprueba, zona amarilla/roja espera WS, timeout=60s retorna denied
- [ ] security_ws.py: emite permission_request al frontend, recibe permission_response y llama resolve()
- [ ] Tests Jest pasan: PermissionAlert (12 tests), SecurityDashboard (6 tests), KillSwitch (8 tests)
- [ ] Tests pytest pasan: test_permission_service.py (6 tests)

SI FALLA:
- Zustand Map no persiste: el onRehydrateStorage reconstruye el Map desde permissionsArray, verificar que se llama correctamente
- Tests de Kill Switch fallan con keyDown: usar act() alrededor de fireEvent.keyDown(window, ...)
- "confirmo" case-insensitive: el check usa .toLowerCase() antes de comparar
- asyncio.TimeoutError en tests: asignar service.TIMEOUT_SECONDS = 0.1 dentro del test para acelerar
- WebSocket broadcast a 0 clientes: el log de warning es esperado, no es error
- CSS animations no visibles en tests: los tests verifican data-testid y atributos, no animaciones visuales

NO HACER:
- No usar WebGL para las animaciones de borde (CSS puro es suficiente y más eficiente)
- No bloquear el hilo principal esperando decisiones de permisos (siempre asyncio.Event)
- No persistir el historial en localStorage (demasiado voluminoso) — solo en memoria
- No matar procesos cuando el Kill Switch activa: PAUSA, nunca matar
- No requerir "confirmo" exacto con mayúsculas — case-insensitive para UX

GATE: Zona amarilla muestra popup con chat inline (máx 3 mensajes), zona roja requiere escribir "confirmo" y habilita el botón, Kill Switch muestra overlay negro con borde rojo y contadores, dashboard muestra historial completo de accesos con ✅/❌. Todos los tests pasan.
```
