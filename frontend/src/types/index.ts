// YeyoOS Type Definitions — Micro-fase 0.5

export interface Node {
  id: string;
  type: NodeType;
  position: { x: number; y: number };
  label: string;
  status: 'active' | 'idle' | 'error';
}

export type NodeType =
  | 'central'
  | 'chat'
  | 'image'
  | 'video'
  | 'code'
  | 'automation'
  | 'files'
  | 'browser'
  | 'config';

export interface Memory {
  id: string;
  content: string;
  type: 'conversation' | 'preference' | 'fact' | 'correction';
  tier: 'HOT' | 'WARM' | 'COLD';
  createdAt: Date;
}
