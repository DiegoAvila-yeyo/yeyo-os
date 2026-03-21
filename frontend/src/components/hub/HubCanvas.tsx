/**
 * YeyoOS — HubCanvas (Viewport Principal del Neural Hub)
 * Micro-fase 3.0 — Capa 3: Cuerpo
 *
 * Canvas PixiJS 8 a pantalla completa que sirve como viewport
 * principal del Neural Hub. Todos los nodos viven aquí.
 */

'use client';

import { useEffect, useRef, useCallback } from 'react';
import { Application } from 'pixi.js';
import { useHubStore } from '@/lib/store/hub-store';

export const BACKGROUND_COLOR = 0x0a0a0f;
export const TARGET_FPS = 60;

export interface HubCanvasProps {
  width?: number;
  height?: number;
}

export default function HubCanvas({ width, height }: HubCanvasProps) {
  const canvasRef = useRef<HTMLDivElement>(null);
  const appRef = useRef<Application | null>(null);
  const setCanvasSize = useHubStore((s) => s.setCanvasSize);

  const initApp = useCallback(async () => {
    if (!canvasRef.current || appRef.current) return;

    const app = new Application();

    await app.init({
      background: BACKGROUND_COLOR,
      resizeTo: width && height ? undefined : window,
      width: width ?? window.innerWidth,
      height: height ?? window.innerHeight,
      antialias: true,
      resolution: window.devicePixelRatio || 1,
      autoDensity: true,
      preferWebGLVersion: 2,
    });

    canvasRef.current.appendChild(app.canvas as HTMLCanvasElement);
    appRef.current = app;

    setCanvasSize({
      width: app.screen.width,
      height: app.screen.height,
    });

    app.ticker.maxFPS = TARGET_FPS;
  }, [width, height, setCanvasSize]);

  const handleResize = useCallback(() => {
    const app = appRef.current;
    if (!app) return;

    if (!width && !height) {
      app.renderer.resize(window.innerWidth, window.innerHeight);
    }

    setCanvasSize({
      width: app.screen.width,
      height: app.screen.height,
    });
  }, [width, height, setCanvasSize]);

  useEffect(() => {
    initApp();

    return () => {
      if (appRef.current) {
        appRef.current.destroy(true);
        appRef.current = null;
      }
    };
  }, [initApp]);

  useEffect(() => {
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [handleResize]);

  return (
    <div
      ref={canvasRef}
      data-testid="hub-canvas"
      style={{
        width: width ? `${width}px` : '100vw',
        height: height ? `${height}px` : '100vh',
        overflow: 'hidden',
        position: 'relative',
      }}
    />
  );
}
