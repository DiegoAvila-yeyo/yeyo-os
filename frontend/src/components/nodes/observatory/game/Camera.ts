/**
 * YeyoOS — Camera
 * 2D viewport camera for the observatory game canvas.
 */

export class Camera {
  x = 0
  y = 0
  targetX = 0
  targetY = 0
  width: number
  height: number
  private smoothing = 0.1

  constructor(width: number, height: number) {
    this.width = width
    this.height = height
  }

  follow(x: number, y: number): void {
    this.targetX = x - this.width / 2
    this.targetY = y - this.height / 2
  }

  update(): void {
    this.x += (this.targetX - this.x) * this.smoothing
    this.y += (this.targetY - this.y) * this.smoothing
  }

  centerOn(x: number, y: number): void {
    this.x = x - this.width / 2
    this.y = y - this.height / 2
    this.targetX = this.x
    this.targetY = this.y
  }

  screenToWorld(screenX: number, screenY: number): { x: number; y: number } {
    return {
      x: screenX + this.x,
      y: screenY + this.y,
    }
  }

  worldToScreen(worldX: number, worldY: number): { x: number; y: number } {
    return {
      x: worldX - this.x,
      y: worldY - this.y,
    }
  }

  resize(width: number, height: number): void {
    this.width = width
    this.height = height
  }
}
