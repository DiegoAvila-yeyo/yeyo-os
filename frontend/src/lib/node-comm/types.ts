/**
 * YeyoOS — Node Communication Types
 * Micro-fase 4.6 — Capa 4: Sistema Nervioso
 *
 * Tipos para la comunicación entre nodos por drag & drop.
 */

export type NodeDataType = 'text' | 'image' | 'file' | 'code' | 'pipeline';

export interface NodeDragData {
  sourceNodeId: string;
  dataType: NodeDataType;
  payload: unknown;
  timestamp: number;
}

export interface NodeDropTarget {
  nodeId: string;
  acceptedTypes: NodeDataType[];
  isActive: boolean;
}

export interface NodeTransferEvent {
  source: string;
  target: string;
  dataType: NodeDataType;
  payload: unknown;
  transferId: string;
  timestamp: number;
}

export interface NodeTransferResult {
  transferId: string;
  success: boolean;
  error?: string;
}

export type DragState = 'idle' | 'dragging' | 'over-valid' | 'over-invalid';
