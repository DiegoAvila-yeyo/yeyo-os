/**
 * YeyoOS — ArenaView
 * Canvas 2D battle visualization for YeyoHack vs Guardian.
 * Uses character sprites from /sprites/characters/yeyohack/ and /sprites/characters/guardian/
 * Battle effects from /sprites/effects/
 */
'use client'

import React, { useRef, useEffect, useState, useCallback } from 'react'
import { SpriteSheet, FRAME_SIZE } from './game/SpriteSheet'

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const WS_URL = API_BASE.replace(/^http/, 'ws') + '/api/v1/arena/live'

const CANVAS_W = 640
const CANVAS_H = 400
const SCALE = 3
const SPRITE_PX = FRAME_SIZE * SCALE // 48px rendered size
const IDLE_FRAMES = 4
const ATTACK_FRAMES = 4
const ANIM_TICK_MS = 150
const EFFECT_DURATION_MS = 500
const SPARK_COUNT = 8

// Positions (canvas-space)
const YEYO_X = 100
const GUARDIAN_X = CANVAS_W - 100 - SPRITE_PX
const FIGHTER_Y = CANVAS_H / 2 - SPRITE_PX / 2 + 30

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface RoundResult {
  round_number: number
  attack_type: string
  attack_success: boolean
  defense_success: boolean
  duration_ms?: number
}

type BattleStatus = 'idle' | 'running' | 'paused'

interface Spark {
  x: number
  y: number
  vx: number
  vy: number
  life: number
  color: string
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
  const sparkRef = useRef<SpriteSheet | null>(null)

  // Animation state refs (mutated in rAF loop)
  const frameRef = useRef(0)
  const lastTickRef = useRef(0)
  const yeyoStateRef = useRef<'idle' | 'attack'>('idle')
  const guardianStateRef = useRef<'idle' | 'attack'>('idle')
  const effectRef = useRef<{ type: 'slash' | 'shield' | null; startTime: number }>({
    type: null,
    startTime: 0,
  })
  const sparksRef = useRef<Spark[]>([])
  const scoresRef = useRef({ red: 0, blue: 0, round: 0, streak: 0 })
  const statusRef = useRef<BattleStatus>('idle')

  // Keep refs in sync with state
  useEffect(() => {
    scoresRef.current = { red: redScore, blue: blueScore, round: currentRound, streak: 0 }
  }, [redScore, blueScore, currentRound])
  useEffect(() => {
    statusRef.current = battleStatus
  }, [battleStatus])

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
        { ref: sparkRef, src: '/sprites/effects/Spark.png' },
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
          const data = await res.json()
          if (data.status) setBattleStatus(data.status as BattleStatus)
          if (typeof data.red_score === 'number') setRedScore(data.red_score)
          if (typeof data.blue_score === 'number') setBlueScore(data.blue_score)
          if (typeof data.current_round === 'number') setCurrentRound(data.current_round)
          if (Array.isArray(data.rounds)) setRounds(data.rounds)
        }
      } catch {
        // API may not be up yet
      }
    }
    fetchStatus()
  }, [])

  // -- trigger animation on round result --
  const handleRoundResult = useCallback((result: RoundResult) => {
    setRounds((prev) => [...prev, result])
    setCurrentRound(result.round_number)

    if (result.attack_success) {
      setRedScore((s) => s + 1)
      yeyoStateRef.current = 'attack'
      effectRef.current = { type: 'slash', startTime: performance.now() }
      spawnSparks(GUARDIAN_X + SPRITE_PX / 2, FIGHTER_Y + SPRITE_PX / 2, '#EF4444')
      setTimeout(() => {
        yeyoStateRef.current = 'idle'
      }, EFFECT_DURATION_MS)
    }

    if (result.defense_success) {
      setBlueScore((s) => s + 1)
      guardianStateRef.current = 'attack'
      effectRef.current = { type: 'shield', startTime: performance.now() }
      spawnSparks(GUARDIAN_X + SPRITE_PX / 2, FIGHTER_Y + SPRITE_PX / 2, '#4FC3F7')
      setTimeout(() => {
        guardianStateRef.current = 'idle'
      }, EFFECT_DURATION_MS)
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
            if (event.type === 'round_result' && event.data) {
              handleRoundResult(event.data as RoundResult)
            }
          } catch {
            // ignore non-JSON
          }
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
      newSparks.push({
        x: cx,
        y: cy,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        life: 1,
        color,
      })
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

      // Tick animation frame
      if (now - lastTickRef.current > ANIM_TICK_MS) {
        frameRef.current = (frameRef.current + 1) % IDLE_FRAMES
        lastTickRef.current = now
      }

      const frame = frameRef.current

      // Clear
      ctx.imageSmoothingEnabled = false
      ctx.fillStyle = '#0a0a1a'
      ctx.fillRect(0, 0, CANVAS_W, CANVAS_H)

      // --- Arena floor ---
      ctx.fillStyle = '#0d0d24'
      ctx.fillRect(40, CANVAS_H - 80, CANVAS_W - 80, 60)
      ctx.strokeStyle = '#1E3A5F'
      ctx.lineWidth = 1
      ctx.strokeRect(40, CANVAS_H - 80, CANVAS_W - 80, 60)

      // --- VS text ---
      ctx.save()
      ctx.font = 'bold 36px monospace'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      const vsGlow = 0.4 + 0.3 * Math.sin(now / 400)
      ctx.shadowColor = '#FF6B35'
      ctx.shadowBlur = 20 * vsGlow
      ctx.fillStyle = `rgba(255, 107, 53, ${0.6 + vsGlow * 0.4})`
      ctx.fillText('VS', CANVAS_W / 2, FIGHTER_Y + SPRITE_PX / 2)
      ctx.restore()

      // --- YeyoHack sprite ---
      const yeyoSheet =
        yeyoStateRef.current === 'attack' ? yeyoAttackRef.current : yeyoIdleRef.current
      if (yeyoSheet?.isLoaded()) {
        yeyoSheet.drawFrame(ctx, frame % ATTACK_FRAMES, 0, YEYO_X, FIGHTER_Y, SCALE)
      } else {
        // Fallback rectangle
        ctx.fillStyle = '#EF4444'
        ctx.fillRect(YEYO_X, FIGHTER_Y, SPRITE_PX, SPRITE_PX)
        ctx.fillStyle = '#fff'
        ctx.font = '10px monospace'
        ctx.textAlign = 'center'
        ctx.fillText('YH', YEYO_X + SPRITE_PX / 2, FIGHTER_Y + SPRITE_PX / 2 + 3)
      }

      // --- Guardian sprite ---
      const guardSheet =
        guardianStateRef.current === 'attack'
          ? guardianAttackRef.current
          : guardianIdleRef.current
      if (guardSheet?.isLoaded()) {
        guardSheet.drawFrame(ctx, frame % ATTACK_FRAMES, 0, GUARDIAN_X, FIGHTER_Y, SCALE)
      } else {
        ctx.fillStyle = '#4FC3F7'
        ctx.fillRect(GUARDIAN_X, FIGHTER_Y, SPRITE_PX, SPRITE_PX)
        ctx.fillStyle = '#fff'
        ctx.font = '10px monospace'
        ctx.textAlign = 'center'
        ctx.fillText('GD', GUARDIAN_X + SPRITE_PX / 2, FIGHTER_Y + SPRITE_PX / 2 + 3)
      }

      // --- Effects ---
      const eff = effectRef.current
      const effElapsed = now - eff.startTime
      if (eff.type && effElapsed < EFFECT_DURATION_MS) {
        const effAlpha = 1 - effElapsed / EFFECT_DURATION_MS

        if (eff.type === 'slash' && slashRef.current?.isLoaded()) {
          ctx.save()
          ctx.globalAlpha = effAlpha
          slashRef.current.drawFrame(
            ctx,
            Math.floor((effElapsed / EFFECT_DURATION_MS) * 4) % 4,
            0,
            GUARDIAN_X - 10,
            FIGHTER_Y - 10,
            SCALE,
            32,
            32
          )
          ctx.restore()
        }

        if (eff.type === 'shield' && shieldRef.current?.isLoaded()) {
          ctx.save()
          ctx.globalAlpha = effAlpha
          shieldRef.current.drawFrame(
            ctx,
            Math.floor((effElapsed / EFFECT_DURATION_MS) * 4) % 4,
            0,
            GUARDIAN_X - 6,
            FIGHTER_Y - 6,
            SCALE,
            32,
            32
          )
          ctx.restore()
        }

        // Fallback glow if sprite not loaded
        if (
          (eff.type === 'slash' && !slashRef.current?.isLoaded()) ||
          (eff.type === 'shield' && !shieldRef.current?.isLoaded())
        ) {
          ctx.save()
          ctx.globalAlpha = effAlpha * 0.6
          const effColor = eff.type === 'slash' ? '#EF4444' : '#4FC3F7'
          ctx.shadowColor = effColor
          ctx.shadowBlur = 30
          ctx.fillStyle = effColor
          ctx.beginPath()
          ctx.arc(
            GUARDIAN_X + SPRITE_PX / 2,
            FIGHTER_Y + SPRITE_PX / 2,
            SPRITE_PX * 0.6,
            0,
            Math.PI * 2
          )
          ctx.fill()
          ctx.restore()
        }
      } else if (eff.type && effElapsed >= EFFECT_DURATION_MS) {
        effectRef.current = { type: null, startTime: 0 }
      }

      // --- Sparks ---
      const liveSparks: Spark[] = []
      for (const s of sparksRef.current) {
        s.x += s.vx
        s.y += s.vy
        s.vy += 0.08 // gravity
        s.life -= 0.02
        if (s.life > 0) {
          ctx.save()
          ctx.globalAlpha = s.life
          ctx.fillStyle = s.color
          ctx.shadowColor = s.color
          ctx.shadowBlur = 6
          ctx.fillRect(s.x - 1.5, s.y - 1.5, 3, 3)
          ctx.restore()
          liveSparks.push(s)
        }
      }
      sparksRef.current = liveSparks

      // --- Health / score bars ---
      const scores = scoresRef.current
      drawHealthBar(ctx, YEYO_X, FIGHTER_Y - 24, SPRITE_PX, scores.red, '#EF4444', '#7F1D1D')
      drawHealthBar(
        ctx,
        GUARDIAN_X,
        FIGHTER_Y - 24,
        SPRITE_PX,
        scores.blue,
        '#4FC3F7',
        '#0C4A6E'
      )

      // --- Labels ---
      ctx.font = 'bold 11px monospace'
      ctx.textAlign = 'center'
      ctx.fillStyle = '#EF4444'
      ctx.fillText('YeyoHack', YEYO_X + SPRITE_PX / 2, FIGHTER_Y - 30)
      ctx.fillStyle = '#4FC3F7'
      ctx.fillText('Guardian', GUARDIAN_X + SPRITE_PX / 2, FIGHTER_Y - 30)

      // --- Scoreboard overlay ---
      drawScoreboard(ctx, scores.red, scores.blue, scores.round, now)

      animFrameRef.current = requestAnimationFrame(draw)
    }

    animFrameRef.current = requestAnimationFrame(draw)

    return () => {
      cancelAnimationFrame(animFrameRef.current)
    }
  }, [])

  // -- auto-scroll log --
  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: 'smooth' })
  }, [rounds.length])

  // -- API actions --
  async function startBattle() {
    try {
      const res = await fetch(`${API_BASE}/api/v1/arena/start`, { method: 'POST' })
      if (res.ok) setBattleStatus('running')
    } catch {
      // handle error silently
    }
  }

  async function stopBattle() {
    try {
      const res = await fetch(`${API_BASE}/api/v1/arena/stop`, { method: 'POST' })
      if (res.ok) setBattleStatus('idle')
    } catch {
      // handle error silently
    }
  }

  // -- render --
  return (
    <div
      style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        backgroundColor: '#060B18',
      }}
    >
      {/* Canvas battle scene */}
      <div style={{ position: 'relative', flexShrink: 0 }}>
        <canvas
          ref={canvasRef}
          width={CANVAS_W}
          height={CANVAS_H}
          style={{
            display: 'block',
            width: '100%',
            maxHeight: CANVAS_H,
            imageRendering: 'pixelated',
            background: '#0a0a1a',
            borderBottom: '1px solid #1E3A5F',
          }}
        />
      </div>

      {/* Battle controls */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: '8px 12px',
          borderBottom: '1px solid #1E3A5F',
          flexShrink: 0,
        }}
      >
        <button
          onClick={startBattle}
          disabled={battleStatus === 'running'}
          style={{
            background: battleStatus === 'running' ? '#1a2a1a' : '#1a3a1a',
            color: battleStatus === 'running' ? '#556' : '#10B981',
            border: '1px solid',
            borderColor: battleStatus === 'running' ? '#334' : '#10B981',
            borderRadius: 4,
            padding: '5px 14px',
            fontSize: 12,
            fontWeight: 600,
            cursor: battleStatus === 'running' ? 'not-allowed' : 'pointer',
            transition: 'all 0.15s',
          }}
        >
          ⚔️ Start Battle
        </button>

        <button
          onClick={stopBattle}
          disabled={battleStatus !== 'running'}
          style={{
            background: battleStatus !== 'running' ? '#1a1a1a' : '#3a1a1a',
            color: battleStatus !== 'running' ? '#556' : '#EF4444',
            border: '1px solid',
            borderColor: battleStatus !== 'running' ? '#334' : '#EF4444',
            borderRadius: 4,
            padding: '5px 14px',
            fontSize: 12,
            fontWeight: 600,
            cursor: battleStatus !== 'running' ? 'not-allowed' : 'pointer',
            transition: 'all 0.15s',
          }}
        >
          ⏹️ Stop
        </button>

        {/* Status indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginLeft: 8 }}>
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              background:
                battleStatus === 'running'
                  ? '#10B981'
                  : battleStatus === 'paused'
                    ? '#F59E0B'
                    : '#556',
              boxShadow:
                battleStatus === 'running'
                  ? '0 0 6px #10B981'
                  : battleStatus === 'paused'
                    ? '0 0 6px #F59E0B'
                    : 'none',
              display: 'inline-block',
            }}
          />
          <span style={{ fontSize: 11, color: '#B0BEC5', textTransform: 'uppercase' }}>
            {battleStatus}
          </span>
        </div>

        {/* WS indicator */}
        {battleStatus === 'running' && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginLeft: 'auto' }}>
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                background: isConnected ? '#10B981' : '#EF4444',
                display: 'inline-block',
              }}
            />
            <span style={{ fontSize: 10, color: '#556' }}>
              {isConnected ? 'LIVE' : 'RECONNECTING'}
            </span>
          </div>
        )}

        {/* Round progress */}
        <div
          style={{
            marginLeft: battleStatus !== 'running' ? 'auto' : 0,
            fontSize: 11,
            color: '#556',
            fontVariantNumeric: 'tabular-nums',
          }}
        >
          Round {currentRound}
        </div>
      </div>

      {/* Battle log */}
      <div
        ref={logRef}
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '8px 12px',
          fontSize: 11,
          fontFamily: 'monospace',
          lineHeight: 1.7,
        }}
      >
        {rounds.length === 0 && (
          <div style={{ color: '#334', textAlign: 'center', padding: 24 }}>
            No rounds yet — start a battle to begin
          </div>
        )}
        {rounds.map((r, i) => {
          const isAttack = r.attack_success
          const isDefense = r.defense_success
          const color = isAttack ? '#EF4444' : isDefense ? '#4FC3F7' : '#556'
          const icon = isAttack ? '🗡️' : isDefense ? '🛡️' : '⚡'
          const result = isAttack
            ? 'ATTACK SUCCESS'
            : isDefense
              ? 'DEFENSE SUCCESS'
              : 'DRAW'

          return (
            <div
              key={i}
              style={{
                display: 'flex',
                gap: 8,
                padding: '2px 0',
                borderBottom: '1px solid rgba(30,58,95,0.15)',
              }}
            >
              <span style={{ color: '#334', minWidth: 40 }}>R{r.round_number}</span>
              <span>{icon}</span>
              <span style={{ color: '#B0BEC5', minWidth: 80 }}>{r.attack_type || '—'}</span>
              <span style={{ color, fontWeight: 600 }}>{result}</span>
              {r.duration_ms != null && (
                <span style={{ color: '#334', marginLeft: 'auto' }}>{r.duration_ms}ms</span>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Canvas helpers (pure draw functions)
// ---------------------------------------------------------------------------

function drawHealthBar(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  width: number,
  score: number,
  fg: string,
  bg: string
) {
  const maxDisplay = Math.max(score, 10)
  const pct = Math.min(score / maxDisplay, 1)

  ctx.fillStyle = bg
  ctx.fillRect(x, y, width, 6)
  ctx.fillStyle = fg
  ctx.fillRect(x, y, width * pct, 6)
  ctx.strokeStyle = '#1E3A5F'
  ctx.lineWidth = 0.5
  ctx.strokeRect(x, y, width, 6)

  ctx.font = '9px monospace'
  ctx.textAlign = 'center'
  ctx.fillStyle = '#fff'
  ctx.fillText(String(score), x + width / 2, y - 2)
}

function drawScoreboard(
  ctx: CanvasRenderingContext2D,
  red: number,
  blue: number,
  round: number,
  _now: number
) {
  const cx = CANVAS_W / 2

  // Background panel
  ctx.save()
  ctx.fillStyle = 'rgba(6, 11, 24, 0.85)'
  ctx.fillRect(cx - 100, 8, 200, 42)
  ctx.strokeStyle = '#1E3A5F'
  ctx.lineWidth = 1
  ctx.strokeRect(cx - 100, 8, 200, 42)

  // Red score
  ctx.font = 'bold 22px monospace'
  ctx.textAlign = 'right'
  ctx.fillStyle = '#EF4444'
  ctx.fillText(String(red), cx - 16, 38)

  // Divider
  ctx.font = 'bold 14px monospace'
  ctx.textAlign = 'center'
  ctx.fillStyle = '#556'
  ctx.fillText(':', cx, 36)

  // Blue score
  ctx.font = 'bold 22px monospace'
  ctx.textAlign = 'left'
  ctx.fillStyle = '#4FC3F7'
  ctx.fillText(String(blue), cx + 16, 38)

  // Round counter
  ctx.font = '9px monospace'
  ctx.textAlign = 'center'
  ctx.fillStyle = '#556'
  ctx.fillText(`ROUND ${round}`, cx, 18)

  ctx.restore()
}

export default ArenaView
