/**
 * YeyoOS — ArenaView
 * Three-panel battle visualization: Script Viewer | Canvas Battle | Battle Log
 * Uses character sprites and real-time WebSocket updates with AI-generated code display.
 */
'use client'

import React, { useRef, useEffect, useState, useCallback } from 'react'
import { SpriteSheet, FRAME_SIZE } from './game/SpriteSheet'

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const WS_URL = API_BASE.replace(/^http/, 'ws') + '/api/v1/arena/live'

const CANVAS_W = 480
const CANVAS_H = 360
const SCALE = 3
const SPRITE_PX = FRAME_SIZE * SCALE
const IDLE_FRAMES = 4
const ATTACK_FRAMES = 4
const ANIM_TICK_MS = 150
const EFFECT_DURATION_MS = 500
const SPARK_COUNT = 8

const YEYO_X = 80
const GUARDIAN_X = CANVAS_W - 80 - SPRITE_PX
const FIGHTER_Y = CANVAS_H / 2 - SPRITE_PX / 2 + 30

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface RoundResult {
  round_number: number
  attack_type: string
  attack_success: boolean
  defense_success: boolean
  attack_duration_ms?: number
  defense_duration_ms?: number
  attack_code?: string
  defense_code?: string
}

type BattleStatus = 'idle' | 'running' | 'paused'

interface Spark {
  x: number; y: number; vx: number; vy: number; life: number; color: string
}

// ---------------------------------------------------------------------------
// Python syntax highlighting (basic)
// ---------------------------------------------------------------------------

function highlightPython(code: string): React.ReactNode[] {
  const lines = code.split('\n')
  const keywords = /\b(import|from|def|class|return|if|elif|else|for|while|try|except|finally|with|as|raise|pass|break|continue|and|or|not|in|is|None|True|False|async|await|print|open|sys|os)\b/g
  const strings = /(["'])(?:(?=(\\?))\2.)*?\1/g
  const comments = /#.*/g
  const decorators = /@\w+/g

  return lines.map((line, i) => {
    let html = line
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
    html = html.replace(comments, (m) => `<span style="color:#6A9955">${m}</span>`)
    html = html.replace(strings, (m) => `<span style="color:#CE9178">${m}</span>`)
    html = html.replace(keywords, (m) => `<span style="color:#569CD6">${m}</span>`)
    html = html.replace(decorators, (m) => `<span style="color:#DCDCAA">${m}</span>`)
    html = html.replace(/\b(\d+\.?\d*)\b/g, (m) => `<span style="color:#B5CEA8">${m}</span>`)
    return (
      <div key={i} style={{ display: 'flex', minHeight: 18 }}>
        <span style={{ color: '#5A5A5A', minWidth: 32, textAlign: 'right', paddingRight: 8, userSelect: 'none' }}>
          {i + 1}
        </span>
        <span dangerouslySetInnerHTML={{ __html: html || '&nbsp;' }} />
      </div>
    )
  })
}

// ---------------------------------------------------------------------------
// ArenaView
// ---------------------------------------------------------------------------

export function ArenaView() {
  // -- state --
  const [battleStatus, setBattleStatus] = useState<BattleStatus>('idle')
  const [rounds, setRounds] = useState<RoundResult[]>([])
  const [redScore, setRedScore] = useState(0)
  const [blueScore, setBlueScore] = useState(0)
  const [currentRound, setCurrentRound] = useState(0)
  const [isConnected, setIsConnected] = useState(false)
  const [maxRounds, setMaxRounds] = useState(100)
  const [scriptTab, setScriptTab] = useState<'attack' | 'defense'>('attack')
  const [latestAttackCode, setLatestAttackCode] = useState('')
  const [latestDefenseCode, setLatestDefenseCode] = useState('')
  const [latestAttackType, setLatestAttackType] = useState('')
  const [latestSuccess, setLatestSuccess] = useState<{ attack: boolean; defense: boolean }>({ attack: false, defense: false })

  // -- refs --
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animFrameRef = useRef<number>(0)
  const wsRef = useRef<WebSocket | null>(null)
  const logRef = useRef<HTMLDivElement>(null)

  // Sprite refs
  const yeyoIdleRef = useRef<SpriteSheet | null>(null)
  const yeyoAttackRef = useRef<SpriteSheet | null>(null)
  const guardianIdleRef = useRef<SpriteSheet | null>(null)
  const guardianAttackRef = useRef<SpriteSheet | null>(null)
  const slashRef = useRef<SpriteSheet | null>(null)
  const shieldRef = useRef<SpriteSheet | null>(null)

  // Animation state refs
  const frameRef = useRef(0)
  const lastTickRef = useRef(0)
  const yeyoStateRef = useRef<'idle' | 'attack'>('idle')
  const guardianStateRef = useRef<'idle' | 'attack'>('idle')
  const effectRef = useRef<{ type: 'slash' | 'shield' | null; startTime: number }>({ type: null, startTime: 0 })
  const sparksRef = useRef<Spark[]>([])
  const scoresRef = useRef({ red: 0, blue: 0, round: 0 })
  const statusRef = useRef<BattleStatus>('idle')

  useEffect(() => {
    scoresRef.current = { red: redScore, blue: blueScore, round: currentRound }
  }, [redScore, blueScore, currentRound])
  useEffect(() => { statusRef.current = battleStatus }, [battleStatus])

  // -- load sprites --
  useEffect(() => {
    async function loadAll() {
      const sheets = [
        { ref: yeyoIdleRef, src: '/sprites/characters/yeyohack/Idle.png' },
        { ref: yeyoAttackRef, src: '/sprites/characters/yeyohack/Attack.png' },
        { ref: guardianIdleRef, src: '/sprites/characters/guardian/Idle.png' },
        { ref: guardianAttackRef, src: '/sprites/characters/guardian/Attack.png' },
        { ref: slashRef, src: '/sprites/effects/SpriteSheetSlash01.png' },
        { ref: shieldRef, src: '/sprites/effects/SpriteSheet.png' },
      ]
      await Promise.all(
        sheets.map(async ({ ref, src }) => {
          const s = new SpriteSheet(src)
          await s.load()
          ref.current = s
        })
      )
    }
    loadAll()
  }, [])

  // -- fetch initial status --
  useEffect(() => {
    async function fetchStatus() {
      try {
        const res = await fetch(`${API_BASE}/api/v1/arena/status`)
        if (res.ok) {
          const json = await res.json()
          const data = json.data || json
          const session = data.session || data
          if (session.status) setBattleStatus(session.status as BattleStatus)
          if (typeof session.red_score === 'number') setRedScore(session.red_score)
          if (typeof session.blue_score === 'number') setBlueScore(session.blue_score)
          if (typeof session.current_round === 'number') setCurrentRound(session.current_round)
        }
      } catch { /* API may not be up yet */ }
    }
    fetchStatus()
  }, [])

  // -- trigger animation on round result --
  const handleRoundResult = useCallback((result: RoundResult) => {
    setRounds(prev => [...prev, result])
    setCurrentRound(result.round_number)
    setLatestAttackType(result.attack_type || '')
    setLatestSuccess({ attack: result.attack_success, defense: result.defense_success })

    if (result.attack_code) setLatestAttackCode(result.attack_code)
    if (result.defense_code) setLatestDefenseCode(result.defense_code)

    if (result.attack_success) {
      setRedScore(s => s + 1)
      yeyoStateRef.current = 'attack'
      effectRef.current = { type: 'slash', startTime: performance.now() }
      spawnSparks(GUARDIAN_X + SPRITE_PX / 2, FIGHTER_Y + SPRITE_PX / 2, '#EF4444')
      setTimeout(() => { yeyoStateRef.current = 'idle' }, EFFECT_DURATION_MS)
    }

    if (result.defense_success) {
      setBlueScore(s => s + 1)
      guardianStateRef.current = 'attack'
      effectRef.current = { type: 'shield', startTime: performance.now() }
      spawnSparks(GUARDIAN_X + SPRITE_PX / 2, FIGHTER_Y + SPRITE_PX / 2, '#4FC3F7')
      setTimeout(() => { guardianStateRef.current = 'idle' }, EFFECT_DURATION_MS)
    }
  }, [])

  // -- websocket --
  useEffect(() => {
    if (battleStatus !== 'running') return

    let ws: WebSocket | null = null
    let reconnectTimer: ReturnType<typeof setTimeout>

    function connect() {
      try {
        ws = new WebSocket(WS_URL)
        ws.onopen = () => setIsConnected(true)
        ws.onmessage = (msg) => {
          try {
            const event = JSON.parse(msg.data)
            if (event.event === 'round_completed' && event.round) {
              handleRoundResult(event.round as RoundResult)
              if (event.scores) {
                setRedScore(event.scores.red)
                setBlueScore(event.scores.blue)
              }
            }
          } catch { /* ignore non-JSON */ }
        }
        ws.onclose = () => {
          setIsConnected(false)
          if (statusRef.current === 'running') {
            reconnectTimer = setTimeout(connect, 2000)
          }
        }
        ws.onerror = () => ws?.close()
        wsRef.current = ws
      } catch {
        reconnectTimer = setTimeout(connect, 2000)
      }
    }

    connect()
    return () => {
      clearTimeout(reconnectTimer)
      ws?.close()
      wsRef.current = null
      setIsConnected(false)
    }
  }, [battleStatus, handleRoundResult])

  // -- spark helpers --
  function spawnSparks(cx: number, cy: number, color: string) {
    const newSparks: Spark[] = []
    for (let i = 0; i < SPARK_COUNT; i++) {
      const angle = (Math.PI * 2 * i) / SPARK_COUNT + Math.random() * 0.4
      const speed = 1.5 + Math.random() * 2
      newSparks.push({ x: cx, y: cy, vx: Math.cos(angle) * speed, vy: Math.sin(angle) * speed, life: 1, color })
    }
    sparksRef.current = [...sparksRef.current, ...newSparks]
  }

  // -- canvas render loop --
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    function draw(now: number) {
      if (!ctx) return

      if (now - lastTickRef.current > ANIM_TICK_MS) {
        frameRef.current = (frameRef.current + 1) % IDLE_FRAMES
        lastTickRef.current = now
      }

      const frame = frameRef.current

      ctx.imageSmoothingEnabled = false
      ctx.fillStyle = '#0a0a1a'
      ctx.fillRect(0, 0, CANVAS_W, CANVAS_H)

      // Arena floor
      ctx.fillStyle = '#0d0d24'
      ctx.fillRect(30, CANVAS_H - 70, CANVAS_W - 60, 50)
      ctx.strokeStyle = '#1E3A5F'
      ctx.lineWidth = 1
      ctx.strokeRect(30, CANVAS_H - 70, CANVAS_W - 60, 50)

      // VS text
      ctx.save()
      ctx.font = 'bold 28px monospace'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      const vsGlow = 0.4 + 0.3 * Math.sin(now / 400)
      ctx.shadowColor = '#FF6B35'
      ctx.shadowBlur = 20 * vsGlow
      ctx.fillStyle = `rgba(255, 107, 53, ${0.6 + vsGlow * 0.4})`
      ctx.fillText('VS', CANVAS_W / 2, FIGHTER_Y + SPRITE_PX / 2)
      ctx.restore()

      // YeyoHack sprite
      const yeyoSheet = yeyoStateRef.current === 'attack' ? yeyoAttackRef.current : yeyoIdleRef.current
      if (yeyoSheet?.isLoaded()) {
        yeyoSheet.drawFrame(ctx, frame % ATTACK_FRAMES, 0, YEYO_X, FIGHTER_Y, SCALE)
      } else {
        ctx.fillStyle = '#EF4444'
        ctx.fillRect(YEYO_X, FIGHTER_Y, SPRITE_PX, SPRITE_PX)
        ctx.fillStyle = '#fff'; ctx.font = '10px monospace'; ctx.textAlign = 'center'
        ctx.fillText('YH', YEYO_X + SPRITE_PX / 2, FIGHTER_Y + SPRITE_PX / 2 + 3)
      }

      // Guardian sprite
      const guardSheet = guardianStateRef.current === 'attack' ? guardianAttackRef.current : guardianIdleRef.current
      if (guardSheet?.isLoaded()) {
        guardSheet.drawFrame(ctx, frame % ATTACK_FRAMES, 0, GUARDIAN_X, FIGHTER_Y, SCALE)
      } else {
        ctx.fillStyle = '#4FC3F7'
        ctx.fillRect(GUARDIAN_X, FIGHTER_Y, SPRITE_PX, SPRITE_PX)
        ctx.fillStyle = '#fff'; ctx.font = '10px monospace'; ctx.textAlign = 'center'
        ctx.fillText('GD', GUARDIAN_X + SPRITE_PX / 2, FIGHTER_Y + SPRITE_PX / 2 + 3)
      }

      // Effects
      const eff = effectRef.current
      const effElapsed = now - eff.startTime
      if (eff.type && effElapsed < EFFECT_DURATION_MS) {
        const effAlpha = 1 - effElapsed / EFFECT_DURATION_MS
        const effSheet = eff.type === 'slash' ? slashRef.current : shieldRef.current
        if (effSheet?.isLoaded()) {
          ctx.save()
          ctx.globalAlpha = effAlpha
          effSheet.drawFrame(ctx, Math.floor((effElapsed / EFFECT_DURATION_MS) * 4) % 4, 0, GUARDIAN_X - 8, FIGHTER_Y - 8, SCALE, 32, 32)
          ctx.restore()
        } else {
          ctx.save()
          ctx.globalAlpha = effAlpha * 0.6
          const effColor = eff.type === 'slash' ? '#EF4444' : '#4FC3F7'
          ctx.shadowColor = effColor; ctx.shadowBlur = 30; ctx.fillStyle = effColor
          ctx.beginPath()
          ctx.arc(GUARDIAN_X + SPRITE_PX / 2, FIGHTER_Y + SPRITE_PX / 2, SPRITE_PX * 0.6, 0, Math.PI * 2)
          ctx.fill()
          ctx.restore()
        }
      } else if (eff.type && effElapsed >= EFFECT_DURATION_MS) {
        effectRef.current = { type: null, startTime: 0 }
      }

      // Sparks
      const liveSparks: Spark[] = []
      for (const s of sparksRef.current) {
        s.x += s.vx; s.y += s.vy; s.vy += 0.08; s.life -= 0.02
        if (s.life > 0) {
          ctx.save()
          ctx.globalAlpha = s.life; ctx.fillStyle = s.color; ctx.shadowColor = s.color; ctx.shadowBlur = 6
          ctx.fillRect(s.x - 1.5, s.y - 1.5, 3, 3)
          ctx.restore()
          liveSparks.push(s)
        }
      }
      sparksRef.current = liveSparks

      // Health bars
      const scores = scoresRef.current
      drawHealthBar(ctx, YEYO_X, FIGHTER_Y - 24, SPRITE_PX, scores.red, '#EF4444', '#7F1D1D')
      drawHealthBar(ctx, GUARDIAN_X, FIGHTER_Y - 24, SPRITE_PX, scores.blue, '#4FC3F7', '#0C4A6E')

      // Labels
      ctx.font = 'bold 10px monospace'; ctx.textAlign = 'center'
      ctx.fillStyle = '#EF4444'
      ctx.fillText('YeyoHack', YEYO_X + SPRITE_PX / 2, FIGHTER_Y - 30)
      ctx.fillStyle = '#4FC3F7'
      ctx.fillText('Guardian', GUARDIAN_X + SPRITE_PX / 2, FIGHTER_Y - 30)

      // Scoreboard
      drawScoreboard(ctx, scores.red, scores.blue, scores.round, now)

      animFrameRef.current = requestAnimationFrame(draw)
    }

    animFrameRef.current = requestAnimationFrame(draw)
    return () => { cancelAnimationFrame(animFrameRef.current) }
  }, [])

  // -- auto-scroll log --
  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: 'smooth' })
  }, [rounds.length])

  // -- API actions --
  async function startBattle() {
    try {
      const res = await fetch(`${API_BASE}/api/v1/arena/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ max_rounds: maxRounds }),
      })
      if (res.ok) {
        setBattleStatus('running')
        setRounds([])
        setRedScore(0)
        setBlueScore(0)
        setCurrentRound(0)
        setLatestAttackCode('')
        setLatestDefenseCode('')
      }
    } catch { /* handle error silently */ }
  }

  async function stopBattle() {
    try {
      const res = await fetch(`${API_BASE}/api/v1/arena/stop`, { method: 'POST' })
      if (res.ok) setBattleStatus('idle')
    } catch { /* handle error silently */ }
  }

  async function pauseBattle() {
    try {
      const res = await fetch(`${API_BASE}/api/v1/arena/pause`, { method: 'POST' })
      if (res.ok) setBattleStatus('paused')
    } catch { /* handle error silently */ }
  }

  async function resumeBattle() {
    try {
      const res = await fetch(`${API_BASE}/api/v1/arena/resume`, { method: 'POST' })
      if (res.ok) setBattleStatus('running')
    } catch { /* handle error silently */ }
  }

  async function exportScripts() {
    try {
      const res = await fetch(`${API_BASE}/api/v1/arena/scripts`)
      if (res.ok) {
        const data = await res.json()
        const blob = new Blob([JSON.stringify(data.data || data, null, 2)], { type: 'application/json' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url; a.download = 'attack_db.json'; a.click()
        URL.revokeObjectURL(url)
      }
    } catch { /* handle error silently */ }
  }

  const currentCode = scriptTab === 'attack' ? latestAttackCode : latestDefenseCode

  // -- render --
  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', backgroundColor: '#060B18' }}>
      {/* Main content: 3 panels */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden', minHeight: 0 }}>

        {/* LEFT PANEL: Script Viewer (30%) */}
        <div style={{
          width: '30%', display: 'flex', flexDirection: 'column',
          borderRight: '1px solid #1E3A5F', overflow: 'hidden',
        }}>
          {/* Script tabs */}
          <div style={{ display: 'flex', borderBottom: '1px solid #1E3A5F', flexShrink: 0 }}>
            <button
              onClick={() => setScriptTab('attack')}
              style={{
                flex: 1, padding: '6px 0', fontSize: 11, fontWeight: 600, border: 'none', cursor: 'pointer',
                background: scriptTab === 'attack' ? '#1a0a0a' : '#0a0a12',
                color: scriptTab === 'attack' ? '#EF4444' : '#556',
                borderBottom: scriptTab === 'attack' ? '2px solid #EF4444' : '2px solid transparent',
              }}
            >
              🔴 Attack Script
            </button>
            <button
              onClick={() => setScriptTab('defense')}
              style={{
                flex: 1, padding: '6px 0', fontSize: 11, fontWeight: 600, border: 'none', cursor: 'pointer',
                background: scriptTab === 'defense' ? '#0a0a1a' : '#0a0a12',
                color: scriptTab === 'defense' ? '#4FC3F7' : '#556',
                borderBottom: scriptTab === 'defense' ? '2px solid #4FC3F7' : '2px solid transparent',
              }}
            >
              🔵 Defense Script
            </button>
          </div>

          {/* Script metadata */}
          <div style={{ padding: '6px 8px', borderBottom: '1px solid #1E3A5F', flexShrink: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
              {latestAttackType && (
                <span style={{
                  fontSize: 10, padding: '2px 6px', borderRadius: 3, fontWeight: 600,
                  background: scriptTab === 'attack' ? '#3B1111' : '#0C2D48',
                  color: scriptTab === 'attack' ? '#EF4444' : '#4FC3F7',
                  border: `1px solid ${scriptTab === 'attack' ? '#7F1D1D' : '#164E63'}`,
                }}>
                  {latestAttackType.toUpperCase()}
                </span>
              )}
              {currentRound > 0 && (
                <span style={{ fontSize: 10, color: '#556' }}>Round {currentRound}</span>
              )}
              {currentRound > 0 && (
                <span style={{
                  fontSize: 10, padding: '1px 5px', borderRadius: 3, fontWeight: 600,
                  background: (scriptTab === 'attack' ? latestSuccess.attack : latestSuccess.defense) ? '#0B3B2B' : '#3B1111',
                  color: (scriptTab === 'attack' ? latestSuccess.attack : latestSuccess.defense) ? '#10B981' : '#EF4444',
                }}>
                  {(scriptTab === 'attack' ? latestSuccess.attack : latestSuccess.defense) ? '✓ SUCCESS' : '✗ FAILED'}
                </span>
              )}
            </div>
          </div>

          {/* Code display */}
          <div style={{
            flex: 1, overflowY: 'auto', overflowX: 'auto', padding: '6px 4px',
            fontFamily: "'Fira Code', 'Cascadia Code', 'Consolas', monospace",
            fontSize: 11, lineHeight: 1.5, backgroundColor: '#0d0d1a',
            whiteSpace: 'pre',
          }}>
            {currentCode ? (
              highlightPython(currentCode)
            ) : (
              <div style={{ color: '#334', textAlign: 'center', padding: 24, whiteSpace: 'normal' }}>
                {battleStatus === 'idle' ? 'Start a battle to see generated scripts' : 'Waiting for first round...'}
              </div>
            )}
          </div>
        </div>

        {/* CENTER PANEL: Canvas Battle (40%) */}
        <div style={{
          width: '40%', display: 'flex', flexDirection: 'column', alignItems: 'center',
          justifyContent: 'center', borderRight: '1px solid #1E3A5F', overflow: 'hidden',
          background: '#080810',
        }}>
          <canvas
            ref={canvasRef}
            width={CANVAS_W}
            height={CANVAS_H}
            style={{
              display: 'block', width: '100%', maxWidth: CANVAS_W, maxHeight: CANVAS_H,
              imageRendering: 'pixelated', background: '#0a0a1a',
            }}
          />
        </div>

        {/* RIGHT PANEL: Battle Log + Stats (30%) */}
        <div style={{
          width: '30%', display: 'flex', flexDirection: 'column', overflow: 'hidden',
        }}>
          {/* Score display */}
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 16,
            padding: '10px 8px', borderBottom: '1px solid #1E3A5F', flexShrink: 0,
          }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 9, color: '#EF4444', fontWeight: 600, letterSpacing: 1 }}>RED TEAM</div>
              <div style={{ fontSize: 28, fontWeight: 800, color: '#EF4444', fontFamily: 'monospace', lineHeight: 1 }}>{redScore}</div>
            </div>
            <div style={{ fontSize: 16, color: '#334', fontWeight: 600 }}>:</div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 9, color: '#4FC3F7', fontWeight: 600, letterSpacing: 1 }}>BLUE TEAM</div>
              <div style={{ fontSize: 28, fontWeight: 800, color: '#4FC3F7', fontFamily: 'monospace', lineHeight: 1 }}>{blueScore}</div>
            </div>
          </div>

          {/* Round counter & status */}
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '4px 8px', borderBottom: '1px solid #1E3A5F', flexShrink: 0,
          }}>
            <span style={{ fontSize: 10, color: '#B0BEC5', fontVariantNumeric: 'tabular-nums' }}>
              Round {currentRound} / {maxRounds}
            </span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{
                width: 6, height: 6, borderRadius: '50%', display: 'inline-block',
                background: battleStatus === 'running' ? '#10B981' : battleStatus === 'paused' ? '#F59E0B' : '#556',
                boxShadow: battleStatus === 'running' ? '0 0 6px #10B981' : 'none',
              }} />
              <span style={{ fontSize: 10, color: '#B0BEC5', textTransform: 'uppercase' }}>{battleStatus}</span>
              {battleStatus === 'running' && (
                <>
                  <span style={{
                    width: 5, height: 5, borderRadius: '50%', display: 'inline-block', marginLeft: 4,
                    background: isConnected ? '#10B981' : '#EF4444',
                  }} />
                  <span style={{ fontSize: 9, color: '#556' }}>{isConnected ? 'LIVE' : 'OFFLINE'}</span>
                </>
              )}
            </div>
          </div>

          {/* Battle log */}
          <div
            ref={logRef}
            style={{
              flex: 1, overflowY: 'auto', padding: '4px 8px',
              fontSize: 10, fontFamily: 'monospace', lineHeight: 1.8,
            }}
          >
            {rounds.length === 0 && (
              <div style={{ color: '#334', textAlign: 'center', padding: 20 }}>
                No rounds yet — start a battle
              </div>
            )}
            {rounds.map((r, i) => {
              const isAttack = r.attack_success
              const isDefense = r.defense_success
              const color = isAttack ? '#EF4444' : isDefense ? '#4FC3F7' : '#556'
              const icon = isAttack ? '🗡️' : isDefense ? '🛡️' : '⚡'
              const result = isAttack ? 'ATK' : isDefense ? 'DEF' : 'DRAW'

              return (
                <div key={i} style={{
                  display: 'flex', gap: 4, padding: '1px 0',
                  borderBottom: '1px solid rgba(30,58,95,0.1)',
                }}>
                  <span style={{ color: '#334', minWidth: 28 }}>R{r.round_number}</span>
                  <span style={{ fontSize: 10 }}>{icon}</span>
                  <span style={{ color: '#8899AA', minWidth: 60, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {r.attack_type || '—'}
                  </span>
                  <span style={{ color, fontWeight: 700, minWidth: 32 }}>{result}</span>
                  {r.attack_duration_ms != null && (
                    <span style={{ color: '#334', marginLeft: 'auto' }}>
                      {Math.round(r.attack_duration_ms + (r.defense_duration_ms || 0))}ms
                    </span>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* BOTTOM: Controls bar */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8, padding: '6px 10px',
        borderTop: '1px solid #1E3A5F', flexShrink: 0, flexWrap: 'wrap',
      }}>
        <button onClick={startBattle} disabled={battleStatus === 'running'} style={btnStyle(battleStatus !== 'running', '#10B981')}>
          ⚔️ Start
        </button>
        <button onClick={stopBattle} disabled={battleStatus === 'idle'} style={btnStyle(battleStatus !== 'idle', '#EF4444')}>
          ⏹️ Stop
        </button>
        <button onClick={pauseBattle} disabled={battleStatus !== 'running'} style={btnStyle(battleStatus === 'running', '#F59E0B')}>
          ⏸️ Pause
        </button>
        <button onClick={resumeBattle} disabled={battleStatus !== 'paused'} style={btnStyle(battleStatus === 'paused', '#10B981')}>
          ▶️ Resume
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginLeft: 4 }}>
          <label style={{ fontSize: 10, color: '#556' }}>Rounds:</label>
          <input
            type="number" min={1} max={10000} value={maxRounds}
            onChange={e => setMaxRounds(Math.max(1, parseInt(e.target.value) || 100))}
            disabled={battleStatus === 'running'}
            style={{
              width: 56, fontSize: 11, padding: '2px 4px', border: '1px solid #1E3A5F',
              borderRadius: 3, background: '#0a0a1a', color: '#B0BEC5', fontFamily: 'monospace',
            }}
          />
        </div>

        <button onClick={exportScripts} style={{
          ...btnStyle(true, '#8B5CF6'), marginLeft: 'auto',
        }}>
          📥 Export Scripts
        </button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Style helpers
// ---------------------------------------------------------------------------

function btnStyle(active: boolean, color: string): React.CSSProperties {
  return {
    background: active ? `${color}18` : '#111',
    color: active ? color : '#334',
    border: `1px solid ${active ? color : '#222'}`,
    borderRadius: 4,
    padding: '4px 10px',
    fontSize: 11,
    fontWeight: 600,
    cursor: active ? 'pointer' : 'not-allowed',
    transition: 'all 0.15s',
    opacity: active ? 1 : 0.5,
  }
}

// ---------------------------------------------------------------------------
// Canvas helpers
// ---------------------------------------------------------------------------

function drawHealthBar(
  ctx: CanvasRenderingContext2D, x: number, y: number, width: number,
  score: number, fg: string, bg: string
) {
  const maxDisplay = Math.max(score, 10)
  const pct = Math.min(score / maxDisplay, 1)
  ctx.fillStyle = bg
  ctx.fillRect(x, y, width, 6)
  ctx.fillStyle = fg
  ctx.fillRect(x, y, width * pct, 6)
  ctx.strokeStyle = '#1E3A5F'; ctx.lineWidth = 0.5
  ctx.strokeRect(x, y, width, 6)
  ctx.font = '9px monospace'; ctx.textAlign = 'center'; ctx.fillStyle = '#fff'
  ctx.fillText(String(score), x + width / 2, y - 2)
}

function drawScoreboard(
  ctx: CanvasRenderingContext2D, red: number, blue: number, round: number, _now: number
) {
  const cx = CANVAS_W / 2
  ctx.save()
  ctx.fillStyle = 'rgba(6, 11, 24, 0.85)'
  ctx.fillRect(cx - 80, 6, 160, 36)
  ctx.strokeStyle = '#1E3A5F'; ctx.lineWidth = 1
  ctx.strokeRect(cx - 80, 6, 160, 36)

  ctx.font = 'bold 18px monospace'; ctx.textAlign = 'right'; ctx.fillStyle = '#EF4444'
  ctx.fillText(String(red), cx - 12, 32)
  ctx.font = 'bold 12px monospace'; ctx.textAlign = 'center'; ctx.fillStyle = '#556'
  ctx.fillText(':', cx, 30)
  ctx.font = 'bold 18px monospace'; ctx.textAlign = 'left'; ctx.fillStyle = '#4FC3F7'
  ctx.fillText(String(blue), cx + 12, 32)
  ctx.font = '8px monospace'; ctx.textAlign = 'center'; ctx.fillStyle = '#556'
  ctx.fillText(`ROUND ${round}`, cx, 15)
  ctx.restore()
}

export default ArenaView
