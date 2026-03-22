/**
 * YeyoOS — NodeWrapper
 * Micro-fase 5.0 — Capa 5: Órganos
 *
 * Wrapper que proporciona header, minimizar, cerrar, redimensionar
 * a TODOS los nodos del Neural Hub.
 */

'use client';

import React, { useState, useCallback, ReactNode } from 'react';

interface NodeWrapperProps {
  nodeId: string;
  title: string;
  icon?: string;
  children: ReactNode;
  onClose?: (nodeId: string) => void;
  onMinimize?: (nodeId: string) => void;
  initialWidth?: number;
  initialHeight?: number;
  className?: string;
}

interface NodeSize {
  width: number;
  height: number;
}

export default function NodeWrapper({
  nodeId,
  title,
  icon = '📦',
  children,
  onClose,
  onMinimize,
  initialWidth = 600,
  initialHeight = 400,
  className = '',
}: NodeWrapperProps) {
  const [isMinimized, setIsMinimized] = useState(false);
  const [size, setSize] = useState<NodeSize>({
    width: initialWidth,
    height: initialHeight,
  });

  const handleMinimize = useCallback(() => {
    setIsMinimized((prev) => !prev);
    onMinimize?.(nodeId);
  }, [nodeId, onMinimize]);

  const handleClose = useCallback(() => {
    onClose?.(nodeId);
  }, [nodeId, onClose]);

  return (
    <div
      className={`flex flex-col bg-gray-900 border border-gray-700 rounded-lg
                  shadow-xl overflow-hidden relative ${className}`}
      style={{
        width: size.width,
        height: isMinimized ? 40 : size.height,
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2
                      bg-gray-800 border-b border-gray-700 cursor-move
                      select-none shrink-0"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm">{icon}</span>
          <span className="text-sm font-medium text-gray-200 truncate">
            {title}
          </span>
        </div>

        <div className="flex items-center gap-1">
          {/* Minimizar */}
          <button
            onClick={handleMinimize}
            className="w-6 h-6 flex items-center justify-center rounded
                       hover:bg-gray-600 text-gray-400 hover:text-yellow-400
                       transition-colors"
            aria-label="Minimizar"
          >
            <span className="text-xs">─</span>
          </button>

          {/* Cerrar */}
          <button
            onClick={handleClose}
            className="w-6 h-6 flex items-center justify-center rounded
                       hover:bg-red-600 text-gray-400 hover:text-white
                       transition-colors"
            aria-label="Cerrar"
          >
            <span className="text-xs">✕</span>
          </button>
        </div>
      </div>

      {/* Content */}
      {!isMinimized && (
        <div className="flex-1 overflow-auto p-3">
          {children}
        </div>
      )}

      {/* Resize handle */}
      {!isMinimized && (
        <div
          className="absolute bottom-0 right-0 w-4 h-4 cursor-se-resize
                     opacity-50 hover:opacity-100"
          aria-label="Redimensionar"
        >
          <svg viewBox="0 0 16 16" className="w-full h-full text-gray-500">
            <path
              d="M14 14H10M14 14V10M14 8V14H8"
              stroke="currentColor"
              strokeWidth="1.5"
              fill="none"
            />
          </svg>
        </div>
      )}
    </div>
  );
}
