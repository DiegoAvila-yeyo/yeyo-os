/**
 * YeyoOS — SpriteSheet
 * Loads sprite sheet images and extracts individual frames.
 * Sprites are at /sprites/characters/{name}/ with:
 * - Walk.png: 64x64 → 4 cols (frames) × 4 rows (down/left/right/up), 16x16 per frame
 * - Idle.png: 64x16 → 4 frames horizontal, 16x16 per frame
 * - Attack.png, Dead.png, etc.: similar layouts
 */

export type Direction = 'down' | 'left' | 'right' | 'up'
export const DIRECTION_ROW: Record<Direction, number> = { down: 0, left: 1, right: 2, up: 3 }
export const FRAME_SIZE = 16
export const WALK_COLS = 4
export const WALK_ROWS = 4

export class SpriteSheet {
  private image: HTMLImageElement | null = null
  private loaded = false
  readonly src: string

  constructor(src: string) {
    this.src = src
  }

  async load(): Promise<void> {
    return new Promise<void>((resolve, reject) => {
      const img = new Image()
      img.crossOrigin = 'anonymous'
      img.onload = () => {
        this.image = img
        this.loaded = true
        resolve()
      }
      img.onerror = (_e) => {
        console.warn(`[SpriteSheet] Failed to load: ${this.src}`)
        resolve()
      }
      img.src = this.src
    })
  }

  getFrame(
    col: number,
    row: number,
    frameWidth = FRAME_SIZE,
    frameHeight = FRAME_SIZE
  ): { image: HTMLImageElement; sx: number; sy: number; sw: number; sh: number } | null {
    if (!this.image || !this.loaded) return null
    return {
      image: this.image,
      sx: col * frameWidth,
      sy: row * frameHeight,
      sw: frameWidth,
      sh: frameHeight,
    }
  }

  drawFrame(
    ctx: CanvasRenderingContext2D,
    col: number,
    row: number,
    dx: number,
    dy: number,
    scale = 3,
    frameWidth = FRAME_SIZE,
    frameHeight = FRAME_SIZE
  ): void {
    const frame = this.getFrame(col, row, frameWidth, frameHeight)
    if (!frame) return
    ctx.drawImage(
      frame.image,
      frame.sx,
      frame.sy,
      frame.sw,
      frame.sh,
      dx,
      dy,
      frameWidth * scale,
      frameHeight * scale
    )
  }

  isLoaded(): boolean {
    return this.loaded
  }
}
