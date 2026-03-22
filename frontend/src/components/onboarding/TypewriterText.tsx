/**
 * YeyoOS — TypewriterText
 * Micro-fase 3.18 — Capa 3: Cuerpo
 *
 * Texto que aparece letra por letra al estilo typewriter.
 * Acepta callback onComplete para encadenar animaciones.
 */

import React, { useEffect, useState, useRef } from 'react'

export interface TypewriterTextProps {
  text: string
  speed?: number          // ms por carácter, default: 50
  onComplete?: () => void
  style?: React.CSSProperties
  className?: string
  /** Si true, muestra cursor parpadeante al final */
  showCursor?: boolean
}

export function TypewriterText({
  text,
  speed = 50,
  onComplete,
  style,
  className,
  showCursor = true,
}: TypewriterTextProps) {
  const [displayed, setDisplayed] = useState('')
  const [done, setDone] = useState(false)
  const indexRef = useRef(0)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    indexRef.current = 0
    setDisplayed('')
    setDone(false)

    const type = () => {
      if (indexRef.current < text.length) {
        indexRef.current++
        setDisplayed(text.slice(0, indexRef.current))
        timerRef.current = setTimeout(type, speed)
      } else {
        setDone(true)
        onComplete?.()
      }
    }

    timerRef.current = setTimeout(type, speed)

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [text, speed])

  return (
    <span
      data-testid="typewriter-text"
      data-complete={done}
      className={className}
      style={style}
    >
      {displayed}
      {showCursor && (
        <span
          data-testid="typewriter-cursor"
          style={{
            display: 'inline-block',
            width: '2px',
            height: '1.1em',
            backgroundColor: '#4FC3F7',
            marginLeft: '2px',
            verticalAlign: 'text-bottom',
            animation: done ? 'blink 1s step-end infinite' : 'none',
          }}
        />
      )}
    </span>
  )
}
