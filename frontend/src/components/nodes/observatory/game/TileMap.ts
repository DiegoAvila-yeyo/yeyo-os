/**
 * YeyoOS — TileMap
 * Grid-based tile map renderer. 20x15 grid with 16x16 tiles.
 * Uses town_tilemap.png from /sprites/tiles/
 */

export const TILE_SIZE = 16
export const MAP_WIDTH = 20
export const MAP_HEIGHT = 15

export interface BuildingDef {
  name: string
  tileX: number
  tileY: number
  width: number
  height: number
  color: string
  icon: string
}

export const BUILDINGS: BuildingDef[] = [
  { name: 'Workflow Factory', tileX: 8, tileY: 6, width: 4, height: 3, color: '#6366F1', icon: '🏭' },
  { name: 'Error Mine', tileX: 1, tileY: 1, width: 3, height: 2, color: '#EF4444', icon: '⛏️' },
  { name: 'Lab', tileX: 15, tileY: 1, width: 3, height: 2, color: '#06B6D4', icon: '🔬' },
  { name: 'Library', tileX: 15, tileY: 10, width: 3, height: 2, color: '#8B5CF6', icon: '📚' },
  { name: 'Gym', tileX: 1, tileY: 10, width: 3, height: 2, color: '#F59E0B', icon: '💪' },
  { name: 'Security Station', tileX: 1, tileY: 6, width: 3, height: 2, color: '#10B981', icon: '🛡️' },
  { name: 'Pattern Palace', tileX: 15, tileY: 6, width: 3, height: 2, color: '#EC4899', icon: '🏛️' },
]

export class TileMap {
  private tileImage: HTMLImageElement | null = null
  private grid: number[][] = []
  private loaded = false

  constructor() {
    this.initGrid()
  }

  private initGrid(): void {
    // Initialize with grass (0)
    this.grid = Array.from({ length: MAP_HEIGHT }, () => Array(MAP_WIDTH).fill(0))

    // Edge tiles blocked (1)
    for (let x = 0; x < MAP_WIDTH; x++) {
      this.grid[0][x] = 1
      this.grid[MAP_HEIGHT - 1][x] = 1
    }
    for (let y = 0; y < MAP_HEIGHT; y++) {
      this.grid[y][0] = 1
      this.grid[y][MAP_WIDTH - 1] = 1
    }

    // Mark building positions as 3
    for (const b of BUILDINGS) {
      for (let dy = 0; dy < b.height; dy++) {
        for (let dx = 0; dx < b.width; dx++) {
          const tx = b.tileX + dx
          const ty = b.tileY + dy
          if (tx >= 0 && tx < MAP_WIDTH && ty >= 0 && ty < MAP_HEIGHT) {
            this.grid[ty][tx] = 3
          }
        }
      }
    }

    // Create horizontal path at y=5 connecting left buildings to center
    for (let x = 1; x < MAP_WIDTH - 1; x++) {
      if (this.grid[5][x] === 0) this.grid[5][x] = 2
    }
    // Create horizontal path at y=9 connecting lower buildings
    for (let x = 1; x < MAP_WIDTH - 1; x++) {
      if (this.grid[9][x] === 0) this.grid[9][x] = 2
    }
    // Vertical path at x=5 connecting top to bottom
    for (let y = 1; y < MAP_HEIGHT - 1; y++) {
      if (this.grid[y][5] === 0) this.grid[y][5] = 2
    }
    // Vertical path at x=14 connecting right buildings
    for (let y = 1; y < MAP_HEIGHT - 1; y++) {
      if (this.grid[y][14] === 0) this.grid[y][14] = 2
    }
    // Vertical path at x=10 through center
    for (let y = 1; y < MAP_HEIGHT - 1; y++) {
      if (this.grid[y][10] === 0) this.grid[y][10] = 2
    }
    // Horizontal path at y=12 near bottom buildings
    for (let x = 1; x < MAP_WIDTH - 1; x++) {
      if (this.grid[12][x] === 0) this.grid[12][x] = 2
    }
    // Horizontal path at y=3 near top buildings
    for (let x = 1; x < MAP_WIDTH - 1; x++) {
      if (this.grid[3][x] === 0) this.grid[3][x] = 2
    }
  }

  async load(): Promise<void> {
    return new Promise<void>((resolve) => {
      const img = new Image()
      img.crossOrigin = 'anonymous'
      img.onload = () => {
        this.tileImage = img
        this.loaded = true
        resolve()
      }
      img.onerror = () => {
        console.warn('[TileMap] town_tilemap.png not found, using fallback colors')
        resolve()
      }
      img.src = '/sprites/tiles/town_tilemap.png'
    })
  }

  draw(ctx: CanvasRenderingContext2D, cameraX: number, cameraY: number, scale: number): void {
    const tileScreenSize = TILE_SIZE * scale

    for (let y = 0; y < MAP_HEIGHT; y++) {
      for (let x = 0; x < MAP_WIDTH; x++) {
        const screenX = x * tileScreenSize - cameraX
        const screenY = y * tileScreenSize - cameraY

        // Skip tiles outside viewport
        if (
          screenX + tileScreenSize < 0 ||
          screenY + tileScreenSize < 0 ||
          screenX > ctx.canvas.width ||
          screenY > ctx.canvas.height
        ) {
          continue
        }

        const tile = this.grid[y][x]

        switch (tile) {
          case 0: // Grass
            ctx.fillStyle = ((x + y) % 2 === 0) ? '#4ADE80' : '#22C55E'
            ctx.fillRect(screenX, screenY, tileScreenSize, tileScreenSize)
            break
          case 1: // Blocked / edge
            ctx.fillStyle = '#166534'
            ctx.fillRect(screenX, screenY, tileScreenSize, tileScreenSize)
            break
          case 2: // Path
            ctx.fillStyle = ((x + y) % 2 === 0) ? '#D4A574' : '#C49A6C'
            ctx.fillRect(screenX, screenY, tileScreenSize, tileScreenSize)
            break
          case 3: // Building (drawn separately)
            ctx.fillStyle = '#1a1a2e'
            ctx.fillRect(screenX, screenY, tileScreenSize, tileScreenSize)
            break
        }
      }
    }

    // Draw buildings
    for (const b of BUILDINGS) {
      const bx = b.tileX * tileScreenSize - cameraX
      const by = b.tileY * tileScreenSize - cameraY
      const bw = b.width * tileScreenSize
      const bh = b.height * tileScreenSize

      // Building fill
      ctx.fillStyle = b.color + '33'
      ctx.fillRect(bx, by, bw, bh)

      // Building border
      ctx.strokeStyle = b.color
      ctx.lineWidth = 2
      ctx.strokeRect(bx + 1, by + 1, bw - 2, bh - 2)

      // Roof accent
      ctx.fillStyle = b.color + '66'
      ctx.fillRect(bx + 2, by + 2, bw - 4, 4)

      // Icon
      const iconSize = Math.max(14, scale * 5)
      ctx.font = `${iconSize}px serif`
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText(b.icon, bx + bw / 2, by + bh / 2 - iconSize * 0.3)

      // Name label
      const labelSize = Math.max(8, scale * 2.5)
      ctx.font = `bold ${labelSize}px monospace`
      ctx.fillStyle = '#FFFFFF'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'top'
      ctx.fillText(b.name, bx + bw / 2, by + bh / 2 + iconSize * 0.2)
    }
  }

  getGrid(): number[][] {
    return this.grid
  }

  isWalkable(tileX: number, tileY: number): boolean {
    if (tileX < 0 || tileX >= MAP_WIDTH || tileY < 0 || tileY >= MAP_HEIGHT) return false
    const tile = this.grid[tileY][tileX]
    return tile === 0 || tile === 2
  }

  getBuildingAt(tileX: number, tileY: number): BuildingDef | null {
    for (const b of BUILDINGS) {
      if (
        tileX >= b.tileX &&
        tileX < b.tileX + b.width &&
        tileY >= b.tileY &&
        tileY < b.tileY + b.height
      ) {
        return b
      }
    }
    return null
  }
}
