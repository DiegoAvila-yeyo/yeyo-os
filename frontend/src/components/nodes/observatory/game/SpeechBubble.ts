/**
 * YeyoOS — SpeechBubble
 * RPG-style speech bubbles using emote sprites from /sprites/ui/
 */

export class SpeechBubble {
  text: string
  emoteIndex: number | null
  x: number
  y: number
  duration: number
  private timer = 0
  private emoteImage: HTMLImageElement | null = null
  private alpha = 1

  constructor(text: string, x: number, y: number, duration = 3000, emoteIndex?: number) {
    this.text = text
    this.x = x
    this.y = y
    this.duration = duration
    this.emoteIndex = emoteIndex ?? null
    if (this.emoteIndex !== null) {
      this.loadEmote()
    }
  }

  async loadEmote(): Promise<void> {
    if (this.emoteIndex === null) return
    return new Promise<void>((resolve) => {
      const img = new Image()
      img.crossOrigin = 'anonymous'
      img.onload = () => {
        this.emoteImage = img
        resolve()
      }
      img.onerror = () => resolve()
      img.src = `/sprites/ui/emote${this.emoteIndex}.png`
    })
  }

  update(deltaTime: number): void {
    this.timer += deltaTime
    const remaining = this.duration - this.timer
    const fadeStart = 500
    if (remaining < fadeStart && remaining > 0) {
      this.alpha = remaining / fadeStart
    } else if (remaining <= 0) {
      this.alpha = 0
    } else {
      this.alpha = 1
    }
  }

  draw(ctx: CanvasRenderingContext2D, cameraX: number, cameraY: number, scale: number): void {
    if (this.alpha <= 0) return

    const screenX = this.x - cameraX
    const screenY = this.y - cameraY - 24 * scale

    ctx.save()
    ctx.globalAlpha = this.alpha

    const padding = 6
    const fontSize = Math.max(10, scale * 3.5)
    ctx.font = `bold ${fontSize}px monospace`
    const textWidth = ctx.measureText(this.text).width
    const emoteSize = this.emoteImage ? 16 * scale * 0.5 : 0
    const totalWidth = textWidth + (emoteSize > 0 ? emoteSize + 4 : 0)

    const bx = screenX - totalWidth / 2 - padding
    const by = screenY - fontSize - padding
    const bw = totalWidth + padding * 2
    const bh = fontSize + padding * 2

    // Bubble background
    ctx.fillStyle = 'rgba(0, 0, 0, 0.8)'
    ctx.beginPath()
    const r = 4
    ctx.moveTo(bx + r, by)
    ctx.lineTo(bx + bw - r, by)
    ctx.quadraticCurveTo(bx + bw, by, bx + bw, by + r)
    ctx.lineTo(bx + bw, by + bh - r)
    ctx.quadraticCurveTo(bx + bw, by + bh, bx + bw - r, by + bh)
    ctx.lineTo(bx + r, by + bh)
    ctx.quadraticCurveTo(bx, by + bh, bx, by + bh - r)
    ctx.lineTo(bx, by + r)
    ctx.quadraticCurveTo(bx, by, bx + r, by)
    ctx.closePath()
    ctx.fill()

    // Pointer triangle
    ctx.beginPath()
    ctx.moveTo(screenX - 4, by + bh)
    ctx.lineTo(screenX + 4, by + bh)
    ctx.lineTo(screenX, by + bh + 6)
    ctx.closePath()
    ctx.fill()

    // Border
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)'
    ctx.lineWidth = 1
    ctx.stroke()

    // Emote image
    let textStartX = screenX - totalWidth / 2
    if (this.emoteImage) {
      ctx.drawImage(this.emoteImage, textStartX, by + padding - 2, emoteSize, emoteSize)
      textStartX += emoteSize + 4
    }

    // Text
    ctx.fillStyle = '#FFFFFF'
    ctx.textAlign = 'left'
    ctx.textBaseline = 'top'
    ctx.fillText(this.text, textStartX, by + padding)

    ctx.restore()
  }

  isExpired(): boolean {
    return this.timer >= this.duration
  }
}
