/**
 * YeyoOS — AppLayout (Layout Principal)
 * Micro-fase 3.14 — Capa 3: Cuerpo
 *
 * Layout responsivo: canvas central + paneles colapsables.
 * Mínimo: 1024x768. Canvas siempre toma espacio restante.
 */

'use client';

import { useEffect, useState, type ReactNode } from 'react';
import { useUIStore } from '@/lib/store/ui-store';

export const MIN_WIDTH = 800;
export const MIN_HEIGHT = 500;

export interface AppLayoutProps {
  canvas: ReactNode;
  chatPanel?: ReactNode;
  miniChat?: ReactNode;
  notifications?: ReactNode;
}

export default function AppLayout({
  canvas,
  chatPanel,
  miniChat,
  notifications,
}: AppLayoutProps) {
  const [windowSize, setWindowSize] = useState({ width: 0, height: 0 });
  const { sidebarCollapsed, activePanel } = useUIStore();

  useEffect(() => {
    const updateSize = () => {
      setWindowSize({
        width: window.innerWidth,
        height: window.innerHeight,
      });
    };
    updateSize();
    window.addEventListener('resize', updateSize);
    return () => window.removeEventListener('resize', updateSize);
  }, []);

  const isBelowMinimum =
    windowSize.width > 0 &&
    (windowSize.width < MIN_WIDTH || windowSize.height < MIN_HEIGHT);

  if (isBelowMinimum) {
    return (
      <div
        data-testid="minimum-size-warning"
        className="fixed inset-0 bg-[#0a0a0f] flex items-center justify-center z-[1000]"
      >
        <div className="text-center p-8">
          <p className="text-4xl mb-4">⚠️</p>
          <h2 className="text-white text-xl font-semibold mb-2">
            Pantalla demasiado pequeña
          </h2>
          <p className="text-gray-400 text-sm">
            YeyoOS requiere mínimo {MIN_WIDTH}x{MIN_HEIGHT} píxeles.
          </p>
          <p className="text-gray-500 text-xs mt-2">
            Actual: {windowSize.width}x{windowSize.height}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      data-testid="app-layout"
      className="fixed inset-0 bg-[#0a0a0f] overflow-hidden flex"
    >
      <main
        data-testid="canvas-area"
        className="flex-1 relative overflow-hidden"
      >
        {canvas}
      </main>

      {chatPanel}
      {miniChat}
      {notifications}
    </div>
  );
}
