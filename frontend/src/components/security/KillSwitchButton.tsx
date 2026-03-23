/**
 * YeyoOS — Kill Switch Button
 * Micro-fase 6.9 — Capa 6: Sistema Inmune
 */

'use client';

import React, { useState, useCallback } from 'react';

interface KillSwitchButtonProps {
  isPaused: boolean;
  onToggle: () => Promise<void>;
  className?: string;
}

export default function KillSwitchButton({ isPaused, onToggle, className = '' }: KillSwitchButtonProps) {
  const [isToggling, setIsToggling] = useState(false);

  const handleClick = useCallback(async () => {
    if (isToggling) return;
    const confirmed = window.confirm(
      isPaused
        ? '¿Reanudar toda la IA del sistema?'
        : '⚠️ ¿PAUSAR toda la IA del sistema? Esto detendrá todos los procesos de IA.'
    );
    if (!confirmed) return;
    setIsToggling(true);
    try { await onToggle(); } finally { setIsToggling(false); }
  }, [isPaused, onToggle, isToggling]);

  return (
    <button
      onClick={handleClick}
      disabled={isToggling}
      className={`
        relative flex items-center gap-3 px-6 py-4 rounded-xl
        font-bold text-lg transition-all duration-300
        ${isPaused
          ? 'bg-red-600 hover:bg-red-700 text-white shadow-red-500/50 shadow-lg animate-pulse'
          : 'bg-green-600 hover:bg-green-700 text-white shadow-green-500/30 shadow-md'
        }
        ${isToggling ? 'opacity-50 cursor-wait' : 'cursor-pointer'}
        ${className}
      `}
      aria-label={isPaused ? 'Reanudar IA' : 'Pausar IA (Kill Switch)'}
    >
      <span className="text-2xl">{isPaused ? '🔴' : '🟢'}</span>
      <div className="flex flex-col items-start">
        <span className="text-xs uppercase tracking-wider opacity-80">Kill Switch</span>
        <span>
          {isToggling ? 'Procesando...' : isPaused ? 'IA PAUSADA — Click para reanudar' : 'IA Activa — Click para pausar'}
        </span>
      </div>
      {isPaused && <span className="absolute -top-1 -right-1 w-3 h-3 bg-red-400 rounded-full animate-ping" />}
    </button>
  );
}
