/**
 * YeyoOS — Node Drag & Drop Communication
 * Micro-fase 4.6 — Capa 4: Sistema Nervioso
 *
 * Drag & drop entre nodos satélite del Neural Hub.
 * Emite eventos al backend para procesamiento.
 */

import type {
  NodeDataType,
  NodeDragData,
  NodeDropTarget,
  NodeTransferEvent,
  NodeTransferResult,
  DragState,
} from './types';

function generateTransferId(): string {
  return `transfer-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export type TransferCallback = (event: NodeTransferEvent) => Promise<NodeTransferResult>;

export class NodeDragDropManager {
  private dropTargets: Map<string, NodeDropTarget> = new Map();
  private currentDrag: NodeDragData | null = null;
  private dragState: DragState = 'idle';
  private transferCallback: TransferCallback | null = null;
  private transferHistory: NodeTransferEvent[] = [];

  setTransferCallback(callback: TransferCallback): void {
    this.transferCallback = callback;
  }

  registerDropTarget(
    nodeId: string,
    acceptedTypes: NodeDataType[],
  ): void {
    this.dropTargets.set(nodeId, {
      nodeId,
      acceptedTypes,
      isActive: true,
    });
  }

  unregisterDropTarget(nodeId: string): void {
    this.dropTargets.delete(nodeId);
  }

  getDropTargets(): NodeDropTarget[] {
    return Array.from(this.dropTargets.values()).filter((t) => t.isActive);
  }

  startDrag(sourceNodeId: string, dataType: NodeDataType, payload: unknown): NodeDragData {
    this.currentDrag = {
      sourceNodeId,
      dataType,
      payload,
      timestamp: Date.now(),
    };
    this.dragState = 'dragging';
    return this.currentDrag;
  }

  cancelDrag(): void {
    this.currentDrag = null;
    this.dragState = 'idle';
  }

  getDragState(): DragState {
    return this.dragState;
  }

  getCurrentDrag(): NodeDragData | null {
    return this.currentDrag;
  }

  isValidDropTarget(targetNodeId: string): boolean {
    if (!this.currentDrag) return false;

    const target = this.dropTargets.get(targetNodeId);
    if (!target || !target.isActive) return false;

    if (targetNodeId === this.currentDrag.sourceNodeId) return false;

    return target.acceptedTypes.includes(this.currentDrag.dataType);
  }

  hoverTarget(targetNodeId: string): void {
    if (!this.currentDrag) return;

    if (this.isValidDropTarget(targetNodeId)) {
      this.dragState = 'over-valid';
    } else {
      this.dragState = 'over-invalid';
    }
  }

  leaveTarget(): void {
    if (this.currentDrag) {
      this.dragState = 'dragging';
    }
  }

  getValidTargetsForCurrentDrag(): NodeDropTarget[] {
    if (!this.currentDrag) return [];

    return this.getDropTargets().filter((target) =>
      target.nodeId !== this.currentDrag!.sourceNodeId &&
      target.acceptedTypes.includes(this.currentDrag!.dataType)
    );
  }

  async drop(targetNodeId: string): Promise<NodeTransferResult> {
    if (!this.currentDrag) {
      return { transferId: '', success: false, error: 'No hay drag activo' };
    }

    if (!this.isValidDropTarget(targetNodeId)) {
      const result: NodeTransferResult = {
        transferId: '',
        success: false,
        error: `Nodo '${targetNodeId}' no acepta tipo '${this.currentDrag.dataType}'`,
      };
      this.cancelDrag();
      return result;
    }

    const transferEvent: NodeTransferEvent = {
      source: this.currentDrag.sourceNodeId,
      target: targetNodeId,
      dataType: this.currentDrag.dataType,
      payload: this.currentDrag.payload,
      transferId: generateTransferId(),
      timestamp: Date.now(),
    };

    this.transferHistory.push(transferEvent);
    this.currentDrag = null;
    this.dragState = 'idle';

    if (this.transferCallback) {
      try {
        return await this.transferCallback(transferEvent);
      } catch (error) {
        return {
          transferId: transferEvent.transferId,
          success: false,
          error: error instanceof Error ? error.message : 'Error en transferencia',
        };
      }
    }

    return {
      transferId: transferEvent.transferId,
      success: true,
    };
  }

  getTransferHistory(): NodeTransferEvent[] {
    return [...this.transferHistory];
  }

  clearHistory(): void {
    this.transferHistory = [];
  }
}
