## ═══════════════════════════════════════
## MICRO-FASE 3.20 — Node App Layout: Topbar + Sidebar + Layouts
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 3.20-1 [VSCODE] — Topbar, Hub Sidebar colapsable y 4 layouts de nodos con chat fijo a la derecha

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 3.20 de Capa 3 (Cuerpo): implementar el layout principal de la app — Topbar de 48px, Hub Sidebar colapsable, y 4 layouts de nodos (Image, Video, Code, Automation) con chat siempre a la derecha.

CONTEXTO:
- Micro-fase 3.18–3.19 completadas: GridBackground, Onboarding, FreeCanvas, VignetteOverlay
- Stack: React + TypeScript + CSS-in-JS (style props) — No Tailwind, no CSS modules externos
- El Kill Switch (Ctrl+Alt+K) ya está registrado en Capa 3 — el Topbar lo referencia pero NO lo reimplementa
- Monaco Editor: usar @monaco-editor/react
- React Flow: para el Automation Node pipeline visual
- Regla de oro del layout: Chat SIEMPRE a la derecha (300px), resultado SIEMPRE visible
- El fondo Double Grid (GridBackground) es visible detrás de todos los workspaces al 50% opacidad

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo frontend/src/components/layout/Topbar.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/layout/Topbar.tsx
   Contenido:

   /**
    * YeyoOS — Topbar
    * Micro-fase 3.20 — Capa 3: Cuerpo
    *
    * Barra superior siempre visible (48px).
    * Contiene: toggle Hub Sidebar, tabs de nodos abiertos,
    * indicador de pipelines activos, y Kill Switch.
    *
    * REGLA: Kill Switch es SAGRADO — siempre visible, siempre funcional.
    */

   import React, { useCallback } from 'react'
   import { useHubStore } from '../../stores/hubStore'
   import { useSystemStore } from '../../stores/systemStore'

   export interface TabInfo {
     id: string
     label: string
     icono?: string
     activo: boolean
   }

   export interface TopbarProps {
     tabs: TabInfo[]
     onTabClick: (tabId: string) => void
     onTabClose: (tabId: string) => void
     onToggleSidebar: () => void
     sidebarOpen: boolean
   }

   const MAX_TABS = 5

   const TOPBAR_STYLES: React.CSSProperties = {
     display: 'flex',
     alignItems: 'center',
     height: 48,
     backgroundColor: '#0A0E1A',
     borderBottom: '1px solid #1E3A5F',
     padding: '0 12px',
     gap: 8,
     userSelect: 'none',
     flexShrink: 0,
     zIndex: 100,
   }

   export function Topbar({ tabs, onTabClick, onTabClose, onToggleSidebar, sidebarOpen }: TopbarProps) {
     const pipelineActivo = useHubStore((s) => s.pipelineActivo)
     const activarKillSwitch = useSystemStore((s) => s.activarKillSwitch)

     const handleKillSwitch = useCallback(() => {
       activarKillSwitch()
     }, [activarKillSwitch])

     const visibleTabs = tabs.slice(0, MAX_TABS)

     return (
       <header data-testid="topbar" style={TOPBAR_STYLES} role="banner">
         {/* Toggle Hub Sidebar */}
         <button
           data-testid="toggle-sidebar-btn"
           onClick={onToggleSidebar}
           aria-label={sidebarOpen ? 'Cerrar Hub' : 'Abrir Hub'}
           aria-expanded={sidebarOpen}
           style={{
             background: sidebarOpen ? 'rgba(79,195,247,0.15)' : 'transparent',
             border: '1px solid #1E3A5F',
             color: '#90CAF9',
             borderRadius: 6,
             padding: '4px 10px',
             cursor: 'pointer',
             fontSize: 14,
             display: 'flex',
             alignItems: 'center',
             gap: 6,
             whiteSpace: 'nowrap',
           }}
         >
           ≡ Hub
         </button>

         {/* Tabs de nodos abiertos */}
         <div
           data-testid="tabs-container"
           style={{
             display: 'flex',
             gap: 4,
             flex: 1,
             overflow: 'hidden',
             alignItems: 'center',
           }}
         >
           {visibleTabs.map((tab) => (
             <div
               key={tab.id}
               data-testid={`tab-${tab.id}`}
               data-active={tab.activo}
               style={{
                 display: 'flex',
                 alignItems: 'center',
                 gap: 6,
                 padding: '4px 10px',
                 backgroundColor: tab.activo ? '#1E3A5F' : 'transparent',
                 border: `1px solid ${tab.activo ? '#4FC3F7' : '#1E3A5F'}`,
                 borderRadius: 6,
                 cursor: 'pointer',
                 color: tab.activo ? '#E0F7FA' : '#90CAF9',
                 fontSize: 13,
                 maxWidth: 140,
                 overflow: 'hidden',
               }}
             >
               <span onClick={() => onTabClick(tab.id)} style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
                 {tab.icono && <span style={{ marginRight: 4 }}>{tab.icono}</span>}
                 {tab.label}
               </span>
               <button
                 data-testid={`close-tab-${tab.id}`}
                 onClick={(e) => { e.stopPropagation(); onTabClose(tab.id) }}
                 aria-label={`Cerrar ${tab.label}`}
                 style={{
                   background: 'transparent',
                   border: 'none',
                   color: '#607D8B',
                   cursor: 'pointer',
                   padding: 0,
                   fontSize: 12,
                   lineHeight: 1,
                   flexShrink: 0,
                 }}
               >
                 ✕
               </button>
             </div>
           ))}
           {tabs.length > MAX_TABS && (
             <span style={{ color: '#607D8B', fontSize: 12 }}>+{tabs.length - MAX_TABS}</span>
           )}
         </div>

         {/* Indicador de pipelines activos */}
         <div
           data-testid="pipeline-indicator"
           data-pipeline-activo={pipelineActivo}
           title={pipelineActivo ? 'Pipeline ejecutándose' : 'Sin pipelines activos'}
           style={{
             fontSize: 18,
             animation: pipelineActivo ? 'pulse 1s ease-in-out infinite' : 'none',
             opacity: pipelineActivo ? 1 : 0.3,
             cursor: 'default',
           }}
         >
           ⚡
         </div>

         {/* Kill Switch */}
         <button
           data-testid="kill-switch-btn"
           onClick={handleKillSwitch}
           aria-label="Kill Switch — detener toda actividad IA"
           style={{
             backgroundColor: '#B71C1C',
             border: '1px solid #E53935',
             color: '#FFCDD2',
             borderRadius: 6,
             padding: '4px 12px',
             cursor: 'pointer',
             fontSize: 12,
             fontWeight: 700,
             letterSpacing: '0.5px',
             flexShrink: 0,
           }}
         >
           ■ STOP
         </button>
       </header>
     )
   }

2. Crear archivo frontend/src/components/layout/HubSidebar.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/layout/HubSidebar.tsx
   Contenido:

   /**
    * YeyoOS — HubSidebar
    * Micro-fase 3.20 — Capa 3: Cuerpo
    *
    * Sidebar izquierdo colapsable con mini-Hub canvas.
    * - 240px abierto / 0px cerrado, transición 300ms
    * - Muestra nodos instalados en miniatura con su estado
    * - Double grid background en miniatura
    * - Click en nodo → abre tab en workspace
    */

   import React from 'react'
   import { useHubStore } from '../../stores/hubStore'
   import { GridBackground } from '../hub/GridBackground'
   import { VignetteOverlay } from '../hub/VignetteOverlay'

   export interface NodoMiniInfo {
     id: string
     label: string
     icono?: string
     estado?: 'idle' | 'activo' | 'error'
   }

   export interface HubSidebarProps {
     open: boolean
     nodos: NodoMiniInfo[]
     onNodoClick: (nodeId: string) => void
   }

   const ESTADO_COLOR: Record<string, string> = {
     idle: '#1565C0',
     activo: '#4FC3F7',
     error: '#F44336',
   }

   export function HubSidebar({ open, nodos, onNodoClick }: HubSidebarProps) {
     const pipelineActivo = useHubStore((s) => s.pipelineActivo)
     const nodosEnPipeline = useHubStore((s) => s.nodosEnPipeline)

     return (
       <aside
         data-testid="hub-sidebar"
         data-open={open}
         style={{
           width: open ? 240 : 0,
           minWidth: open ? 240 : 0,
           maxWidth: open ? 240 : 0,
           overflow: 'hidden',
           transition: 'width 300ms ease, min-width 300ms ease, max-width 300ms ease',
           backgroundColor: '#060B18',
           borderRight: open ? '1px solid #1E3A5F' : 'none',
           display: 'flex',
           flexDirection: 'column',
           position: 'relative',
           flexShrink: 0,
         }}
         aria-hidden={!open}
       >
         {open && (
           <>
             {/* Mini Hub canvas con double grid */}
             <div style={{ position: 'relative', height: 180, overflow: 'hidden' }}>
               <GridBackground saturation={1.0} style={{ opacity: 0.6 }} />
               <VignetteOverlay visible={pipelineActivo} maxOpacity={0.25} />
               <div style={{ position: 'relative', zIndex: 2, padding: 12 }}>
                 <div style={{ color: '#4FC3F7', fontSize: 11, fontWeight: 600, marginBottom: 8, letterSpacing: '1px', textTransform: 'uppercase' }}>
                   Hub
                 </div>
                 {/* Representación visual mínima del hub */}
                 <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                   {nodos.map((n) => {
                     const enPipeline = nodosEnPipeline.includes(n.id)
                     const estado = enPipeline ? 'activo' : (n.estado ?? 'idle')
                     return (
                       <button
                         key={n.id}
                         data-testid={`mini-node-${n.id}`}
                         data-estado={estado}
                         onClick={() => onNodoClick(n.id)}
                         title={n.label}
                         style={{
                           width: 36,
                           height: 36,
                           borderRadius: '50%',
                           backgroundColor: ESTADO_COLOR[estado] ?? ESTADO_COLOR.idle,
                           border: `2px solid ${enPipeline ? '#4FC3F7' : '#1E3A5F'}`,
                           cursor: 'pointer',
                           display: 'flex',
                           alignItems: 'center',
                           justifyContent: 'center',
                           fontSize: 16,
                           boxShadow: enPipeline ? '0 0 12px rgba(79,195,247,0.5)' : 'none',
                           transition: 'all 300ms ease',
                         }}
                       >
                         {n.icono ?? '◎'}
                       </button>
                     )
                   })}
                 </div>
               </div>
             </div>

             {/* Lista de nodos instalados */}
             <div style={{ flex: 1, overflowY: 'auto', padding: '8px 0' }}>
               {nodos.map((n) => {
                 const enPipeline = nodosEnPipeline.includes(n.id)
                 const estado = enPipeline ? 'activo' : (n.estado ?? 'idle')
                 return (
                   <button
                     key={n.id}
                     data-testid={`sidebar-node-${n.id}`}
                     onClick={() => onNodoClick(n.id)}
                     style={{
                       display: 'flex',
                       alignItems: 'center',
                       gap: 10,
                       width: '100%',
                       padding: '8px 16px',
                       background: 'transparent',
                       border: 'none',
                       borderBottom: '1px solid #0D1B2A',
                       cursor: 'pointer',
                       color: '#B0BEC5',
                       fontSize: 13,
                       textAlign: 'left',
                     }}
                   >
                     <span style={{
                       width: 8, height: 8, borderRadius: '50%',
                       backgroundColor: ESTADO_COLOR[estado],
                       flexShrink: 0,
                     }} />
                     <span style={{ fontSize: 16 }}>{n.icono ?? '◎'}</span>
                     <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                       {n.label}
                     </span>
                   </button>
                 )
               })}
             </div>
           </>
         )}
       </aside>
     )
   }

3. Crear archivo frontend/src/components/nodes/ImageNodeLayout.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/nodes/ImageNodeLayout.tsx
   Contenido:

   /**
    * YeyoOS — ImageNodeLayout
    * Micro-fase 3.20 — Capa 3: Cuerpo
    *
    * Layout del nodo de generación de imágenes.
    * [Controles (izq 220px)] | [Galería (centro flex)] | [Chat IA (der 300px)]
    *
    * REGLA: Chat SIEMPRE a la derecha. Resultado (galería) SIEMPRE visible.
    */

   import React, { useState } from 'react'
   import { GridBackground } from '../hub/GridBackground'

   export interface ImageGenerada {
     id: string
     url: string
     prompt: string
     modelo: string
     timestamp: number
   }

   export interface ImageNodeLayoutProps {
     imagenes?: ImageGenerada[]
     onGenerar?: (prompt: string, modelo: string, opciones: ImageOpciones) => void
     chatMessages?: ChatMessage[]
     onChatSend?: (mensaje: string) => void
   }

   export interface ImageOpciones {
     resolucion: string
     estilo: string
     seed: number
   }

   export interface ChatMessage {
     id: string
     role: 'user' | 'assistant'
     content: string
   }

   export function ImageNodeLayout({
     imagenes = [],
     onGenerar,
     chatMessages = [],
     onChatSend,
   }: ImageNodeLayoutProps) {
     const [prompt, setPrompt] = useState('')
     const [modelo, setModelo] = useState('sdxl')
     const [resolucion, setResolucion] = useState('1024x1024')
     const [estilo, setEstilo] = useState('photorealistic')
     const [seed, setSeed] = useState(-1)
     const [chatInput, setChatInput] = useState('')

     const handleGenerar = () => {
       if (!prompt.trim()) return
       onGenerar?.(prompt, modelo, { resolucion, estilo, seed })
     }

     const handleChatSend = (e: React.FormEvent) => {
       e.preventDefault()
       if (!chatInput.trim()) return
       onChatSend?.(chatInput)
       setChatInput('')
     }

     return (
       <div
         data-testid="image-node-layout"
         style={{
           display: 'flex',
           height: '100%',
           position: 'relative',
           overflow: 'hidden',
           backgroundColor: '#060B18',
         }}
       >
         {/* Double Grid Background sutil */}
         <GridBackground saturation={1.0} style={{ opacity: 0.5 }} />

         {/* === CONTROLES (izquierda 220px) === */}
         <aside
           data-testid="image-controls"
           style={{
             width: 220,
             flexShrink: 0,
             padding: 16,
             borderRight: '1px solid #1E3A5F',
             display: 'flex',
             flexDirection: 'column',
             gap: 12,
             position: 'relative',
             zIndex: 1,
             overflowY: 'auto',
           }}
         >
           <label style={{ color: '#90CAF9', fontSize: 12 }}>
             Prompt
             <textarea
               data-testid="prompt-textarea"
               value={prompt}
               onChange={(e) => setPrompt(e.target.value)}
               rows={4}
               style={{
                 display: 'block',
                 width: '100%',
                 marginTop: 4,
                 backgroundColor: '#0A0E1A',
                 border: '1px solid #1E3A5F',
                 borderRadius: 4,
                 color: '#E0F7FA',
                 padding: 8,
                 fontSize: 13,
                 resize: 'vertical',
                 fontFamily: 'inherit',
               }}
             />
           </label>

           <label style={{ color: '#90CAF9', fontSize: 12 }}>
             Modelo
             <select
               data-testid="modelo-select"
               value={modelo}
               onChange={(e) => setModelo(e.target.value)}
               style={{
                 display: 'block',
                 width: '100%',
                 marginTop: 4,
                 backgroundColor: '#0A0E1A',
                 border: '1px solid #1E3A5F',
                 color: '#E0F7FA',
                 padding: '6px 8px',
                 borderRadius: 4,
               }}
             >
               <option value="sdxl">SDXL</option>
               <option value="flux">Flux</option>
               <option value="dalle3">DALL-E 3</option>
             </select>
           </label>

           <label style={{ color: '#90CAF9', fontSize: 12 }}>
             Resolución
             <select
               data-testid="resolucion-select"
               value={resolucion}
               onChange={(e) => setResolucion(e.target.value)}
               style={{
                 display: 'block', width: '100%', marginTop: 4,
                 backgroundColor: '#0A0E1A', border: '1px solid #1E3A5F',
                 color: '#E0F7FA', padding: '6px 8px', borderRadius: 4,
               }}
             >
               <option value="512x512">512×512</option>
               <option value="1024x1024">1024×1024</option>
               <option value="1920x1080">1920×1080</option>
             </select>
           </label>

           <label style={{ color: '#90CAF9', fontSize: 12 }}>
             Estilo
             <input
               data-testid="estilo-input"
               value={estilo}
               onChange={(e) => setEstilo(e.target.value)}
               style={{
                 display: 'block', width: '100%', marginTop: 4,
                 backgroundColor: '#0A0E1A', border: '1px solid #1E3A5F',
                 color: '#E0F7FA', padding: '6px 8px', borderRadius: 4,
               }}
             />
           </label>

           <label style={{ color: '#90CAF9', fontSize: 12 }}>
             Seed
             <input
               data-testid="seed-input"
               type="number"
               value={seed}
               onChange={(e) => setSeed(Number(e.target.value))}
               style={{
                 display: 'block', width: '100%', marginTop: 4,
                 backgroundColor: '#0A0E1A', border: '1px solid #1E3A5F',
                 color: '#E0F7FA', padding: '6px 8px', borderRadius: 4,
               }}
             />
           </label>

           <button
             data-testid="generar-btn"
             onClick={handleGenerar}
             style={{
               backgroundColor: '#1565C0',
               border: '1px solid #4FC3F7',
               color: '#E0F7FA',
               borderRadius: 6,
               padding: '8px 0',
               cursor: 'pointer',
               fontWeight: 600,
               fontSize: 14,
               marginTop: 'auto',
             }}
           >
             Generar
           </button>
         </aside>

         {/* === GALERÍA (centro flex) === */}
         <main
           data-testid="gallery-area"
           style={{
             flex: 1,
             padding: 16,
             overflowY: 'auto',
             position: 'relative',
             zIndex: 1,
           }}
         >
           <div
             style={{
               display: 'grid',
               gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
               gap: 12,
             }}
           >
             {imagenes.map((img) => (
               <div
                 key={img.id}
                 data-testid={`imagen-card-${img.id}`}
                 draggable
                 onDragStart={(e) => e.dataTransfer.setData('application/yeyo-image', img.id)}
                 style={{
                   borderRadius: 8,
                   overflow: 'hidden',
                   border: '1px solid #1E3A5F',
                   cursor: 'grab',
                   backgroundColor: '#0A0E1A',
                 }}
               >
                 <img
                   src={img.url}
                   alt={img.prompt}
                   style={{ width: '100%', height: 180, objectFit: 'cover', display: 'block' }}
                 />
                 <div style={{ padding: '6px 8px', fontSize: 11, color: '#607D8B' }}>
                   {img.modelo} • {img.prompt.slice(0, 40)}...
                 </div>
               </div>
             ))}
             {imagenes.length === 0 && (
               <div style={{ color: '#37474F', fontSize: 14, gridColumn: '1/-1', textAlign: 'center', paddingTop: 60 }}>
                 Las imágenes generadas aparecerán aquí
               </div>
             )}
           </div>
         </main>

         {/* === CHAT IA (derecha 300px) — SIEMPRE VISIBLE === */}
         <aside
           data-testid="chat-panel"
           style={{
             width: 300,
             flexShrink: 0,
             borderLeft: '1px solid #1E3A5F',
             display: 'flex',
             flexDirection: 'column',
             position: 'relative',
             zIndex: 1,
           }}
         >
           <div style={{ padding: '12px 16px', borderBottom: '1px solid #1E3A5F', color: '#4FC3F7', fontSize: 12, fontWeight: 600 }}>
             Chat IA
           </div>
           <div
             data-testid="chat-messages"
             style={{ flex: 1, overflowY: 'auto', padding: 12, display: 'flex', flexDirection: 'column', gap: 8 }}
           >
             {chatMessages.map((msg) => (
               <div
                 key={msg.id}
                 data-testid={`chat-msg-${msg.id}`}
                 style={{
                   backgroundColor: msg.role === 'user' ? '#1E3A5F' : '#0A0E1A',
                   borderRadius: 8,
                   padding: '8px 12px',
                   fontSize: 13,
                   color: msg.role === 'user' ? '#E0F7FA' : '#90CAF9',
                   alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                   maxWidth: '90%',
                 }}
               >
                 {msg.content}
               </div>
             ))}
           </div>
           <form onSubmit={handleChatSend} style={{ padding: 12, borderTop: '1px solid #1E3A5F' }}>
             <input
               data-testid="chat-input"
               value={chatInput}
               onChange={(e) => setChatInput(e.target.value)}
               placeholder="Escribe un mensaje..."
               style={{
                 width: '100%',
                 backgroundColor: '#0A0E1A',
                 border: '1px solid #1E3A5F',
                 borderRadius: 6,
                 color: '#E0F7FA',
                 padding: '8px 12px',
                 fontSize: 13,
                 boxSizing: 'border-box',
               }}
             />
           </form>
         </aside>
       </div>
     )
   }

4. Crear archivo frontend/src/components/nodes/VideoNodeLayout.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/nodes/VideoNodeLayout.tsx
   Contenido:

   /**
    * YeyoOS — VideoNodeLayout
    * Micro-fase 3.20 — Capa 3: Cuerpo
    *
    * Layout del nodo de video.
    * [Preview player (top 50%)] | [Chat IA (der 300px, full height)]
    * [Assets panel (izq 180px)] | [Timeline (centro flex, bottom 50%)]
    */

   import React, { useState } from 'react'

   export interface ClipInfo {
     id: string
     nombre: string
     duracion: number  // segundos
     tipo: 'video' | 'audio' | 'imagen'
     url?: string
   }

   export interface VideoNodeLayoutProps {
     clips?: ClipInfo[]
     chatMessages?: Array<{ id: string; role: 'user' | 'assistant'; content: string }>
     onChatSend?: (mensaje: string) => void
     onClipAdd?: (clip: ClipInfo) => void
   }

   export function VideoNodeLayout({
     clips = [],
     chatMessages = [],
     onChatSend,
     onClipAdd,
   }: VideoNodeLayoutProps) {
     const [chatInput, setChatInput] = useState('')
     const [playbackTime, setPlaybackTime] = useState(0)

     const handleChatSend = (e: React.FormEvent) => {
       e.preventDefault()
       if (!chatInput.trim()) return
       onChatSend?.(chatInput)
       setChatInput('')
     }

     const handleDrop = (e: React.DragEvent) => {
       e.preventDefault()
       Array.from(e.dataTransfer.files).forEach((file) => {
         const tipo: ClipInfo['tipo'] = file.type.startsWith('video') ? 'video'
           : file.type.startsWith('audio') ? 'audio' : 'imagen'
         onClipAdd?.({ id: crypto.randomUUID(), nombre: file.name, duracion: 0, tipo })
       })
     }

     return (
       <div
         data-testid="video-node-layout"
         style={{ display: 'flex', height: '100%', backgroundColor: '#060B18' }}
       >
         {/* === ÁREA PRINCIPAL (izquierda + centro) === */}
         <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
           {/* TOP: Preview player + Assets */}
           <div style={{ flex: '0 0 50%', display: 'flex', borderBottom: '1px solid #1E3A5F' }}>
             {/* Assets panel */}
             <aside
               data-testid="assets-panel"
               onDrop={handleDrop}
               onDragOver={(e) => e.preventDefault()}
               style={{
                 width: 180, flexShrink: 0, borderRight: '1px solid #1E3A5F',
                 padding: 12, overflowY: 'auto',
               }}
             >
               <div style={{ color: '#4FC3F7', fontSize: 11, fontWeight: 600, marginBottom: 8, letterSpacing: '1px' }}>
                 ASSETS
               </div>
               <div style={{ fontSize: 11, color: '#37474F', marginBottom: 8 }}>Arrastra archivos aquí</div>
               {clips.map((c) => (
                 <div
                   key={c.id}
                   data-testid={`asset-${c.id}`}
                   draggable
                   onDragStart={(e) => e.dataTransfer.setData('application/yeyo-clip', c.id)}
                   style={{
                     padding: '6px 8px', borderRadius: 4, backgroundColor: '#0A0E1A',
                     border: '1px solid #1E3A5F', marginBottom: 4, cursor: 'grab',
                     fontSize: 12, color: '#B0BEC5',
                   }}
                 >
                   {c.tipo === 'video' ? '🎬' : c.tipo === 'audio' ? '🎵' : '🖼️'} {c.nombre}
                 </div>
               ))}
             </aside>

             {/* Preview player */}
             <div data-testid="preview-player" style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: '#000', position: 'relative' }}>
               <div style={{ color: '#37474F', fontSize: 14 }}>
                 {clips.length === 0 ? '▷  Sin clips en timeline' : '▷  Preview'}
               </div>
             </div>
           </div>

           {/* BOTTOM: Timeline */}
           <div
             data-testid="timeline"
             style={{
               flex: 1, padding: 12, overflowX: 'auto', position: 'relative',
               backgroundColor: '#080D18',
             }}
           >
             {/* Timeline controls */}
             <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
               {['✂️', '➕', '🎵', '📝', '⚙️'].map((icon) => (
                 <button
                   key={icon}
                   data-testid={`timeline-btn-${icon}`}
                   style={{
                     background: 'transparent', border: '1px solid #1E3A5F',
                     borderRadius: 4, padding: '4px 8px', cursor: 'pointer',
                     color: '#90CAF9', fontSize: 16,
                   }}
                 >
                   {icon}
                 </button>
               ))}
             </div>

             {/* Clips en timeline */}
             <div style={{ display: 'flex', gap: 4, height: 60, alignItems: 'center', position: 'relative' }}>
               {clips.filter(c => c.tipo === 'video').map((c, i) => (
                 <div
                   key={c.id}
                   data-testid={`timeline-clip-${c.id}`}
                   draggable
                   style={{
                     height: 48, minWidth: 100, backgroundColor: '#1565C0',
                     borderRadius: 4, border: '1px solid #4FC3F7',
                     display: 'flex', alignItems: 'center', justifyContent: 'center',
                     fontSize: 11, color: '#E0F7FA', cursor: 'grab',
                   }}
                 >
                   {c.nombre.slice(0, 12)}
                 </div>
               ))}
               {clips.length === 0 && (
                 <div style={{ color: '#37474F', fontSize: 12 }}>Arrastra clips al timeline</div>
               )}
             </div>
           </div>
         </div>

         {/* === CHAT IA (derecha 300px, full height) — SIEMPRE VISIBLE === */}
         <aside
           data-testid="chat-panel"
           style={{
             width: 300, flexShrink: 0, borderLeft: '1px solid #1E3A5F',
             display: 'flex', flexDirection: 'column',
           }}
         >
           <div style={{ padding: '12px 16px', borderBottom: '1px solid #1E3A5F', color: '#4FC3F7', fontSize: 12, fontWeight: 600 }}>
             Chat IA
           </div>
           <div data-testid="chat-messages" style={{ flex: 1, overflowY: 'auto', padding: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
             {chatMessages.map((msg) => (
               <div key={msg.id} data-testid={`chat-msg-${msg.id}`} style={{
                 backgroundColor: msg.role === 'user' ? '#1E3A5F' : '#0A0E1A',
                 borderRadius: 8, padding: '8px 12px', fontSize: 13,
                 color: msg.role === 'user' ? '#E0F7FA' : '#90CAF9',
                 alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start', maxWidth: '90%',
               }}>
                 {msg.content}
               </div>
             ))}
           </div>
           <form onSubmit={handleChatSend} style={{ padding: 12, borderTop: '1px solid #1E3A5F' }}>
             <input
               data-testid="chat-input"
               value={chatInput}
               onChange={(e) => setChatInput(e.target.value)}
               placeholder="Escribe un mensaje..."
               style={{
                 width: '100%', backgroundColor: '#0A0E1A', border: '1px solid #1E3A5F',
                 borderRadius: 6, color: '#E0F7FA', padding: '8px 12px',
                 fontSize: 13, boxSizing: 'border-box',
               }}
             />
           </form>
         </aside>
       </div>
     )
   }

5. Crear archivo frontend/src/components/nodes/CodeNodeLayout.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/nodes/CodeNodeLayout.tsx
   Contenido:

   /**
    * YeyoOS — CodeNodeLayout
    * Micro-fase 3.20 — Capa 3: Cuerpo
    *
    * Layout del nodo de código.
    * [File explorer (izq 200px)] | [Monaco editor (centro flex)] | [Chat IA (der 300px)]
    * [Terminal (bottom 180px, collapsable)]
    */

   import React, { useState } from 'react'
   import Editor from '@monaco-editor/react'

   export interface FileNode {
     id: string
     nombre: string
     tipo: 'file' | 'folder'
     children?: FileNode[]
     contenido?: string
   }

   export interface CodeNodeLayoutProps {
     archivos?: FileNode[]
     chatMessages?: Array<{ id: string; role: 'user' | 'assistant'; content: string }>
     onChatSend?: (mensaje: string) => void
     onArchivoSeleccionado?: (archivo: FileNode) => void
     terminalOutput?: string
   }

   export function CodeNodeLayout({
     archivos = [],
     chatMessages = [],
     onChatSend,
     onArchivoSeleccionado,
     terminalOutput = '',
   }: CodeNodeLayoutProps) {
     const [archivoActivo, setArchivoActivo] = useState<FileNode | null>(null)
     const [codigoActivo, setCodigoActivo] = useState('')
     const [terminalVisible, setTerminalVisible] = useState(true)
     const [chatInput, setChatInput] = useState('')

     const handleArchivoClick = (archivo: FileNode) => {
       if (archivo.tipo === 'file') {
         setArchivoActivo(archivo)
         setCodigoActivo(archivo.contenido ?? '')
         onArchivoSeleccionado?.(archivo)
       }
     }

     const handleChatSend = (e: React.FormEvent) => {
       e.preventDefault()
       if (!chatInput.trim()) return
       onChatSend?.(chatInput)
       setChatInput('')
     }

     const renderFileTree = (nodes: FileNode[], depth = 0) =>
       nodes.map((n) => (
         <div key={n.id}>
           <button
             data-testid={`file-${n.id}`}
             onClick={() => handleArchivoClick(n)}
             style={{
               display: 'block', width: '100%', textAlign: 'left',
               background: archivoActivo?.id === n.id ? '#1E3A5F' : 'transparent',
               border: 'none', color: '#B0BEC5', fontSize: 12,
               padding: `4px 8px 4px ${8 + depth * 12}px`, cursor: 'pointer',
             }}
           >
             {n.tipo === 'folder' ? '📁' : '📄'} {n.nombre}
           </button>
           {n.children && renderFileTree(n.children, depth + 1)}
         </div>
       ))

     return (
       <div data-testid="code-node-layout" style={{ display: 'flex', height: '100%', backgroundColor: '#060B18' }}>
         {/* === FILE EXPLORER (izquierda 200px) === */}
         <aside
           data-testid="file-explorer"
           style={{
             width: 200, flexShrink: 0, borderRight: '1px solid #1E3A5F',
             overflowY: 'auto', padding: '8px 0',
           }}
         >
           <div style={{ color: '#4FC3F7', fontSize: 11, fontWeight: 600, padding: '4px 12px 8px', letterSpacing: '1px' }}>
             EXPLORADOR
           </div>
           {renderFileTree(archivos)}
           {archivos.length === 0 && (
             <div style={{ color: '#37474F', fontSize: 12, padding: '8px 12px' }}>Sin archivos</div>
           )}
         </aside>

         {/* === EDITOR + TERMINAL (centro) === */}
         <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
           {/* Monaco Editor */}
           <div data-testid="monaco-editor-container" style={{ flex: 1, overflow: 'hidden' }}>
             <Editor
               height="100%"
               language={archivoActivo?.nombre.endsWith('.py') ? 'python' : 'typescript'}
               value={codigoActivo}
               onChange={(val) => setCodigoActivo(val ?? '')}
               theme="vs-dark"
               options={{
                 fontSize: 14,
                 minimap: { enabled: false },
                 scrollBeyondLastLine: false,
                 wordWrap: 'on',
               }}
             />
           </div>

           {/* Terminal */}
           {terminalVisible && (
             <div
               data-testid="terminal"
               style={{
                 height: 180, borderTop: '1px solid #1E3A5F', backgroundColor: '#000',
                 fontFamily: 'monospace', fontSize: 12, color: '#A5D6A7',
                 padding: 12, overflowY: 'auto',
               }}
             >
               <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                 <span style={{ color: '#4FC3F7', fontWeight: 600 }}>TERMINAL</span>
                 <button
                   data-testid="terminal-toggle"
                   onClick={() => setTerminalVisible(false)}
                   style={{ background: 'transparent', border: 'none', color: '#607D8B', cursor: 'pointer' }}
                 >
                   ▼
                 </button>
               </div>
               <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{terminalOutput || '$ _'}</pre>
             </div>
           )}
           {!terminalVisible && (
             <button
               data-testid="terminal-toggle-show"
               onClick={() => setTerminalVisible(true)}
               style={{
                 height: 28, backgroundColor: '#0A0E1A', border: 'none',
                 borderTop: '1px solid #1E3A5F', color: '#607D8B',
                 cursor: 'pointer', fontSize: 12, width: '100%',
               }}
             >
               ▲ Terminal
             </button>
           )}
         </div>

         {/* === CHAT IA (derecha 300px) — SIEMPRE VISIBLE === */}
         <aside
           data-testid="chat-panel"
           style={{
             width: 300, flexShrink: 0, borderLeft: '1px solid #1E3A5F',
             display: 'flex', flexDirection: 'column',
           }}
         >
           <div style={{ padding: '12px 16px', borderBottom: '1px solid #1E3A5F', color: '#4FC3F7', fontSize: 12, fontWeight: 600 }}>
             Chat IA
           </div>
           <div data-testid="chat-messages" style={{ flex: 1, overflowY: 'auto', padding: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
             {chatMessages.map((msg) => (
               <div key={msg.id} data-testid={`chat-msg-${msg.id}`} style={{
                 backgroundColor: msg.role === 'user' ? '#1E3A5F' : '#0A0E1A',
                 borderRadius: 8, padding: '8px 12px', fontSize: 13,
                 color: msg.role === 'user' ? '#E0F7FA' : '#90CAF9',
                 alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start', maxWidth: '90%',
               }}>
                 {msg.content}
               </div>
             ))}
           </div>
           <form onSubmit={handleChatSend} style={{ padding: 12, borderTop: '1px solid #1E3A5F' }}>
             <input
               data-testid="chat-input"
               value={chatInput}
               onChange={(e) => setChatInput(e.target.value)}
               placeholder="Escribe un mensaje..."
               style={{
                 width: '100%', backgroundColor: '#0A0E1A', border: '1px solid #1E3A5F',
                 borderRadius: 6, color: '#E0F7FA', padding: '8px 12px',
                 fontSize: 13, boxSizing: 'border-box',
               }}
             />
           </form>
         </aside>
       </div>
     )
   }

6. Crear archivo frontend/src/components/nodes/AutomationNodeLayout.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/nodes/AutomationNodeLayout.tsx
   Contenido:

   /**
    * YeyoOS — AutomationNodeLayout
    * Micro-fase 3.20 — Capa 3: Cuerpo
    *
    * Layout del nodo de automatización.
    * [Pipeline canvas visual (izq flex)] | [Chat IA (der 300px)]
    * Pipeline canvas: bloques arrastrables con React Flow
    * Historial de ejecuciones abajo del chat
    */

   import React, { useState, useCallback } from 'react'
   import ReactFlow, {
     Node, Edge, Controls, Background,
     useNodesState, useEdgesState, addEdge, Connection,
     BackgroundVariant,
   } from 'reactflow'
   import 'reactflow/dist/style.css'

   export interface EjecucionHistorial {
     id: string
     timestamp: number
     estado: 'completado' | 'error' | 'cancelado'
     duracionMs: number
     mensaje?: string
   }

   export interface AutomationNodeLayoutProps {
     chatMessages?: Array<{ id: string; role: 'user' | 'assistant'; content: string }>
     onChatSend?: (mensaje: string) => void
     historialEjecuciones?: EjecucionHistorial[]
     initialNodes?: Node[]
     initialEdges?: Edge[]
   }

   const DEFAULT_NODES: Node[] = [
     { id: 'trigger', position: { x: 50, y: 100 }, data: { label: '⚡ Trigger' }, type: 'input' },
     { id: 'action', position: { x: 250, y: 100 }, data: { label: '⚙️ Acción' } },
     { id: 'output', position: { x: 450, y: 100 }, data: { label: '✅ Resultado' }, type: 'output' },
   ]

   const DEFAULT_EDGES: Edge[] = [
     { id: 'e-trigger-action', source: 'trigger', target: 'action', animated: true },
     { id: 'e-action-output', source: 'action', target: 'output', animated: true },
   ]

   const REACT_FLOW_STYLE: React.CSSProperties = {
     backgroundColor: '#060B18',
   }

   export function AutomationNodeLayout({
     chatMessages = [],
     onChatSend,
     historialEjecuciones = [],
     initialNodes = DEFAULT_NODES,
     initialEdges = DEFAULT_EDGES,
   }: AutomationNodeLayoutProps) {
     const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
     const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)
     const [chatInput, setChatInput] = useState('')

     const onConnect = useCallback(
       (params: Connection) => setEdges((eds) => addEdge({ ...params, animated: true }, eds)),
       [setEdges]
     )

     const handleChatSend = (e: React.FormEvent) => {
       e.preventDefault()
       if (!chatInput.trim()) return
       onChatSend?.(chatInput)
       setChatInput('')
     }

     return (
       <div data-testid="automation-node-layout" style={{ display: 'flex', height: '100%', backgroundColor: '#060B18' }}>
         {/* === PIPELINE CANVAS (izquierda flex) === */}
         <div data-testid="pipeline-canvas" style={{ flex: 1, position: 'relative' }}>
           <ReactFlow
             nodes={nodes}
             edges={edges}
             onNodesChange={onNodesChange}
             onEdgesChange={onEdgesChange}
             onConnect={onConnect}
             style={REACT_FLOW_STYLE}
             fitView
           >
             <Controls />
             <Background variant={BackgroundVariant.Dots} color="#1E3A5F" gap={20} size={1} />
           </ReactFlow>
         </div>

         {/* === CHAT + HISTORIAL (derecha 300px) — SIEMPRE VISIBLE === */}
         <aside
           data-testid="chat-panel"
           style={{
             width: 300, flexShrink: 0, borderLeft: '1px solid #1E3A5F',
             display: 'flex', flexDirection: 'column',
           }}
         >
           <div style={{ padding: '12px 16px', borderBottom: '1px solid #1E3A5F', color: '#4FC3F7', fontSize: 12, fontWeight: 600 }}>
             Chat IA
           </div>
           <div data-testid="chat-messages" style={{ flex: 1, overflowY: 'auto', padding: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
             {chatMessages.map((msg) => (
               <div key={msg.id} data-testid={`chat-msg-${msg.id}`} style={{
                 backgroundColor: msg.role === 'user' ? '#1E3A5F' : '#0A0E1A',
                 borderRadius: 8, padding: '8px 12px', fontSize: 13,
                 color: msg.role === 'user' ? '#E0F7FA' : '#90CAF9',
                 alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start', maxWidth: '90%',
               }}>
                 {msg.content}
               </div>
             ))}
           </div>
           <form onSubmit={handleChatSend} style={{ padding: 12, borderTop: '1px solid #1E3A5F' }}>
             <input
               data-testid="chat-input"
               value={chatInput}
               onChange={(e) => setChatInput(e.target.value)}
               placeholder="Escribe un mensaje..."
               style={{
                 width: '100%', backgroundColor: '#0A0E1A', border: '1px solid #1E3A5F',
                 borderRadius: 6, color: '#E0F7FA', padding: '8px 12px',
                 fontSize: 13, boxSizing: 'border-box',
               }}
             />
           </form>

           {/* Historial de ejecuciones */}
           {historialEjecuciones.length > 0 && (
             <div
               data-testid="historial-ejecuciones"
               style={{ borderTop: '1px solid #1E3A5F', maxHeight: 180, overflowY: 'auto', padding: 8 }}
             >
               <div style={{ color: '#607D8B', fontSize: 11, fontWeight: 600, marginBottom: 6, letterSpacing: '1px' }}>
                 HISTORIAL
               </div>
               {historialEjecuciones.map((e) => (
                 <div
                   key={e.id}
                   data-testid={`historial-${e.id}`}
                   style={{
                     padding: '4px 8px', borderRadius: 4, marginBottom: 2,
                     backgroundColor: '#0A0E1A', border: '1px solid #1E3A5F',
                     fontSize: 11, color: e.estado === 'completado' ? '#A5D6A7' : '#EF9A9A',
                     display: 'flex', justifyContent: 'space-between',
                   }}
                 >
                   <span>{e.estado === 'completado' ? '✅' : '❌'} {e.mensaje ?? e.estado}</span>
                   <span style={{ color: '#37474F' }}>{e.duracionMs}ms</span>
                 </div>
               ))}
             </div>
           )}
         </aside>
       </div>
     )
   }

7. Crear archivo frontend/src/__tests__/layout/Topbar.test.tsx:

   Ruta: ~/yeyo-os/frontend/src/__tests__/layout/Topbar.test.tsx
   Contenido:

   /**
    * Tests para Topbar, HubSidebar, y 4 layouts de nodos — Micro-fase 3.20
    */

   import React from 'react'
   import { render, screen, fireEvent } from '@testing-library/react'
   import { Topbar, TabInfo } from '../../components/layout/Topbar'
   import { HubSidebar } from '../../components/layout/HubSidebar'
   import { ImageNodeLayout } from '../../components/nodes/ImageNodeLayout'
   import { VideoNodeLayout } from '../../components/nodes/VideoNodeLayout'
   import { CodeNodeLayout } from '../../components/nodes/CodeNodeLayout'
   import { AutomationNodeLayout } from '../../components/nodes/AutomationNodeLayout'
   import { useHubStore } from '../../stores/hubStore'

   // Mocks
   jest.mock('pixi.js', () => ({
     Application: jest.fn().mockImplementation(() => ({
       init: jest.fn().mockResolvedValue(undefined),
       destroy: jest.fn(),
       screen: { width: 800, height: 600 },
       stage: { addChild: jest.fn() },
       ticker: { add: jest.fn() },
       canvas: document.createElement('canvas'),
     })),
   }))

   jest.mock('@monaco-editor/react', () => ({
     __esModule: true,
     default: () => <div data-testid="monaco-editor" />,
   }))

   jest.mock('reactflow', () => ({
     __esModule: true,
     default: ({ children }: { children: React.ReactNode }) => <div data-testid="react-flow">{children}</div>,
     Controls: () => <div />,
     Background: () => <div />,
     BackgroundVariant: { Dots: 'dots' },
     useNodesState: (nodes: unknown[]) => [nodes, jest.fn(), jest.fn()],
     useEdgesState: (edges: unknown[]) => [edges, jest.fn(), jest.fn()],
     addEdge: jest.fn(),
   }))

   const TABS_MOCK: TabInfo[] = [
     { id: 'img', label: 'Image', icono: '🎨', activo: true },
     { id: 'code', label: 'Code', icono: '💻', activo: false },
   ]

   beforeEach(() => {
     useHubStore.setState({ pipelineActivo: false, nodosEnPipeline: [], nodosInstalados: [] })
   })

   describe('Topbar', () => {
     it('renderiza el topbar', () => {
       render(<Topbar tabs={TABS_MOCK} onTabClick={jest.fn()} onTabClose={jest.fn()} onToggleSidebar={jest.fn()} sidebarOpen={false} />)
       expect(screen.getByTestId('topbar')).toBeInTheDocument()
     })

     it('muestra el botón de toggle sidebar', () => {
       render(<Topbar tabs={[]} onTabClick={jest.fn()} onTabClose={jest.fn()} onToggleSidebar={jest.fn()} sidebarOpen={false} />)
       expect(screen.getByTestId('toggle-sidebar-btn')).toBeInTheDocument()
     })

     it('llama onToggleSidebar al hacer click en toggle', () => {
       const onToggle = jest.fn()
       render(<Topbar tabs={[]} onTabClick={jest.fn()} onTabClose={jest.fn()} onToggleSidebar={onToggle} sidebarOpen={false} />)
       fireEvent.click(screen.getByTestId('toggle-sidebar-btn'))
       expect(onToggle).toHaveBeenCalledTimes(1)
     })

     it('muestra las tabs', () => {
       render(<Topbar tabs={TABS_MOCK} onTabClick={jest.fn()} onTabClose={jest.fn()} onToggleSidebar={jest.fn()} sidebarOpen={false} />)
       expect(screen.getByTestId('tab-img')).toBeInTheDocument()
       expect(screen.getByTestId('tab-code')).toBeInTheDocument()
     })

     it('Kill Switch siempre visible', () => {
       render(<Topbar tabs={[]} onTabClick={jest.fn()} onTabClose={jest.fn()} onToggleSidebar={jest.fn()} sidebarOpen={false} />)
       expect(screen.getByTestId('kill-switch-btn')).toBeInTheDocument()
     })

     it('indicador de pipeline visible pero inactivo por defecto', () => {
       render(<Topbar tabs={[]} onTabClick={jest.fn()} onTabClose={jest.fn()} onToggleSidebar={jest.fn()} sidebarOpen={false} />)
       expect(screen.getByTestId('pipeline-indicator')).toHaveAttribute('data-pipeline-activo', 'false')
     })

     it('llama onTabClose al cerrar una tab', () => {
       const onClose = jest.fn()
       render(<Topbar tabs={TABS_MOCK} onTabClick={jest.fn()} onTabClose={onClose} onToggleSidebar={jest.fn()} sidebarOpen={false} />)
       fireEvent.click(screen.getByTestId('close-tab-img'))
       expect(onClose).toHaveBeenCalledWith('img')
     })
   })

   describe('HubSidebar', () => {
     const NODOS = [{ id: 'img', label: 'Image', icono: '🎨', estado: 'idle' as const }]

     it('renderiza con data-open=false cuando cerrado', () => {
       render(<HubSidebar open={false} nodos={NODOS} onNodoClick={jest.fn()} />)
       expect(screen.getByTestId('hub-sidebar')).toHaveAttribute('data-open', 'false')
     })

     it('renderiza con data-open=true cuando abierto', () => {
       render(<HubSidebar open={true} nodos={NODOS} onNodoClick={jest.fn()} />)
       expect(screen.getByTestId('hub-sidebar')).toHaveAttribute('data-open', 'true')
     })

     it('muestra nodo en sidebar cuando está abierto', () => {
       render(<HubSidebar open={true} nodos={NODOS} onNodoClick={jest.fn()} />)
       expect(screen.getByTestId('sidebar-node-img')).toBeInTheDocument()
     })

     it('llama onNodoClick al hacer click en un nodo', () => {
       const onClick = jest.fn()
       render(<HubSidebar open={true} nodos={NODOS} onNodoClick={onClick} />)
       fireEvent.click(screen.getByTestId('sidebar-node-img'))
       expect(onClick).toHaveBeenCalledWith('img')
     })
   })

   describe('ImageNodeLayout', () => {
     it('renderiza sin errores', () => {
       render(<ImageNodeLayout />)
       expect(screen.getByTestId('image-node-layout')).toBeInTheDocument()
     })

     it('chat siempre visible', () => {
       render(<ImageNodeLayout />)
       expect(screen.getByTestId('chat-panel')).toBeInTheDocument()
     })

     it('panel de controles visible', () => {
       render(<ImageNodeLayout />)
       expect(screen.getByTestId('image-controls')).toBeInTheDocument()
     })

     it('galería visible', () => {
       render(<ImageNodeLayout />)
       expect(screen.getByTestId('gallery-area')).toBeInTheDocument()
     })
   })

   describe('VideoNodeLayout', () => {
     it('renderiza sin errores', () => {
       render(<VideoNodeLayout />)
       expect(screen.getByTestId('video-node-layout')).toBeInTheDocument()
     })

     it('chat siempre visible', () => {
       render(<VideoNodeLayout />)
       expect(screen.getByTestId('chat-panel')).toBeInTheDocument()
     })

     it('timeline visible', () => {
       render(<VideoNodeLayout />)
       expect(screen.getByTestId('timeline')).toBeInTheDocument()
     })
   })

   describe('CodeNodeLayout', () => {
     it('renderiza sin errores', () => {
       render(<CodeNodeLayout />)
       expect(screen.getByTestId('code-node-layout')).toBeInTheDocument()
     })

     it('chat siempre visible', () => {
       render(<CodeNodeLayout />)
       expect(screen.getByTestId('chat-panel')).toBeInTheDocument()
     })

     it('Monaco editor visible', () => {
       render(<CodeNodeLayout />)
       expect(screen.getByTestId('monaco-editor-container')).toBeInTheDocument()
     })

     it('file explorer visible', () => {
       render(<CodeNodeLayout />)
       expect(screen.getByTestId('file-explorer')).toBeInTheDocument()
     })
   })

   describe('AutomationNodeLayout', () => {
     it('renderiza sin errores', () => {
       render(<AutomationNodeLayout />)
       expect(screen.getByTestId('automation-node-layout')).toBeInTheDocument()
     })

     it('chat siempre visible', () => {
       render(<AutomationNodeLayout />)
       expect(screen.getByTestId('chat-panel')).toBeInTheDocument()
     })

     it('pipeline canvas visible', () => {
       render(<AutomationNodeLayout />)
       expect(screen.getByTestId('pipeline-canvas')).toBeInTheDocument()
     })

     it('muestra historial cuando hay ejecuciones', () => {
       const historial = [{ id: 'e1', timestamp: Date.now(), estado: 'completado' as const, duracionMs: 1500 }]
       render(<AutomationNodeLayout historialEjecuciones={historial} />)
       expect(screen.getByTestId('historial-ejecuciones')).toBeInTheDocument()
     })
   })

VERIFICAR:
- [ ] Topbar.tsx — 48px, toggle sidebar, tabs (máx 5), indicador pipeline, Kill Switch siempre visible
- [ ] HubSidebar.tsx — 240px abierto, 0px cerrado, transición 300ms, nodos en miniatura
- [ ] ImageNodeLayout.tsx — controles izq, galería centro, chat der
- [ ] VideoNodeLayout.tsx — preview+assets arriba, timeline abajo, chat der
- [ ] CodeNodeLayout.tsx — file explorer izq, Monaco centro, chat der, terminal abajo collapsable
- [ ] AutomationNodeLayout.tsx — React Flow izq, chat+historial der
- [ ] Chat SIEMPRE a la derecha en los 4 layouts
- [ ] Tests pasan: Topbar (7), HubSidebar (4), 4 layouts (4 cada uno = 16) = 27 tests total

SI FALLA:
- @monaco-editor/react no instalado: npm install @monaco-editor/react
- reactflow no instalado: npm install reactflow
- systemStore.activarKillSwitch no existe: agregar al systemStore existente o mockear en tests
- React Flow CSS import error en tests: mockear el módulo completo como en el test
- useSystemStore no existe: crear store mínimo o agregar campo al store existente

NO HACER:
- No reimplementar el Kill Switch — solo referenciarlo desde systemStore
- No conectar el drag & drop con el backend en esta micro-fase (solo UI)
- No implementar Monaco desde cero — usar @monaco-editor/react
- No hacer los 4 layouts en un solo archivo — cada uno en su propio componente
- No usar modales para mostrar resultados — siempre visible en el layout

GATE: Topbar visible con tabs, toggle de sidebar y Kill Switch. Hub Sidebar se abre/cierra con animación 300ms mostrando nodos instalados. Los 4 layouts de nodos renderizan con chat fijo a la derecha (300px). Drag & drop habilitado entre zonas. Double Grid Background visible detrás. Todos los tests pasan (27 mínimo).
```
