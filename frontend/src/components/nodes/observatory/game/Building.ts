/**
 * YeyoOS — Building
 * Interactive building in the observatory town.
 */
import { BuildingDef, TILE_SIZE } from './TileMap'

export interface BuildingActivity {
  agent: string
  action: string
  timestamp: number
}

export class Building {
  def: BuildingDef
  activities: BuildingActivity[] = []
  isHovered = false
  isSelected = false

  constructor(def: BuildingDef) {
    this.def = def
  }

  addActivity(agent: string, action: string): void {
    this.activities.unshift({
      agent,
      action,
      timestamp: Date.now(),
    })
    if (this.activities.length > 10) {
      this.activities.length = 10
    }
  }

  draw(ctx: CanvasRenderingContext2D, cameraX: number, cameraY: number, scale: number): void {
    const tileScreenSize = TILE_SIZE * scale
    const bx = this.def.tileX * tileScreenSize - cameraX
    const by = this.def.tileY * tileScreenSize - cameraY
    const bw = this.def.width * tileScreenSize
    const bh = this.def.height * tileScreenSize

    // Hover glow
    if (this.isHovered) {
      ctx.save()
      ctx.shadowColor = this.def.color
      ctx.shadowBlur = 12
      ctx.fillStyle = this.def.color + '22'
      ctx.fillRect(bx - 2, by - 2, bw + 4, bh + 4)
      ctx.restore()
    }

    // Selection border
    if (this.isSelected) {
      ctx.save()
      ctx.strokeStyle = '#FFFFFF'
      ctx.lineWidth = 3
      ctx.setLineDash([6, 3])
      ctx.strokeRect(bx - 2, by - 2, bw + 4, bh + 4)
      ctx.setLineDash([])
      ctx.restore()
    }

    // Activity indicator: pulsing dot if recent activity
    if (this.activities.length > 0) {
      const latest = this.activities[0]
      const age = Date.now() - latest.timestamp
      if (age < 5000) {
        const pulse = 0.5 + 0.5 * Math.sin(Date.now() / 200)
        ctx.save()
        ctx.globalAlpha = pulse
        ctx.fillStyle = '#22D3EE'
        ctx.beginPath()
        ctx.arc(bx + bw - 6, by + 6, 4, 0, Math.PI * 2)
        ctx.fill()
        ctx.restore()
      }
    }
  }

  containsPoint(worldX: number, worldY: number, scale: number): boolean {
    const tileScreenSize = TILE_SIZE * scale
    const bx = this.def.tileX * tileScreenSize
    const by = this.def.tileY * tileScreenSize
    const bw = this.def.width * tileScreenSize
    const bh = this.def.height * tileScreenSize
    return worldX >= bx && worldX < bx + bw && worldY >= by && worldY < by + bh
  }

  getScreenBounds(
    cameraX: number,
    cameraY: number,
    scale: number
  ): { x: number; y: number; width: number; height: number } {
    const tileScreenSize = TILE_SIZE * scale
    return {
      x: this.def.tileX * tileScreenSize - cameraX,
      y: this.def.tileY * tileScreenSize - cameraY,
      width: this.def.width * tileScreenSize,
      height: this.def.height * tileScreenSize,
    }
  }
}
