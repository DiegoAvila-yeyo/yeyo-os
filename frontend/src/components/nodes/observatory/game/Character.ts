/**
 * YeyoOS — Character
 * Animated character that walks around the tile map.
 * Uses Walk.png for movement, Idle.png for idle state.
 */
import { SpriteSheet, Direction, DIRECTION_ROW, FRAME_SIZE } from './SpriteSheet'
import { TILE_SIZE } from './TileMap'

export interface CharacterConfig {
  name: string
  spritePath: string
  startX: number
  startY: number
  building?: string
  color?: string
}

export type CharacterState = 'idle' | 'walking' | 'working' | 'attacking' | 'dead'

interface PathNode {
  x: number
  y: number
  g: number
  h: number
  f: number
  parent: PathNode | null
}

export class Character {
  name: string
  x: number
  y: number
  tileX: number
  tileY: number
  targetTileX: number
  targetTileY: number
  direction: Direction = 'down'
  state: CharacterState = 'idle'
  building: string
  color: string

  private walkSheet: SpriteSheet
  private idleSheet: SpriteSheet
  private attackSheet: SpriteSheet
  private frame = 0
  private animTimer = 0
  private animSpeed = 150
  private moveSpeed = 1.5
  private path: Array<{ x: number; y: number }> = []
  private pathIndex = 0
  private statusText = ''
  private statusTimer = 0

  constructor(config: CharacterConfig) {
    this.name = config.name
    this.tileX = config.startX
    this.tileY = config.startY
    this.targetTileX = config.startX
    this.targetTileY = config.startY
    this.x = config.startX * TILE_SIZE
    this.y = config.startY * TILE_SIZE
    this.building = config.building ?? ''
    this.color = config.color ?? '#FFFFFF'

    this.walkSheet = new SpriteSheet(`${config.spritePath}/Walk.png`)
    this.idleSheet = new SpriteSheet(`${config.spritePath}/Idle.png`)
    this.attackSheet = new SpriteSheet(`${config.spritePath}/Attack.png`)
  }

  async loadSprites(): Promise<void> {
    await Promise.all([
      this.walkSheet.load(),
      this.idleSheet.load(),
      this.attackSheet.load(),
    ])
  }

  update(deltaTime: number): void {
    // Update animation frame timer
    this.animTimer += deltaTime
    if (this.animTimer >= this.animSpeed) {
      this.animTimer -= this.animSpeed
      this.frame = (this.frame + 1) % 4
    }

    // Update status text timer
    if (this.statusTimer > 0) {
      this.statusTimer -= deltaTime
      if (this.statusTimer <= 0) {
        this.statusText = ''
        this.statusTimer = 0
      }
    }

    if (this.state === 'walking') {
      this.updateMovement(deltaTime)
    }
  }

  private updateMovement(deltaTime: number): void {
    if (this.pathIndex >= this.path.length) {
      this.state = 'idle'
      this.tileX = this.targetTileX
      this.tileY = this.targetTileY
      this.x = this.tileX * TILE_SIZE
      this.y = this.tileY * TILE_SIZE
      return
    }

    const target = this.path[this.pathIndex]
    const targetPixelX = target.x * TILE_SIZE
    const targetPixelY = target.y * TILE_SIZE

    const dx = targetPixelX - this.x
    const dy = targetPixelY - this.y
    const dist = Math.sqrt(dx * dx + dy * dy)

    // Determine direction based on movement
    if (Math.abs(dx) > Math.abs(dy)) {
      this.direction = dx > 0 ? 'right' : 'left'
    } else if (dy !== 0) {
      this.direction = dy > 0 ? 'down' : 'up'
    }

    const step = this.moveSpeed * (deltaTime / 16)

    if (dist <= step) {
      this.x = targetPixelX
      this.y = targetPixelY
      this.tileX = target.x
      this.tileY = target.y
      this.pathIndex++
    } else {
      this.x += (dx / dist) * step
      this.y += (dy / dist) * step
    }
  }

  draw(ctx: CanvasRenderingContext2D, cameraX: number, cameraY: number, scale: number): void {
    const screenX = this.x * scale - cameraX
    const screenY = this.y * scale - cameraY
    const spriteSize = FRAME_SIZE * scale

    // Draw shadow
    ctx.save()
    ctx.fillStyle = 'rgba(0, 0, 0, 0.2)'
    ctx.beginPath()
    ctx.ellipse(
      screenX + spriteSize / 2,
      screenY + spriteSize - 2,
      spriteSize / 3,
      spriteSize / 6,
      0, 0, Math.PI * 2
    )
    ctx.fill()
    ctx.restore()

    // Draw sprite
    const sheet = this.state === 'walking' ? this.walkSheet : this.idleSheet
    const row = this.state === 'walking' ? DIRECTION_ROW[this.direction] : 0

    if (sheet.isLoaded()) {
      sheet.drawFrame(ctx, this.frame, row, screenX, screenY, scale)
    } else {
      // Fallback: colored rectangle
      ctx.fillStyle = this.color
      ctx.fillRect(screenX + 4, screenY + 4, spriteSize - 8, spriteSize - 8)
      ctx.strokeStyle = '#FFFFFF'
      ctx.lineWidth = 1
      ctx.strokeRect(screenX + 4, screenY + 4, spriteSize - 8, spriteSize - 8)
    }

    // Name label
    const labelSize = Math.max(8, scale * 2.5)
    ctx.font = `bold ${labelSize}px monospace`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'bottom'

    // Name shadow
    ctx.fillStyle = 'rgba(0, 0, 0, 0.7)'
    ctx.fillText(this.name, screenX + spriteSize / 2 + 1, screenY - 3)
    // Name text
    ctx.fillStyle = this.color
    ctx.fillText(this.name, screenX + spriteSize / 2, screenY - 4)

    // Status text / speech bubble
    if (this.statusText) {
      const statusSize = Math.max(7, scale * 2)
      ctx.font = `${statusSize}px monospace`
      const textWidth = ctx.measureText(this.statusText).width
      const padding = 4

      const bubbleX = screenX + spriteSize / 2 - textWidth / 2 - padding
      const bubbleY = screenY - labelSize - statusSize - 12
      const bubbleW = textWidth + padding * 2
      const bubbleH = statusSize + padding * 2

      // Bubble background
      ctx.fillStyle = 'rgba(0, 0, 0, 0.75)'
      ctx.beginPath()
      const r = 3
      ctx.moveTo(bubbleX + r, bubbleY)
      ctx.lineTo(bubbleX + bubbleW - r, bubbleY)
      ctx.quadraticCurveTo(bubbleX + bubbleW, bubbleY, bubbleX + bubbleW, bubbleY + r)
      ctx.lineTo(bubbleX + bubbleW, bubbleY + bubbleH - r)
      ctx.quadraticCurveTo(bubbleX + bubbleW, bubbleY + bubbleH, bubbleX + bubbleW - r, bubbleY + bubbleH)
      ctx.lineTo(bubbleX + r, bubbleY + bubbleH)
      ctx.quadraticCurveTo(bubbleX, bubbleY + bubbleH, bubbleX, bubbleY + bubbleH - r)
      ctx.lineTo(bubbleX, bubbleY + r)
      ctx.quadraticCurveTo(bubbleX, bubbleY, bubbleX + r, bubbleY)
      ctx.closePath()
      ctx.fill()

      // Pointer
      ctx.beginPath()
      ctx.moveTo(screenX + spriteSize / 2 - 3, bubbleY + bubbleH)
      ctx.lineTo(screenX + spriteSize / 2 + 3, bubbleY + bubbleH)
      ctx.lineTo(screenX + spriteSize / 2, bubbleY + bubbleH + 4)
      ctx.closePath()
      ctx.fill()

      ctx.fillStyle = '#FFFFFF'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'top'
      ctx.fillText(this.statusText, screenX + spriteSize / 2, bubbleY + padding)
    }
  }

  moveTo(tileX: number, tileY: number, grid: number[][]): void {
    this.targetTileX = tileX
    this.targetTileY = tileY
    this.path = this.findPath(this.tileX, this.tileY, tileX, tileY, grid)
    this.pathIndex = 0
    if (this.path.length > 0) {
      this.state = 'walking'
    }
  }

  setStatus(text: string, duration = 3000): void {
    this.statusText = text
    this.statusTimer = duration
  }

  setBuilding(building: string): void {
    this.building = building
  }

  private findPath(
    startX: number,
    startY: number,
    endX: number,
    endY: number,
    grid: number[][]
  ): Array<{ x: number; y: number }> {
    const rows = grid.length
    const cols = grid[0]?.length ?? 0
    if (rows === 0 || cols === 0) return []

    // Clamp endpoints to grid bounds
    const sx = Math.max(0, Math.min(cols - 1, startX))
    const sy = Math.max(0, Math.min(rows - 1, startY))
    const ex = Math.max(0, Math.min(cols - 1, endX))
    const ey = Math.max(0, Math.min(rows - 1, endY))

    // Check if end is walkable; if not, find nearest walkable tile
    const isWalkable = (x: number, y: number): boolean => {
      if (x < 0 || x >= cols || y < 0 || y >= rows) return false
      const tile = grid[y][x]
      return tile === 0 || tile === 2
    }

    let finalX = ex
    let finalY = ey
    if (!isWalkable(ex, ey)) {
      // Find nearest walkable tile to the target
      let bestDist = Infinity
      for (let dy = -2; dy <= 2; dy++) {
        for (let dx = -2; dx <= 2; dx++) {
          const nx = ex + dx
          const ny = ey + dy
          if (isWalkable(nx, ny)) {
            const d = Math.abs(dx) + Math.abs(dy)
            if (d < bestDist) {
              bestDist = d
              finalX = nx
              finalY = ny
            }
          }
        }
      }
      if (bestDist === Infinity) return []
    }

    if (sx === finalX && sy === finalY) return []
    if (!isWalkable(sx, sy)) return []

    // A* implementation
    const heuristic = (ax: number, ay: number, bx: number, by: number): number => {
      return Math.abs(ax - bx) + Math.abs(ay - by)
    }

    const keyOf = (x: number, y: number): string => `${x},${y}`

    const openSet: PathNode[] = []
    const closedSet = new Set<string>()
    const gScores = new Map<string, number>()

    const startNode: PathNode = {
      x: sx,
      y: sy,
      g: 0,
      h: heuristic(sx, sy, finalX, finalY),
      f: heuristic(sx, sy, finalX, finalY),
      parent: null,
    }

    openSet.push(startNode)
    gScores.set(keyOf(sx, sy), 0)

    const directions = [
      { dx: 0, dy: -1 },
      { dx: 0, dy: 1 },
      { dx: -1, dy: 0 },
      { dx: 1, dy: 0 },
    ]

    let iterations = 0
    const maxIterations = cols * rows * 4

    while (openSet.length > 0 && iterations < maxIterations) {
      iterations++

      // Find node with lowest f score
      let lowestIdx = 0
      for (let i = 1; i < openSet.length; i++) {
        if (openSet[i].f < openSet[lowestIdx].f) {
          lowestIdx = i
        }
      }

      const current = openSet[lowestIdx]

      // Check if we reached the goal
      if (current.x === finalX && current.y === finalY) {
        const path: Array<{ x: number; y: number }> = []
        let node: PathNode | null = current
        while (node !== null) {
          path.unshift({ x: node.x, y: node.y })
          node = node.parent
        }
        // Remove start position from path (character is already there)
        if (path.length > 0) path.shift()
        return path
      }

      // Move current from open to closed
      openSet.splice(lowestIdx, 1)
      closedSet.add(keyOf(current.x, current.y))

      // Explore neighbors
      for (const dir of directions) {
        const nx = current.x + dir.dx
        const ny = current.y + dir.dy
        const nKey = keyOf(nx, ny)

        if (!isWalkable(nx, ny)) continue
        if (closedSet.has(nKey)) continue

        const tentativeG = current.g + 1
        const existingG = gScores.get(nKey)

        if (existingG !== undefined && tentativeG >= existingG) continue

        gScores.set(nKey, tentativeG)

        const h = heuristic(nx, ny, finalX, finalY)
        const neighbor: PathNode = {
          x: nx,
          y: ny,
          g: tentativeG,
          h,
          f: tentativeG + h,
          parent: current,
        }

        // Remove existing node in open set with worse g
        const existingIdx = openSet.findIndex((n) => n.x === nx && n.y === ny)
        if (existingIdx !== -1) {
          openSet.splice(existingIdx, 1)
        }

        openSet.push(neighbor)
      }
    }

    return []
  }

  isAt(tileX: number, tileY: number): boolean {
    return this.tileX === tileX && this.tileY === tileY
  }

  getBounds(scale: number): { x: number; y: number; width: number; height: number } {
    return {
      x: this.x * scale,
      y: this.y * scale,
      width: FRAME_SIZE * scale,
      height: FRAME_SIZE * scale,
    }
  }
}
