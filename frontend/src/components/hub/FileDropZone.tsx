/**
 * YeyoOS — FileDropZone (Zona de Drop de Archivos)
 * Micro-fase 3.7 — Capa 3: Cuerpo
 *
 * Overlay global para drag & drop de archivos sobre el canvas.
 * Rutea archivos al nodo apropiado segun su tipo.
 */
'use client';

import { useState, useCallback, type DragEvent } from 'react';

export type FileCategory = 'image' | 'text' | 'code' | 'pdf' | 'audio' | 'video' | 'unknown';

export interface DroppedFile {
  file: File;
  category: FileCategory;
}

export interface FileDropZoneProps {
  onFileDrop: (droppedFile: DroppedFile) => void;
  onError?: (message: string) => void;
  maxSizeMB?: number;
  children: React.ReactNode;
}

export const MAX_SIZE_MB = 100;
export const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;

export const MIME_CATEGORIES: Record<string, FileCategory> = {
  'image/jpeg': 'image',
  'image/png': 'image',
  'image/gif': 'image',
  'image/webp': 'image',
  'image/svg+xml': 'image',
  'text/plain': 'text',
  'text/html': 'text',
  'text/css': 'code',
  'text/javascript': 'code',
  'application/javascript': 'code',
  'application/typescript': 'code',
  'application/json': 'code',
  'application/xml': 'code',
  'application/pdf': 'pdf',
  'audio/mpeg': 'audio',
  'audio/wav': 'audio',
  'audio/ogg': 'audio',
  'audio/webm': 'audio',
  'video/mp4': 'video',
  'video/webm': 'video',
  'video/ogg': 'video',
};

export const EXT_CATEGORIES: Record<string, FileCategory> = {
  '.ts': 'code',
  '.tsx': 'code',
  '.js': 'code',
  '.jsx': 'code',
  '.py': 'code',
  '.rs': 'code',
  '.go': 'code',
  '.java': 'code',
  '.cpp': 'code',
  '.c': 'code',
  '.h': 'code',
  '.md': 'text',
  '.txt': 'text',
  '.csv': 'text',
};

export const CATEGORY_ICONS: Record<FileCategory, string> = {
  image: '🖼️',
  text: '📄',
  code: '💻',
  pdf: '📕',
  audio: '🎵',
  video: '🎬',
  unknown: '📎',
};

export function categorizeFile(file: File): FileCategory {
  const mimeCategory = MIME_CATEGORIES[file.type];
  if (mimeCategory) return mimeCategory;

  const ext = '.' + file.name.split('.').pop()?.toLowerCase();
  const extCategory = EXT_CATEGORIES[ext];
  if (extCategory) return extCategory;

  return 'unknown';
}

export default function FileDropZone({
  onFileDrop,
  onError,
  maxSizeMB = MAX_SIZE_MB,
  children,
}: FileDropZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [dragFileName, setDragFileName] = useState<string | null>(null);
  const [dragCategory, setDragCategory] = useState<FileCategory | null>(null);

  const maxBytes = maxSizeMB * 1024 * 1024;

  const handleDragEnter = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);

    const items = e.dataTransfer.items;
    if (items.length > 0 && items[0].kind === 'file') {
      const entry = items[0].getAsFile();
      if (entry) {
        setDragFileName(entry.name);
        setDragCategory(categorizeFile(entry));
      }
    }
  }, []);

  const handleDragOver = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDragLeave = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.currentTarget === e.target) {
      setIsDragOver(false);
      setDragFileName(null);
      setDragCategory(null);
    }
  }, []);

  const handleDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragOver(false);
      setDragFileName(null);
      setDragCategory(null);

      const files = e.dataTransfer.files;
      if (files.length === 0) return;

      const file = files[0];

      if (file.size > maxBytes) {
        onError?.(`Archivo demasiado grande: ${(file.size / 1024 / 1024).toFixed(1)}MB. Maximo: ${maxSizeMB}MB.`);
        return;
      }

      const category = categorizeFile(file);
      onFileDrop({ file, category });
    },
    [maxBytes, maxSizeMB, onFileDrop, onError]
  );

  return (
    <div
      data-testid="file-drop-zone"
      className="relative w-full h-full"
      onDragEnter={handleDragEnter}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {children}
      {isDragOver && (
        <div
          data-testid="drop-overlay"
          className="absolute inset-0 bg-blue-500/10 border-2 border-dashed border-blue-400 rounded-xl z-[100] flex items-center justify-center backdrop-blur-sm"
        >
          <div className="text-center">
            <p className="text-4xl mb-2">
              {dragCategory ? CATEGORY_ICONS[dragCategory] : '📎'}
            </p>
            <p className="text-blue-300 text-lg font-medium">Soltar archivo aqui</p>
            {dragFileName && (
              <p className="text-blue-400/70 text-sm mt-1">{dragFileName}</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
