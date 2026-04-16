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
  private smoothing = 0.05
  private shakeIntensity = 0
  private shakeDuration = 0
  private shakeTimer = 0
  shakeOffsetX = 0
  shakeOffsetY = 0

  constructor(width: number, height: number) {
    this.width = width
    this.height = height
  }

  follow(x: number, y: number): void {
    this.targetX = x - this.width / 2
    this.targetY = y - this.height / 2
  }

  panTo(worldX: number, worldY: number): void {
    this.targetX = worldX - this.width / 2
    this.targetY = worldY - this.height / 2
  }

  shake(intensity: number, duration: number): void {
    this.shakeIntensity = intensity
    this.shakeDuration = duration
    this.shakeTimer = duration
  }

  update(deltaTime: number): void {
    // Frame-rate independent smooth interpolation
    const dtSec = deltaTime / 1000
    const t = 1 - Math.exp(-this.smoothing * 60 * dtSec)
    this.x += (this.targetX - this.x) * t
    this.y += (this.targetY - this.y) * t

    // Screen shake
    if (this.shakeTimer > 0) {
      this.shakeTimer -= deltaTime
      const decay = Math.max(0, this.shakeTimer / this.shakeDuration)
      const intensity = this.shakeIntensity * decay
      this.shakeOffsetX = (Math.random() * 2 - 1) * intensity
      this.shakeOffsetY = (Math.random() * 2 - 1) * intensity
    } else {
      this.shakeOffsetX = 0
      this.shakeOffsetY = 0
    }
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
