/**
 * YeyoOS — GameEngine
 * Main requestAnimationFrame game loop for the Observatory.
 * Manages characters, tilemap, camera, buildings, and speech bubbles.
 */
import { Character, CharacterConfig } from './Character'
import { TileMap, TILE_SIZE, MAP_WIDTH, MAP_HEIGHT, BUILDINGS } from './TileMap'
import { Camera } from './Camera'
import { Building } from './Building'
import { SpeechBubble } from './SpeechBubble'

export interface GameEvent {
  agent_name: string
  event_type: string
  data?: Record<string, unknown>
  building?: string
}

export interface Particle {
  x: number
  y: number
  vx: number
  vy: number
  life: number
  maxLife: number
  color: string
  size: number
}

const AGENT_BUILDINGS: Record<string, string> = {
  miner: 'Error Mine',
  scientist: 'Lab',
  tester: 'Gym',
  writer: 'Library',
  optimizer: 'Pattern Palace',
  guard: 'Security Station',
  sage: 'Pattern Palace',
  robot: 'Workflow Factory',
}

const DEFAULT_CHARACTERS: CharacterConfig[] = [
  { name: 'miner', spritePath: '/sprites/characters/miner', startX: 2, startY: 2, building: 'Error Mine', color: '#EF4444' },
  { name: 'scientist', spritePath: '/sprites/characters/scientist', startX: 16, startY: 2, building: 'Lab', color: '#06B6D4' },
  { name: 'tester', spritePath: '/sprites/characters/tester', startX: 2, startY: 11, building: 'Gym', color: '#F59E0B' },
  { name: 'writer', spritePath: '/sprites/characters/writer', startX: 16, startY: 11, building: 'Library', color: '#8B5CF6' },
  { name: 'optimizer', spritePath: '/sprites/characters/optimizer', startX: 16, startY: 7, building: 'Pattern Palace', color: '#EC4899' },
  { name: 'guard', spritePath: '/sprites/characters/guard', startX: 2, startY: 7, building: 'Security Station', color: '#10B981' },
  { name: 'sage', spritePath: '/sprites/characters/sage', startX: 14, startY: 7, building: 'Pattern Palace', color: '#F472B6' },
  { name: 'robot', spritePath: '/sprites/characters/robot', startX: 9, startY: 7, building: 'Workflow Factory', color: '#6366F1' },
]

export class GameEngine {
  private canvas: HTMLCanvasElement | null = null
  private ctx: CanvasRenderingContext2D | null = null
  private tileMap: TileMap
  private camera: Camera
  private characters: Map<string, Character> = new Map()
  private buildings: Building[] = []
  private bubbles: SpeechBubble[] = []
  private animFrameId = 0
  private lastTime = 0
  private running = false
  private scale = 3
  private clickHandler: ((e: MouseEvent) => void) | null = null
  private mouseMoveHandler: ((e: MouseEvent) => void) | null = null
  private particles: Particle[] = []
  private nightAlpha = 0
  private selectedBuildingName: string | null = null

  onCharacterClick?: (name: string) => void
  onBuildingClick?: (name: string) => void

  constructor() {
    this.tileMap = new TileMap()
    this.camera = new Camera(0, 0)
  }

  async init(canvas: HTMLCanvasElement): Promise<void> {
    this.canvas = canvas
    this.ctx = canvas.getContext('2d')
    if (!this.ctx) throw new Error('Could not get 2D context')

    this.ctx.imageSmoothingEnabled = false

    // Load tilemap
    await this.tileMap.load()

    // Create buildings
    this.buildings = BUILDINGS.map((def) => new Building(def))

    // Create and load characters
    const loadPromises: Promise<void>[] = []
    for (const config of DEFAULT_CHARACTERS) {
      const character = new Character(config)
      this.characters.set(config.name, character)
      loadPromises.push(character.loadSprites())
    }
    await Promise.all(loadPromises)

    // Center camera on map
    const mapPixelWidth = MAP_WIDTH * TILE_SIZE * this.scale
    const mapPixelHeight = MAP_HEIGHT * TILE_SIZE * this.scale
    this.camera.resize(canvas.width, canvas.height)
    this.camera.centerOn(mapPixelWidth / 2, mapPixelHeight / 2)

    // Add event listeners
    this.clickHandler = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect()
      const screenX = e.clientX - rect.left
      const screenY = e.clientY - rect.top
      this.handleClick(screenX, screenY)
    }
    canvas.addEventListener('click', this.clickHandler)

    this.mouseMoveHandler = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect()
      const screenX = e.clientX - rect.left
      const screenY = e.clientY - rect.top
      this.handleMouseMove(screenX, screenY)
    }
    canvas.addEventListener('mousemove', this.mouseMoveHandler)

    // Start game loop
    this.running = true
    this.lastTime = performance.now()
    this.animFrameId = requestAnimationFrame((t) => this.gameLoop(t))
  }

  private gameLoop(timestamp: number): void {
    if (!this.running || !this.ctx || !this.canvas) return

    const deltaTime = Math.min(timestamp - this.lastTime, 100)
    this.lastTime = timestamp

    // Update
    for (const character of Array.from(this.characters.values())) {
      character.update(deltaTime)
    }

    this.bubbles = this.bubbles.filter((b) => {
      b.update(deltaTime)
      return !b.isExpired()
    })

    this.camera.update(deltaTime)
    this.updateParticles(deltaTime)
    this.nightAlpha = this.getNightAlpha()

    // Camera with shake offset
    const camX = this.camera.x + this.camera.shakeOffsetX
    const camY = this.camera.y + this.camera.shakeOffsetY

    // Clear
    this.ctx.fillStyle = '#0F172A'
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height)

    // Draw tilemap
    this.tileMap.draw(this.ctx, camX, camY, this.scale)

    // Draw buildings overlays (hover/selection effects + selected pulse)
    for (const building of this.buildings) {
      building.draw(this.ctx, camX, camY, this.scale)
      if (building.isSelected) {
        const tileScreenSize = TILE_SIZE * this.scale
        const bx = building.def.tileX * tileScreenSize - camX
        const by = building.def.tileY * tileScreenSize - camY
        const bw = building.def.width * tileScreenSize
        const bh = building.def.height * tileScreenSize
        const pulse = 0.15 + 0.12 * Math.sin(timestamp / 300)
        this.ctx.save()
        this.ctx.globalAlpha = pulse
        this.ctx.fillStyle = building.def.color
        this.ctx.fillRect(bx, by, bw, bh)
        this.ctx.restore()
      }
    }

    // Sort characters by Y for proper depth ordering
    const sortedChars = Array.from(this.characters.values()).sort((a, b) => a.y - b.y)

    for (const character of sortedChars) {
      character.draw(this.ctx, camX, camY, this.scale)
    }

    // Draw particles
    this.drawParticles(this.ctx, camX, camY)

    // Draw speech bubbles
    for (const bubble of this.bubbles) {
      bubble.draw(this.ctx, camX, camY, this.scale)
    }

    // Day/night overlay
    this.drawNightOverlay(this.ctx, this.canvas.width, this.canvas.height)

    this.animFrameId = requestAnimationFrame((t) => this.gameLoop(t))
  }

  spawnParticles(x: number, y: number, count: number, color: string): void {
    for (let i = 0; i < count; i++) {
      const angle = Math.random() * Math.PI * 2
      const speed = 20 + Math.random() * 60
      const life = 600 + Math.random() * 600
      this.particles.push({
        x,
        y,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed - 30,
        life,
        maxLife: life,
        color,
        size: 1.5 + Math.random() * 2.5,
      })
    }
  }

  private getNightAlpha(): number {
    const now = new Date()
    const hour = now.getHours() + now.getMinutes() / 60
    if (hour >= 23.5 || hour < 6.5) return 0.4
    if (hour >= 7.5 && hour < 22.5) return 0
    if (hour >= 22.5 && hour < 23.5) return 0.4 * (hour - 22.5)
    if (hour >= 6.5 && hour < 7.5) return 0.4 * (1 - (hour - 6.5))
    return 0
  }

  private updateParticles(deltaTime: number): void {
    const dtSec = deltaTime / 1000
    for (let i = this.particles.length - 1; i >= 0; i--) {
      const p = this.particles[i]
      p.x += p.vx * dtSec
      p.y += p.vy * dtSec
      p.vy += 50 * dtSec
      p.life -= deltaTime
      if (p.life <= 0) {
        this.particles.splice(i, 1)
      }
    }
  }

  private drawParticles(ctx: CanvasRenderingContext2D, camX: number, camY: number): void {
    for (const p of this.particles) {
      const alpha = Math.max(0, p.life / p.maxLife)
      ctx.save()
      ctx.globalAlpha = alpha
      ctx.fillStyle = p.color
      ctx.beginPath()
      ctx.arc(p.x - camX, p.y - camY, p.size, 0, Math.PI * 2)
      ctx.fill()
      ctx.restore()
    }
  }

  private drawNightOverlay(ctx: CanvasRenderingContext2D, width: number, height: number): void {
    if (this.nightAlpha <= 0) return

    ctx.save()
    ctx.fillStyle = `rgba(0, 0, 30, ${this.nightAlpha})`
    ctx.fillRect(0, 0, width, height)

    // Subtle glow around buildings at night
    const tileScreenSize = TILE_SIZE * this.scale
    const camX = this.camera.x + this.camera.shakeOffsetX
    const camY = this.camera.y + this.camera.shakeOffsetY
    for (const b of this.buildings) {
      const bx = b.def.tileX * tileScreenSize - camX
      const by = b.def.tileY * tileScreenSize - camY
      const bw = b.def.width * tileScreenSize
      const bh = b.def.height * tileScreenSize
      const gradient = ctx.createRadialGradient(
        bx + bw / 2, by + bh / 2, bw * 0.2,
        bx + bw / 2, by + bh / 2, bw * 0.8
      )
      gradient.addColorStop(0, `rgba(255, 200, 100, ${this.nightAlpha * 0.3})`)
      gradient.addColorStop(1, 'rgba(255, 200, 100, 0)')
      ctx.fillStyle = gradient
      ctx.fillRect(bx - bw * 0.3, by - bh * 0.3, bw * 1.6, bh * 1.6)
    }

    // Glow around characters at night
    for (const character of Array.from(this.characters.values())) {
      const sx = character.x * this.scale - camX
      const sy = character.y * this.scale - camY
      const gradient = ctx.createRadialGradient(sx + 24, sy + 24, 4, sx + 24, sy + 24, 30)
      gradient.addColorStop(0, `rgba(255, 220, 150, ${this.nightAlpha * 0.25})`)
      gradient.addColorStop(1, 'rgba(255, 220, 150, 0)')
      ctx.fillStyle = gradient
      ctx.fillRect(sx - 6, sy - 6, 60, 60)
    }

    ctx.restore()
  }

  handleEvent(event: GameEvent): void {
    const character = this.characters.get(event.agent_name)
    if (!character) return

    const grid = this.tileMap.getGrid()
    const buildingName = event.building ?? AGENT_BUILDINGS[event.agent_name] ?? ''

    switch (event.event_type) {
      case 'task_start': {
        // Walk to assigned building
        const targetBuilding = this.buildings.find((b) => b.def.name === buildingName)
        if (targetBuilding) {
          // Move to tile adjacent to building (bottom-center)
          const targetX = targetBuilding.def.tileX + Math.floor(targetBuilding.def.width / 2)
          const targetY = targetBuilding.def.tileY + targetBuilding.def.height
          character.moveTo(targetX, targetY, grid)
          character.setStatus(`→ ${buildingName}`, 4000)
          targetBuilding.addActivity(event.agent_name, event.data?.action as string ?? 'working')
        }
        break
      }
      case 'task_complete': {
        character.setStatus('✅ Done!', 3000)
        this.spawnParticles(
          character.x * this.scale,
          character.y * this.scale,
          15,
          '#FFD700'
        )
        const bld = this.buildings.find((b) => b.def.name === buildingName)
        if (bld) {
          bld.addActivity(event.agent_name, 'completed')
        }
        // Add celebration bubble
        const bubble = new SpeechBubble(
          event.data?.message as string ?? 'Task complete!',
          character.x * this.scale,
          character.y * this.scale,
          4000,
          5
        )
        this.bubbles.push(bubble)
        break
      }
      case 'error': {
        character.setStatus('❌ Error!', 4000)
        this.spawnParticles(
          character.x * this.scale,
          character.y * this.scale,
          12,
          '#EF4444'
        )
        const errorBubble = new SpeechBubble(
          event.data?.message as string ?? 'Something went wrong',
          character.x * this.scale,
          character.y * this.scale,
          5000,
          15
        )
        this.bubbles.push(errorBubble)
        break
      }
      case 'idle': {
        character.setStatus('💤 Idle', 2000)
        break
      }
      default: {
        if (event.data?.message) {
          character.setStatus(event.data.message as string, 3000)
        }
        break
      }
    }
  }

  private handleClick(screenX: number, screenY: number): void {
    const world = this.camera.screenToWorld(screenX, screenY)

    // Check characters
    for (const character of Array.from(this.characters.values())) {
      const bounds = character.getBounds(this.scale)
      if (
        world.x >= bounds.x &&
        world.x < bounds.x + bounds.width &&
        world.y >= bounds.y &&
        world.y < bounds.y + bounds.height
      ) {
        const emoteIdx = Math.floor(Math.random() * 16)
        const bubble = new SpeechBubble(
          '👋',
          character.x * this.scale,
          character.y * this.scale,
          2000,
          emoteIdx
        )
        this.bubbles.push(bubble)
        this.onCharacterClick?.(character.name)
        return
      }
    }

    // Check buildings
    for (const building of this.buildings) {
      if (building.containsPoint(world.x, world.y, this.scale)) {
        building.isSelected = !building.isSelected
        this.selectedBuildingName = building.isSelected ? building.def.name : null
        // Deselect others
        for (const b of this.buildings) {
          if (b !== building) b.isSelected = false
        }
        this.onBuildingClick?.(building.def.name)
        return
      }
    }

    // Click on ground: move nearest character? or deselect
    for (const b of this.buildings) {
      b.isSelected = false
    }
  }

  private handleMouseMove(screenX: number, screenY: number): void {
    const world = this.camera.screenToWorld(screenX, screenY)
    for (const building of this.buildings) {
      building.isHovered = building.containsPoint(world.x, world.y, this.scale)
    }
  }

  getCharacter(name: string): Character | undefined {
    return this.characters.get(name)
  }

  getBuilding(name: string): Building | undefined {
    return this.buildings.find((b) => b.def.name === name)
  }

  resize(width: number, height: number): void {
    if (this.canvas) {
      this.canvas.width = width
      this.canvas.height = height
      if (this.ctx) {
        this.ctx.imageSmoothingEnabled = false
      }
    }
    this.camera.resize(width, height)
  }

  destroy(): void {
    this.running = false
    if (this.animFrameId) {
      cancelAnimationFrame(this.animFrameId)
      this.animFrameId = 0
    }
    if (this.canvas && this.clickHandler) {
      this.canvas.removeEventListener('click', this.clickHandler)
    }
    if (this.canvas && this.mouseMoveHandler) {
      this.canvas.removeEventListener('mousemove', this.mouseMoveHandler)
    }
    this.clickHandler = null
    this.mouseMoveHandler = null
    this.canvas = null
    this.ctx = null
    this.characters.clear()
    this.buildings = []
    this.bubbles = []
    this.particles = []
  }
}
