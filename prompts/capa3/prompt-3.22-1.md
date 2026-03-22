## ═══════════════════════════════════════
## MICRO-FASE 3.22 — Primera Tarea: Materialización de Nodo + Scan Result
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 3.22-1 [VSCODE] — Partículas que convergen, línea de energía y efecto scan al revelar resultado

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 3.22 de Capa 3 (Cuerpo): implementar la secuencia visual de la primera tarea — un nodo materializa desde partículas dispersas, se traza una línea de energía desde YEYO, y el resultado mock se revela con un efecto scan de arriba a abajo.

CONTEXTO:
- Micro-fases 3.0–3.21 completadas: Hub Canvas, nodos, grafos, doble cuadrícula, onboarding (3.18), Hub activo con nodos libres (3.19), Node App Layout (3.20), Seguridad Visual (3.21)
- OnboardingScreen.tsx existe en frontend/src/components/onboarding/OnboardingScreen.tsx (de 3.18): tiene el flujo de nombre + primera tarea del usuario
- graphStore existe en frontend/src/stores/graphStore.ts con estado de nodos (pendiente/activo/completado/error)
- hubStore existe en frontend/src/stores/hubStore.ts con posicionesNodos: Record<string, {x, y}>
- Stack: React + TypeScript + PixiJS 8 + Zustand
- Backend: FastAPI — en esta micro-fase el resultado se MOCKEA con datos de ejemplo (no hay integración real con backend)
- Hardware: GTX 1060 3GB — partículas PixiJS deben ser ≤12 por nodo, usar Graphics (no Sprite), sin shaders pesados

Colores por tipo de nodo:
- image  → #A855F7 (púrpura)
- video  → #3B82F6 (azul)
- code   → #10B981 (verde esmeralda)
- text   → #F59E0B (ámbar)
- audio  → #EC4899 (rosa)
- generic → #60A5FA (azul YEYO)

YEYO central siempre #60A5FA. Posición default de YEYO: centro del canvas (canvasWidth/2, canvasHeight/2).

Secuencia temporal exacta (t=0 cuando el usuario presiona Enter en onboarding):
- t=0ms      : 10 partículas aparecen en posiciones aleatorias (radio 60–80px desde destino)
- t=0–600ms  : partículas convergen al centro del nodo (ease-in-out)
- t=600–800ms: fusión — partículas desaparecen, nodo hace pop (scale 0→1.2→1.0 en 200ms)
- t=800ms    : nodo visible, línea de energía empieza a dibujarse
- t=800–1200ms: línea de energía se traza desde YEYO al nodo (strokeDashoffset animation via PixiJS)
- t=1200ms   : partículas de energía empiezan a fluir por la línea; nodo pulsa (estado "procesando")
- t=3200ms   : resultado mock llega; efecto scan inicia (600ms)
- t=3800ms   : nodo pasa a estado "completado" (#4CAF50); línea se hace tenue (opacity 0.4)

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo frontend/src/stores/firstTaskStore.ts:

   Ruta: ~/yeyo-os/frontend/src/stores/firstTaskStore.ts
   Contenido:

   /**
    * YeyoOS — firstTaskStore
    * Micro-fase 3.22 — Capa 3: Cuerpo
    *
    * Store Zustand que gestiona la secuencia de primera tarea:
    * idle → materializing → drawing_line → processing → scanning → complete
    */

   import { create } from 'zustand'

   export type FirstTaskPhase =
     | 'idle'
     | 'materializing'
     | 'drawing_line'
     | 'processing'
     | 'scanning'
     | 'complete'

   export type NodeType = 'image' | 'video' | 'code' | 'text' | 'audio' | 'generic'

   export interface FirstTaskResult {
     type: NodeType
     imageUrl?: string
     textContent?: string
     title: string
   }

   export const NODE_COLORS: Record<NodeType, string> = {
     image:   '#A855F7',
     video:   '#3B82F6',
     code:    '#10B981',
     text:    '#F59E0B',
     audio:   '#EC4899',
     generic: '#60A5FA',
   }

   const MOCK_RESULTS: Record<NodeType, FirstTaskResult> = {
     image: {
       type: 'image',
       title: 'Imagen generada',
       imageUrl: 'https://picsum.photos/320/200?random=42',
     },
     video: {
       type: 'video',
       title: 'Video procesado',
       textContent: 'Video clip generado: 1080p, 30fps, 15 segundos.\nListo para exportar.',
     },
     code: {
       type: 'code',
       title: 'Código generado',
       textContent: 'def generar_atardecer():\n    paleta = ["#FF6B35", "#F7C59F", "#EFEFD0"]\n    return pintar(paleta)\n\nresultado = generar_atardecer()',
     },
     text: {
       type: 'text',
       title: 'Texto generado',
       textContent: 'YeyoOS es un sistema operativo AI-nativo con arquitectura hexagonal. Diseñado para potenciar tu creatividad con inteligencia artificial integrada.',
     },
     audio: {
       type: 'audio',
       title: 'Audio generado',
       textContent: 'Pista de audio sintetizada.\nDuración: 30 segundos\nFormato: WAV 44.1kHz estéreo\nListo para reproducir.',
     },
     generic: {
       type: 'generic',
       title: 'Tarea completada',
       textContent: 'La tarea fue procesada exitosamente por YeyoOS.',
     },
   }

   /** Detecta el tipo de nodo según palabras clave en la tarea. */
   export function detectarTipoNodo(tarea: string): NodeType {
     const t = tarea.toLowerCase()
     if (/imagen|foto|diseño|ilustra|pinta|dibuja|render|genera.*imagen|fotogr/.test(t)) return 'image'
     if (/video|clip|reel|película|animación|graba|screencast/.test(t)) return 'video'
     if (/código|code|programa|script|función|clase|api|endpoint|debug/.test(t)) return 'code'
     if (/audio|música|canción|sonido|podcast|voz|beat|melodía/.test(t)) return 'audio'
     if (/texto|redacta|escribe|resume|traduce|corrije|carta|email|artículo/.test(t)) return 'text'
     return 'generic'
   }

   export interface FirstTaskStore {
     phase: FirstTaskPhase
     taskText: string
     nodeType: NodeType
     nodeColor: string
     result: FirstTaskResult | null
     iniciarPrimeraTarea: (tarea: string, tipoNodo?: NodeType) => void
     setPhase: (phase: FirstTaskPhase) => void
     setResult: (result: FirstTaskResult) => void
     reset: () => void
   }

   export const useFirstTaskStore = create<FirstTaskStore>((set, get) => ({
     phase: 'idle',
     taskText: '',
     nodeType: 'generic',
     nodeColor: '#60A5FA',
     result: null,

     iniciarPrimeraTarea: (tarea: string, tipoNodo?: NodeType) => {
       const tipo = tipoNodo ?? detectarTipoNodo(tarea)
       set({
         phase: 'materializing',
         taskText: tarea,
         nodeType: tipo,
         nodeColor: NODE_COLORS[tipo],
         result: null,
       })

       // Secuencia temporal con timeouts
       setTimeout(() => set({ phase: 'drawing_line' }), 800)
       setTimeout(() => set({ phase: 'processing' }), 1200)
       setTimeout(() => {
         set({ phase: 'scanning', result: MOCK_RESULTS[get().nodeType] })
       }, 3200)
       setTimeout(() => set({ phase: 'complete' }), 3800)
     },

     setPhase: (phase) => set({ phase }),
     setResult: (result) => set({ result }),
     reset: () => set({ phase: 'idle', taskText: '', nodeType: 'generic', nodeColor: '#60A5FA', result: null }),
   }))


2. Crear archivo frontend/src/components/hub/FirstTaskSequence.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/hub/FirstTaskSequence.tsx
   Contenido:

   /**
    * YeyoOS — FirstTaskSequence
    * Micro-fase 3.22 — Capa 3: Cuerpo
    *
    * Secuencia visual completa de la primera tarea:
    * 1. Partículas convergen → nodo materializa (PixiJS)
    * 2. Línea de energía se traza desde YEYO (PixiJS)
    * 3. Partículas de energía fluyen por la línea (PixiJS)
    * 4. Nodo pulsa en estado "procesando" (CSS)
    * 5. ScanReveal revela el resultado (CSS + CSS clip-path)
    * 6. Estado completado: nodo verde, línea tenue (CSS transition)
    */

   import React, { useEffect, useRef, useState, useCallback } from 'react'
   import * as PIXI from 'pixi.js'
   import { useFirstTaskStore, NodeType, FirstTaskResult, NODE_COLORS } from '../../stores/firstTaskStore'
   import { ScanReveal } from './ScanReveal'

   // ═══════════════════════════════════
   // TIPOS INTERNOS
   // ═══════════════════════════════════

   interface Particle {
     gfx: PIXI.Graphics
     startX: number
     startY: number
     startTime: number
     duration: number
   }

   interface EnergyParticle {
     gfx: PIXI.Graphics
     progress: number   // 0.0–1.0 a lo largo de la línea
     speed: number
   }

   export interface FirstTaskSequenceProps {
     yeyoX: number       // posición X del nodo central YEYO
     yeyoY: number       // posición Y del nodo central YEYO
     nodeX: number       // posición X destino del nuevo nodo satélite
     nodeY: number       // posición Y destino del nuevo nodo satélite
     canvasWidth: number
     canvasHeight: number
   }

   // ═══════════════════════════════════
   // HELPERS DE ANIMACIÓN
   // ═══════════════════════════════════

   function lerp(a: number, b: number, t: number): number {
     return a + (b - a) * t
   }

   function easeInOut(t: number): number {
     return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t
   }

   function hexToInt(hex: string): number {
     return parseInt(hex.replace('#', ''), 16)
   }

   // ═══════════════════════════════════
   // COMPONENTE PRINCIPAL
   // ═══════════════════════════════════

   export function FirstTaskSequence({
     yeyoX,
     yeyoY,
     nodeX,
     nodeY,
     canvasWidth,
     canvasHeight,
   }: FirstTaskSequenceProps) {
     const canvasRef = useRef<HTMLCanvasElement>(null)
     const appRef    = useRef<PIXI.Application | null>(null)
     const lineGfxRef = useRef<PIXI.Graphics | null>(null)
     const particlesRef = useRef<Particle[]>([])
     const energyRef    = useRef<EnergyParticle[]>([])
     const animRef      = useRef<number>(0)
     const energyAnimRef = useRef<number>(0)

     const [nodeScale, setNodeScale]         = useState(0)
     const [lineProgress, setLineProgress]   = useState(0)
     const [lineOpacity, setLineOpacity]     = useState(1)
     const [showProcessing, setShowProcessing] = useState(false)
     const [showScan, setShowScan]           = useState(false)

     const { phase, nodeColor, nodeType, result } = useFirstTaskStore()

     // ── Inicializar PixiJS ──────────────────────────────────────
     useEffect(() => {
       if (!canvasRef.current || appRef.current) return

       const app = new PIXI.Application()
       app.init({
         canvas: canvasRef.current,
         width: canvasWidth,
         height: canvasHeight,
         backgroundAlpha: 0,
         antialias: true,
         resolution: window.devicePixelRatio || 1,
       }).then(() => {
         appRef.current = app
         const lg = new PIXI.Graphics()
         app.stage.addChild(lg)
         lineGfxRef.current = lg
       })

       return () => {
         cancelAnimationFrame(animRef.current)
         cancelAnimationFrame(energyAnimRef.current)
         app.destroy(false)
         appRef.current = null
       }
     }, [canvasWidth, canvasHeight])

     // ── Fase MATERIALIZING: crear partículas dispersas ──────────
     useEffect(() => {
       if (phase !== 'materializing' || !appRef.current) return

       const app = appRef.current
       const colorInt = hexToInt(nodeColor)
       const NUM = 10
       const now = performance.now()
       particlesRef.current = []

       for (let i = 0; i < NUM; i++) {
         const angle = (i / NUM) * Math.PI * 2 + (Math.random() - 0.5) * 0.6
         const dist  = 65 + Math.random() * 20
         const startX = nodeX + Math.cos(angle) * dist
         const startY = nodeY + Math.sin(angle) * dist
         const size   = 2.5 + Math.random() * 2.5

         const gfx = new PIXI.Graphics()
         gfx.circle(0, 0, size)
         gfx.fill({ color: colorInt, alpha: 0.9 })
         gfx.x = startX
         gfx.y = startY
         app.stage.addChild(gfx)

         particlesRef.current.push({
           gfx,
           startX,
           startY,
           startTime: now + i * 18,  // stagger 18ms
           duration: 530 + Math.random() * 80,
         })
       }

       function animateConverge(ts: number) {
         let allDone = true
         particlesRef.current.forEach((p) => {
           const elapsed = ts - p.startTime
           if (elapsed < 0) { allDone = false; return }
           const t    = Math.min(elapsed / p.duration, 1)
           const ease = easeInOut(t)
           p.gfx.x    = lerp(p.startX, nodeX, ease)
           p.gfx.y    = lerp(p.startY, nodeY, ease)
           p.gfx.alpha = 0.9 - ease * 0.4
           if (t < 1) allDone = false
         })

         if (!allDone) {
           animRef.current = requestAnimationFrame(animateConverge)
         } else {
           // Eliminar partículas y hacer pop del nodo
           particlesRef.current.forEach((p) => {
             appRef.current?.stage.removeChild(p.gfx)
           })
           particlesRef.current = []
           animateNodePop()
         }
       }

       animRef.current = requestAnimationFrame(animateConverge)
     }, [phase, nodeColor, nodeX, nodeY])

     // ── Pop del nodo: scale 0 → 1.2 → 1.0 en 200ms ─────────────
     const animateNodePop = useCallback(() => {
       const start    = performance.now()
       const DURATION = 200

       function frame(ts: number) {
         const t = Math.min((ts - start) / DURATION, 1)
         const scale = t < 0.65
           ? lerp(0, 1.2, t / 0.65)
           : lerp(1.2, 1.0, (t - 0.65) / 0.35)
         setNodeScale(scale)
         if (t < 1) animRef.current = requestAnimationFrame(frame)
       }

       animRef.current = requestAnimationFrame(frame)
     }, [])

     // ── Fase DRAWING_LINE: animar progreso de la línea ───────────
     useEffect(() => {
       if (phase !== 'drawing_line') return

       const start    = performance.now()
       const DURATION = 400

       function animateLine(ts: number) {
         const t = Math.min((ts - start) / DURATION, 1)
         setLineProgress(t)
         if (t < 1) {
           animRef.current = requestAnimationFrame(animateLine)
         } else {
           startEnergyFlow()
         }
       }

       animRef.current = requestAnimationFrame(animateLine)
     }, [phase])

     // ── Partículas de energía fluyendo por la línea ──────────────
     const startEnergyFlow = useCallback(() => {
       if (!appRef.current) return
       const app      = appRef.current
       const colorInt = hexToInt(nodeColor)
       const NUM      = 5

       for (let i = 0; i < NUM; i++) {
         const gfx = new PIXI.Graphics()
         gfx.circle(0, 0, 2.5)
         gfx.fill({ color: colorInt, alpha: 0.85 })
         app.stage.addChild(gfx)
         energyRef.current.push({
           gfx,
           progress: i / NUM,
           speed: 0.0038 + Math.random() * 0.0022,
         })
       }

       function animateEnergy() {
         energyRef.current.forEach((ep) => {
           ep.progress = (ep.progress + ep.speed) % 1
           ep.gfx.x = lerp(yeyoX, nodeX, ep.progress)
           ep.gfx.y = lerp(yeyoY, nodeY, ep.progress)
           const fade = 0.12
           if      (ep.progress < fade)       ep.gfx.alpha = (ep.progress / fade) * 0.85
           else if (ep.progress > 1 - fade)   ep.gfx.alpha = ((1 - ep.progress) / fade) * 0.85
           else                               ep.gfx.alpha = 0.85
         })
         energyAnimRef.current = requestAnimationFrame(animateEnergy)
       }

       energyAnimRef.current = requestAnimationFrame(animateEnergy)
     }, [nodeColor, nodeX, nodeY, yeyoX, yeyoY])

     // ── Sincronizar estados de UI con la fase ────────────────────
     useEffect(() => {
       if (phase === 'processing')  { setShowProcessing(true) }
       if (phase === 'scanning')    { setShowProcessing(false); setShowScan(true) }
       if (phase === 'complete')    { setLineOpacity(0.4) }
     }, [phase])

     // ── Redibujar línea en PixiJS ────────────────────────────────
     useEffect(() => {
       const lg = lineGfxRef.current
       if (!lg || lineProgress <= 0) { lg?.clear(); return }

       const endX    = lerp(yeyoX, nodeX, lineProgress)
       const endY    = lerp(yeyoY, nodeY, lineProgress)
       const colorInt = hexToInt(nodeColor)

       lg.clear()
       lg.setStrokeStyle({ width: 2, color: colorInt, alpha: lineOpacity })
       lg.moveTo(yeyoX, yeyoY)
       lg.lineTo(endX, endY)
       lg.stroke()
     }, [lineProgress, lineOpacity, yeyoX, yeyoY, nodeX, nodeY, nodeColor])

     if (phase === 'idle') return null

     const NODE_D    = 48
     const isComplete = phase === 'complete'

     return (
       <div
         data-testid="first-task-sequence"
         style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}
       >
         {/* Canvas PixiJS — partículas y línea */}
         <canvas
           ref={canvasRef}
           data-testid="pixi-canvas"
           style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}
         />

         {/* Nodo satélite (CSS) */}
         {nodeScale > 0 && (
           <div
             data-testid="satellite-node"
             style={{
               position: 'absolute',
               left:   nodeX - NODE_D / 2,
               top:    nodeY - NODE_D / 2,
               width:  NODE_D,
               height: NODE_D,
               borderRadius: '50%',
               background:  isComplete ? '#4CAF50' : nodeColor,
               boxShadow:   `0 0 18px ${isComplete ? '#4CAF5088' : nodeColor + '88'}`,
               transform:   `scale(${nodeScale})`,
               transition:  isComplete ? 'background 0.5s ease, box-shadow 0.5s ease' : 'none',
               display: 'flex', alignItems: 'center', justifyContent: 'center',
               animation: phase === 'processing'
                 ? 'yeyoNodePulse 1.2s ease-in-out infinite'
                 : 'none',
             }}
           >
             <NodeIcon type={nodeType} />
           </div>
         )}

         {/* Label "procesando..." */}
         {showProcessing && (
           <div
             data-testid="processing-label"
             style={{
               position:   'absolute',
               left:       nodeX - 52,
               top:        nodeY + NODE_D / 2 + 10,
               color:      nodeColor,
               fontSize:   11,
               fontFamily: 'monospace',
               opacity:    0.85,
               animation:  'yeyoFadeInUp 0.3s ease',
             }}
           >
             procesando<AnimatedDots />
           </div>
         )}

         {/* Panel ScanReveal */}
         {showScan && result && (
           <div
             data-testid="scan-reveal-container"
             style={{
               position:     'absolute',
               left:         nodeX + NODE_D / 2 + 18,
               top:          nodeY - 110,
               pointerEvents: 'auto',
             }}
           >
             <ScanReveal
               result={result}
               nodeColor={nodeColor}
               isScanning={phase === 'scanning'}
             />
           </div>
         )}

         <style>{`
           @keyframes yeyoNodePulse {
             0%,100% { transform: scale(1);    box-shadow: 0 0 18px ${nodeColor}88; }
             50%     { transform: scale(1.09); box-shadow: 0 0 30px ${nodeColor}cc; }
           }
           @keyframes yeyoFadeInUp {
             from { opacity: 0; transform: translateY(5px); }
             to   { opacity: 0.85; transform: translateY(0); }
           }
           @keyframes yeyoDotBlink {
             0%,80%,100% { opacity: 0; }
             40%         { opacity: 1; }
           }
         `}</style>
       </div>
     )
   }

   // ── Sub-componentes ──────────────────────────────────────────

   function NodeIcon({ type }: { type: NodeType }) {
     const icons: Record<NodeType, string> = {
       image:   '🖼',
       video:   '🎬',
       code:    '⌨',
       text:    '📝',
       audio:   '🎵',
       generic: '✦',
     }
     return <span style={{ fontSize: 20, lineHeight: 1 }}>{icons[type]}</span>
   }

   function AnimatedDots() {
     return (
       <span>
         {[0, 1, 2].map((i) => (
           <span
             key={i}
             style={{
               display:   'inline-block',
               animation: `yeyoDotBlink 1.4s ${i * 0.2}s infinite`,
             }}
           >.</span>
         ))}
       </span>
     )
   }


3. Crear archivo frontend/src/components/hub/ScanReveal.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/hub/ScanReveal.tsx
   Contenido:

   /**
    * YeyoOS — ScanReveal
    * Micro-fase 3.22 — Capa 3: Cuerpo
    *
    * Panel de resultado con efecto scanner que barre de arriba a abajo en 600ms.
    * - Scanner bar: rectángulo semitransparente 4px de alto con glow del color del nodo
    * - Imagen: se revela usando CSS clip-path sincronizado con la posición del scanner
    * - Texto: las líneas aparecen conforme el scanner las alcanza
    * - Al terminar: scanner bar desaparece (fade-out 200ms), panel queda con glow border
    */

   import React, { useEffect, useState, useRef } from 'react'
   import { FirstTaskResult } from '../../stores/firstTaskStore'

   export interface ScanRevealProps {
     result: FirstTaskResult
     nodeColor: string
     isScanning: boolean
   }

   const PANEL_WIDTH    = 320
   const PANEL_HEIGHT   = 220
   const SCAN_DURATION  = 600   // ms
   const FADE_DURATION  = 200   // ms del fade-out del scanner bar

   export function ScanReveal({ result, nodeColor, isScanning }: ScanRevealProps) {
     const [scanY, setScanY]         = useState(0)     // 0.0–1.0
     const [scanDone, setScanDone]   = useState(false)
     const [barOpacity, setBarOpacity] = useState(1)
     const animRef  = useRef<number>(0)

     useEffect(() => {
       if (!isScanning) return

       setScanY(0)
       setScanDone(false)
       setBarOpacity(1)

       const scanStart = performance.now()

       function frameScan(now: number) {
         const t = Math.min((now - scanStart) / SCAN_DURATION, 1)
         setScanY(t)
         if (t < 1) {
           animRef.current = requestAnimationFrame(frameScan)
         } else {
           // Fade-out del scanner bar
           const fadeStart = performance.now()
           function frameFade(now2: number) {
             const tf = Math.min((now2 - fadeStart) / FADE_DURATION, 1)
             setBarOpacity(1 - tf)
             if (tf < 1) {
               animRef.current = requestAnimationFrame(frameFade)
             } else {
               setScanDone(true)
             }
           }
           animRef.current = requestAnimationFrame(frameFade)
         }
       }

       animRef.current = requestAnimationFrame(frameScan)
       return () => cancelAnimationFrame(animRef.current)
     }, [isScanning])

     const isImage = result.type === 'image' && !!result.imageUrl

     return (
       <div
         data-testid="scan-reveal-panel"
         style={{
           width:      PANEL_WIDTH,
           minHeight:  PANEL_HEIGHT,
           background: 'rgba(8, 8, 20, 0.93)',
           border:     `1.5px solid ${nodeColor}`,
           borderRadius: 12,
           overflow:   'hidden',
           position:   'relative',
           boxShadow:  scanDone ? `0 0 22px ${nodeColor}44, inset 0 0 10px ${nodeColor}11` : 'none',
           transition: 'box-shadow 0.5s ease',
         }}
       >
         {/* Contenido */}
         <div style={{ padding: '16px 18px', position: 'relative' }}>
           {/* Título */}
           <div
             data-testid="result-title"
             style={{
               fontSize:   13,
               fontWeight: 700,
               color:      nodeColor,
               marginBottom: 12,
               fontFamily: 'monospace',
               opacity:    scanY > 0.05 ? 1 : 0,
               transition: 'opacity 0.2s ease',
             }}
           >
             {result.title}
           </div>

           {/* Imagen: clip-path revela de arriba a abajo */}
           {isImage && (
             <div
               style={{
                 width:        '100%',
                 height:       148,
                 borderRadius: 8,
                 overflow:     'hidden',
               }}
             >
               <img
                 src={result.imageUrl}
                 alt={result.title}
                 data-testid="result-image"
                 style={{
                   width:      '100%',
                   height:     '100%',
                   objectFit:  'cover',
                   clipPath:   `inset(0 0 ${(1 - scanY) * 100}% 0)`,
                   transition: 'clip-path 16ms linear',
                 }}
               />
             </div>
           )}

           {/* Texto: líneas aparecen conforme el scanner las alcanza */}
           {!isImage && result.textContent && (
             <TextReveal
               content={result.textContent}
               progress={scanY}
               nodeColor={nodeColor}
             />
           )}
         </div>

         {/* Scanner bar */}
         {!scanDone && (
           <div
             data-testid="scanner-bar"
             style={{
               position:   'absolute',
               left:       0,
               right:      0,
               top:        `${scanY * 100}%`,
               height:     4,
               background: `${nodeColor}99`,
               boxShadow:  `0 0 10px ${nodeColor}, 0 0 20px ${nodeColor}66`,
               pointerEvents: 'none',
               zIndex:     10,
               transform:  'translateY(-50%)',
               opacity:    barOpacity,
             }}
           />
         )}
       </div>
     )
   }

   // ── TextReveal: revela líneas de texto conforme pasa el scanner ──

   interface TextRevealProps {
     content:   string
     progress:  number
     nodeColor: string
   }

   function TextReveal({ content, progress, nodeColor }: TextRevealProps) {
     const lines = content.split('\n')
     return (
       <div style={{ fontFamily: 'monospace', fontSize: 12, color: '#e2e8f0', lineHeight: 1.6 }}>
         {lines.map((line, i) => {
           const threshold   = (i + 1) / lines.length
           const lineVisible = progress >= threshold * 0.88
           const isCode      = /^\s+|^def |^class |^import |^from /.test(line)
           return (
             <div
               key={i}
               data-testid={`text-line-${i}`}
               style={{
                 opacity:    lineVisible ? 1 : 0,
                 transition: 'opacity 0.15s ease',
                 minHeight:  18,
                 color:      isCode ? '#a5f3fc' : '#e2e8f0',
                 paddingBottom: 1,
               }}
             >
               {line || '\u00A0'}
             </div>
           )
         })}
       </div>
     )
   }


4. Actualizar frontend/src/components/onboarding/OnboardingScreen.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/onboarding/OnboardingScreen.tsx
   MODIFICAR — agregar la llamada a iniciarPrimeraTarea cuando el usuario escribe la primera tarea y presiona Enter.

   Agregar al inicio del archivo (imports):
     import { useFirstTaskStore } from '../../stores/firstTaskStore'

   Agregar dentro del componente OnboardingScreen (antes del return):
     const { iniciarPrimeraTarea } = useFirstTaskStore()

   Buscar el handler donde el usuario presiona Enter en el campo de primera tarea (generalmente un input con placeholder "¿Cuál va a ser la primera tarea del día?" o similar).
   Añadir al handler, ANTES de cualquier navegación:
     iniciarPrimeraTarea(primeraTareaValue)

   Así el FirstTaskSequence se activa inmediatamente cuando el usuario confirma su primera tarea.


5. Crear archivo frontend/src/__tests__/hub/FirstTaskSequence.test.tsx:

   Ruta: ~/yeyo-os/frontend/src/__tests__/hub/FirstTaskSequence.test.tsx
   Contenido:

   /**
    * Tests — FirstTaskSequence + ScanReveal + firstTaskStore
    * Micro-fase 3.22
    */

   import React from 'react'
   import { render, screen, act } from '@testing-library/react'
   import { renderHook } from '@testing-library/react'
   import { FirstTaskSequence } from '../../../components/hub/FirstTaskSequence'
   import { ScanReveal } from '../../../components/hub/ScanReveal'
   import {
     useFirstTaskStore,
     detectarTipoNodo,
     FirstTaskResult,
     NODE_COLORS,
   } from '../../../stores/firstTaskStore'

   // ── Mock PixiJS (no WebGL en Jest) ────────────────────────────
   jest.mock('pixi.js', () => ({
     Application: jest.fn().mockImplementation(() => ({
       init: jest.fn().mockResolvedValue(undefined),
       stage: {
         addChild:    jest.fn(),
         removeChild: jest.fn(),
       },
       destroy: jest.fn(),
     })),
     Graphics: jest.fn().mockImplementation(() => ({
       circle:         jest.fn().mockReturnThis(),
       fill:           jest.fn().mockReturnThis(),
       clear:          jest.fn().mockReturnThis(),
       setStrokeStyle: jest.fn().mockReturnThis(),
       moveTo:         jest.fn().mockReturnThis(),
       lineTo:         jest.fn().mockReturnThis(),
       stroke:         jest.fn().mockReturnThis(),
       x: 0, y: 0, alpha: 1,
     })),
     Container: jest.fn().mockImplementation(() => ({ x: 0, y: 0, addChild: jest.fn() })),
   }))

   const DEFAULT_PROPS = {
     yeyoX: 400, yeyoY: 300,
     nodeX: 620, nodeY: 300,
     canvasWidth: 800, canvasHeight: 600,
   }

   beforeEach(() => {
     useFirstTaskStore.setState({
       phase: 'idle', taskText: '', nodeType: 'generic',
       nodeColor: '#60A5FA', result: null,
     })
     jest.useFakeTimers()
   })

   afterEach(() => {
     jest.useRealTimers()
   })

   // ─── detectarTipoNodo ─────────────────────────────────────────

   describe('detectarTipoNodo', () => {
     test('detecta imagen con "genera una imagen"', () => {
       expect(detectarTipoNodo('genera una imagen de un atardecer')).toBe('image')
     })
     test('detecta imagen con "foto"', () => {
       expect(detectarTipoNodo('toma una foto del paisaje')).toBe('image')
     })
     test('detecta video con "video"', () => {
       expect(detectarTipoNodo('crea un video corto')).toBe('video')
     })
     test('detecta code con "código"', () => {
       expect(detectarTipoNodo('escribe código python para ordenar una lista')).toBe('code')
     })
     test('detecta audio con "música"', () => {
       expect(detectarTipoNodo('genera música relajante')).toBe('audio')
     })
     test('detecta text con "redacta"', () => {
       expect(detectarTipoNodo('redacta un email profesional')).toBe('text')
     })
     test('retorna generic para tarea desconocida', () => {
       expect(detectarTipoNodo('hola yeyo')).toBe('generic')
     })
   })

   // ─── firstTaskStore ───────────────────────────────────────────

   describe('firstTaskStore', () => {
     test('estado inicial es idle', () => {
       const { result } = renderHook(() => useFirstTaskStore())
       expect(result.current.phase).toBe('idle')
       expect(result.current.result).toBeNull()
     })

     test('iniciarPrimeraTarea pone phase=materializing', () => {
       const { result } = renderHook(() => useFirstTaskStore())
       act(() => { result.current.iniciarPrimeraTarea('genera una imagen') })
       expect(result.current.phase).toBe('materializing')
     })

     test('iniciarPrimeraTarea asigna tipo y color correcto para imagen', () => {
       const { result } = renderHook(() => useFirstTaskStore())
       act(() => { result.current.iniciarPrimeraTarea('genera una imagen') })
       expect(result.current.nodeType).toBe('image')
       expect(result.current.nodeColor).toBe(NODE_COLORS.image)
     })

     test('secuencia: materializing → drawing_line a los 800ms', () => {
       const { result } = renderHook(() => useFirstTaskStore())
       act(() => { result.current.iniciarPrimeraTarea('hola yeyo') })
       act(() => { jest.advanceTimersByTime(800) })
       expect(result.current.phase).toBe('drawing_line')
     })

     test('secuencia: drawing_line → processing a los 1200ms', () => {
       const { result } = renderHook(() => useFirstTaskStore())
       act(() => { result.current.iniciarPrimeraTarea('hola yeyo') })
       act(() => { jest.advanceTimersByTime(1200) })
       expect(result.current.phase).toBe('processing')
     })

     test('secuencia: scanning con resultado mock a los 3200ms', () => {
       const { result } = renderHook(() => useFirstTaskStore())
       act(() => { result.current.iniciarPrimeraTarea('hola yeyo') })
       act(() => { jest.advanceTimersByTime(3200) })
       expect(result.current.phase).toBe('scanning')
       expect(result.current.result).not.toBeNull()
     })

     test('secuencia: complete a los 3800ms', () => {
       const { result } = renderHook(() => useFirstTaskStore())
       act(() => { result.current.iniciarPrimeraTarea('hola yeyo') })
       act(() => { jest.advanceTimersByTime(3800) })
       expect(result.current.phase).toBe('complete')
     })

     test('reset vuelve a idle y borra result', () => {
       const { result } = renderHook(() => useFirstTaskStore())
       act(() => { result.current.iniciarPrimeraTarea('hola yeyo') })
       act(() => { result.current.reset() })
       expect(result.current.phase).toBe('idle')
       expect(result.current.taskText).toBe('')
       expect(result.current.result).toBeNull()
     })

     test('tipoNodo override manual ignora detección automática', () => {
       const { result } = renderHook(() => useFirstTaskStore())
       act(() => { result.current.iniciarPrimeraTarea('hola yeyo', 'code') })
       expect(result.current.nodeType).toBe('code')
       expect(result.current.nodeColor).toBe(NODE_COLORS.code)
     })
   })

   // ─── FirstTaskSequence render ─────────────────────────────────

   describe('FirstTaskSequence — render', () => {
     test('NO renderiza nada cuando phase=idle', () => {
       const { container } = render(<FirstTaskSequence {...DEFAULT_PROPS} />)
       expect(container.firstChild).toBeNull()
     })

     test('renderiza canvas y contenedor cuando phase=materializing', () => {
       useFirstTaskStore.setState({ phase: 'materializing', nodeColor: '#A855F7', nodeType: 'image' })
       render(<FirstTaskSequence {...DEFAULT_PROPS} />)
       expect(screen.getByTestId('first-task-sequence')).toBeInTheDocument()
       expect(screen.getByTestId('pixi-canvas')).toBeInTheDocument()
     })

     test('muestra label procesando cuando phase=processing', () => {
       useFirstTaskStore.setState({ phase: 'processing', nodeColor: '#A855F7', nodeType: 'image', result: null })
       render(<FirstTaskSequence {...DEFAULT_PROPS} />)
       expect(screen.getByTestId('processing-label')).toBeInTheDocument()
     })

     test('muestra ScanReveal cuando phase=scanning con result', () => {
       const mockResult: FirstTaskResult = { type: 'text', title: 'Texto', textContent: 'Hola' }
       useFirstTaskStore.setState({ phase: 'scanning', nodeColor: '#F59E0B', nodeType: 'text', result: mockResult })
       render(<FirstTaskSequence {...DEFAULT_PROPS} />)
       expect(screen.getByTestId('scan-reveal-container')).toBeInTheDocument()
     })

     test('NO muestra ScanReveal cuando result es null', () => {
       useFirstTaskStore.setState({ phase: 'scanning', nodeColor: '#F59E0B', nodeType: 'text', result: null })
       render(<FirstTaskSequence {...DEFAULT_PROPS} />)
       expect(screen.queryByTestId('scan-reveal-container')).toBeNull()
     })
   })

   // ─── ScanReveal ───────────────────────────────────────────────

   describe('ScanReveal', () => {
     const textResult: FirstTaskResult = {
       type: 'text',
       title: 'Texto generado',
       textContent: 'Primera línea\nSegunda línea\nTercera línea',
     }

     test('renderiza el panel con borde del color del nodo', () => {
       render(<ScanReveal result={textResult} nodeColor="#F59E0B" isScanning={false} />)
       const panel = screen.getByTestId('scan-reveal-panel')
       expect(panel).toBeInTheDocument()
       expect(panel.style.border).toContain('#F59E0B')
     })

     test('muestra el título del resultado', () => {
       render(<ScanReveal result={textResult} nodeColor="#F59E0B" isScanning={false} />)
       expect(screen.getByTestId('result-title')).toHaveTextContent('Texto generado')
     })

     test('muestra scanner bar cuando isScanning=true', () => {
       render(<ScanReveal result={textResult} nodeColor="#F59E0B" isScanning={true} />)
       expect(screen.getByTestId('scanner-bar')).toBeInTheDocument()
     })

     test('NO muestra scanner bar cuando isScanning=false', () => {
       render(<ScanReveal result={textResult} nodeColor="#F59E0B" isScanning={false} />)
       expect(screen.queryByTestId('scanner-bar')).toBeNull()
     })

     test('renderiza imagen para resultado tipo image', () => {
       const imageResult: FirstTaskResult = {
         type: 'image', title: 'Imagen generada',
         imageUrl: 'https://picsum.photos/320/200',
       }
       render(<ScanReveal result={imageResult} nodeColor="#A855F7" isScanning={false} />)
       expect(screen.getByTestId('result-image')).toBeInTheDocument()
     })

     test('renderiza líneas de texto para resultado tipo text', () => {
       render(<ScanReveal result={textResult} nodeColor="#F59E0B" isScanning={false} />)
       expect(screen.getByTestId('text-line-0')).toBeInTheDocument()
       expect(screen.getByTestId('text-line-1')).toBeInTheDocument()
       expect(screen.getByTestId('text-line-2')).toBeInTheDocument()
     })

     test('NO renderiza img cuando el resultado es texto', () => {
       render(<ScanReveal result={textResult} nodeColor="#F59E0B" isScanning={false} />)
       expect(screen.queryByTestId('result-image')).toBeNull()
     })
   })
```

VERIFICAR:
- [ ] firstTaskStore: `iniciarPrimeraTarea("genera una imagen")` pone nodeType='image', nodeColor='#A855F7', phase='materializing'
- [ ] Secuencia temporal confirmada con jest.useFakeTimers(): t=800ms → drawing_line, t=1200ms → processing, t=3200ms → scanning con result, t=3800ms → complete
- [ ] FirstTaskSequence no renderiza nada cuando phase='idle'
- [ ] Al llegar a phase='materializing', el canvas PixiJS se inicializa y aparecen partículas dispersas (visible en browser)
- [ ] Las partículas convergen al centro del nodo en ~600ms y el nodo hace pop (visible en browser)
- [ ] La línea se traza desde el centro YEYO hasta el nodo en ~400ms (visible en browser)
- [ ] Partículas de energía fluyen continuamente por la línea al llegar a drawing_line (visible en browser)
- [ ] El label "procesando..." aparece con dots animados en phase='processing'
- [ ] ScanReveal aparece en phase='scanning': scanner bar barre de arriba a abajo revelando imagen/texto
- [ ] Al terminar el scan, el scanner bar desaparece con fade-out y el panel queda con glow border
- [ ] En phase='complete': nodo se torna verde (#4CAF50), línea de energía se hace tenue (opacity 0.4)
- [ ] `detectarTipoNodo` detecta correctamente image/video/code/text/audio/generic
- [ ] OnboardingScreen.tsx llama a `iniciarPrimeraTarea` cuando el usuario presiona Enter en la primera tarea
- [ ] Todos los tests pasan: `npm test -- --testPathPattern=FirstTaskSequence`

SI FALLA:
- PixiJS no inicializa (canvas null): verificar que `canvasRef.current` existe antes de `app.init()`; el segundo `useEffect` con `appRef.current` como guarda previene reinicialización
- Partículas no desaparecen: asegurar que `app.stage.removeChild(p.gfx)` se llama después de que todas las partículas llegaron al destino (revisar que `allDone` sea true en el frame final)
- Línea no se dibuja: `lineGfxRef.current` puede ser null si PixiJS no terminó de inicializar antes de que la fase cambie a drawing_line; agregar guard `if (!lineGfxRef.current) return` en el useEffect de dibujo
- Tests fallan con "pixi.js not mocked": verificar que el mock de pixi.js está en `__mocks__` o en el propio test; el mock debe cubrir `Application`, `Graphics` y `Container`
- `jest.advanceTimersByTime` no cambia la fase: envolver la llamada en `act(() => { jest.advanceTimersByTime(800) })` para que React procese los state updates
- ScanReveal no aparece: verificar que `result` no es null en el store antes de phase='scanning'; en el store `setPhase('scanning')` y `setResult(mock)` se hacen en el mismo `set({})` call
- CSS animations no visibles en tests: los tests verifican `data-testid` y estilos inline, no animaciones CSS; esto es esperado
- OnboardingScreen no tiene handler de primera tarea: buscar en el componente el `onKeyDown` o `onSubmit` del segundo input (el de la tarea), y agregar la llamada ahí

NO HACER:
- No usar WebGL shaders para las partículas — PixiJS Graphics puro es suficiente y respeta el budget de GTX 1060 3GB
- No crear más de 12 partículas por nodo (budget GPU)
- No integrar con el backend real en esta micro-fase — el resultado es siempre mock de MOCK_RESULTS
- No modificar graphStore ni hubStore — firstTaskStore es independiente
- No agregar persistencia en localStorage para firstTaskStore — la secuencia es ephemeral (solo ocurre una vez)
- No bloquear el thread principal esperando animaciones — siempre usar requestAnimationFrame y setTimeout

GATE: Al escribir la primera tarea en onboarding y presionar Enter, 10 partículas dispersas convergen formando un nodo con efecto pop, una línea de energía se traza desde YEYO hasta el nodo, el nodo pulsa con "procesando...", y el resultado mock se revela con el efecto scan de arriba a abajo; todos los 22 tests pasan.
```
