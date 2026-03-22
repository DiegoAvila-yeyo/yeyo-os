/**
 * YeyoOS — Image Generation Node Frontend
 * Micro-fase 5.2 — Capa 5: Órganos
 */

'use client';

import React, { useState } from 'react';
import NodeWrapper from '../NodeWrapper';

interface GalleryItem {
  id: string;
  prompt: string;
  resolution: string;
  created_at: string;
}

interface ImageGenerationNodeProps {
  nodeId: string;
  styles: string[];
  resolutions: string[];
  gallery: GalleryItem[];
  isGenerating: boolean;
  onGenerate: (prompt: string, style: string, resolution: string) => void;
  onImageClick: (imageId: string) => void;
  onClose: (nodeId: string) => void;
}

export default function ImageGenerationNode({
  nodeId,
  styles,
  resolutions,
  gallery,
  isGenerating,
  onGenerate,
  onImageClick,
  onClose,
}: ImageGenerationNodeProps) {
  const [prompt, setPrompt] = useState('');
  const [style, setStyle] = useState('none');
  const [resolution, setResolution] = useState('512x512');

  const handleGenerate = () => {
    if (!prompt.trim()) return;
    onGenerate(prompt.trim(), style, resolution);
  };

  return (
    <NodeWrapper nodeId={nodeId} title="Image Generation" icon="🎨" onClose={onClose}>
      <div className="flex flex-col h-full gap-3">
        {/* Prompt input */}
        <div className="space-y-2">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Describe la imagen que quieres generar..."
            rows={3}
            className="w-full px-3 py-2 text-sm bg-gray-700 text-white
                       rounded-lg border border-gray-600 focus:border-purple-500
                       focus:outline-none resize-none"
          />
          <div className="flex gap-2">
            {/* Style selector */}
            <select
              value={style}
              onChange={(e) => setStyle(e.target.value)}
              className="flex-1 px-2 py-1 text-sm bg-gray-700 text-white
                         rounded border border-gray-600"
            >
              {styles.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>

            {/* Resolution selector */}
            <select
              value={resolution}
              onChange={(e) => setResolution(e.target.value)}
              className="flex-1 px-2 py-1 text-sm bg-gray-700 text-white
                         rounded border border-gray-600"
            >
              {resolutions.map((r) => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          </div>
          <button
            onClick={handleGenerate}
            disabled={!prompt.trim() || isGenerating}
            className="w-full px-4 py-2 bg-purple-600 text-white rounded-lg
                       text-sm font-medium hover:bg-purple-500
                       disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isGenerating ? '⏳ Generando...' : '🎨 Generar Imagen'}
          </button>
        </div>

        {/* Gallery */}
        <div className="flex-1 overflow-y-auto">
          <h3 className="text-xs text-gray-400 mb-2">Galería</h3>
          <div className="grid grid-cols-2 gap-2">
            {gallery.map((item) => (
              <div
                key={item.id}
                onClick={() => onImageClick(item.id)}
                className="cursor-pointer rounded-lg border border-gray-600
                           hover:border-purple-500 overflow-hidden bg-gray-800"
              >
                <div className="aspect-square bg-gray-700 flex items-center
                                justify-center text-2xl">
                  🖼️
                </div>
                <p className="text-xs text-gray-400 p-1 truncate">{item.prompt}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </NodeWrapper>
  );
}
