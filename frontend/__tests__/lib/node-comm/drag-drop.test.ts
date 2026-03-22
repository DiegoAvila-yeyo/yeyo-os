/**
 * Tests para Node Drag & Drop — Micro-fase 4.6
 */

import { NodeDragDropManager } from '@/lib/node-comm/drag-drop';
import type { NodeTransferEvent, NodeTransferResult } from '@/lib/node-comm/types';

describe('NodeDragDropManager', () => {
  let manager: NodeDragDropManager;

  beforeEach(() => {
    manager = new NodeDragDropManager();
  });

  describe('drop targets', () => {
    it('registra drop targets', () => {
      manager.registerDropTarget('node-a', ['text', 'code']);
      const targets = manager.getDropTargets();
      expect(targets).toHaveLength(1);
      expect(targets[0].nodeId).toBe('node-a');
    });

    it('desregistra drop targets', () => {
      manager.registerDropTarget('node-a', ['text']);
      manager.unregisterDropTarget('node-a');
      expect(manager.getDropTargets()).toHaveLength(0);
    });
  });

  describe('drag', () => {
    it('inicia drag correctamente', () => {
      const data = manager.startDrag('node-a', 'text', 'hello');
      expect(data.sourceNodeId).toBe('node-a');
      expect(data.dataType).toBe('text');
      expect(data.payload).toBe('hello');
      expect(manager.getDragState()).toBe('dragging');
    });

    it('cancela drag', () => {
      manager.startDrag('node-a', 'text', 'hello');
      manager.cancelDrag();
      expect(manager.getDragState()).toBe('idle');
      expect(manager.getCurrentDrag()).toBeNull();
    });

    it('estado idle por defecto', () => {
      expect(manager.getDragState()).toBe('idle');
    });
  });

  describe('valid targets', () => {
    beforeEach(() => {
      manager.registerDropTarget('node-b', ['text', 'code']);
      manager.registerDropTarget('node-c', ['image']);
    });

    it('valida target que acepta el tipo', () => {
      manager.startDrag('node-a', 'text', 'hello');
      expect(manager.isValidDropTarget('node-b')).toBe(true);
    });

    it('rechaza target que no acepta el tipo', () => {
      manager.startDrag('node-a', 'text', 'hello');
      expect(manager.isValidDropTarget('node-c')).toBe(false);
    });

    it('rechaza drop en el mismo nodo fuente', () => {
      manager.registerDropTarget('node-a', ['text']);
      manager.startDrag('node-a', 'text', 'hello');
      expect(manager.isValidDropTarget('node-a')).toBe(false);
    });

    it('rechaza target no registrado', () => {
      manager.startDrag('node-a', 'text', 'hello');
      expect(manager.isValidDropTarget('node-unknown')).toBe(false);
    });

    it('retorna targets válidos para drag actual', () => {
      manager.startDrag('node-a', 'text', 'hello');
      const valid = manager.getValidTargetsForCurrentDrag();
      expect(valid).toHaveLength(1);
      expect(valid[0].nodeId).toBe('node-b');
    });
  });

  describe('hover states', () => {
    it('hover en target válido cambia estado a over-valid', () => {
      manager.registerDropTarget('node-b', ['text']);
      manager.startDrag('node-a', 'text', 'data');
      manager.hoverTarget('node-b');
      expect(manager.getDragState()).toBe('over-valid');
    });

    it('hover en target inválido cambia estado a over-invalid', () => {
      manager.registerDropTarget('node-b', ['image']);
      manager.startDrag('node-a', 'text', 'data');
      manager.hoverTarget('node-b');
      expect(manager.getDragState()).toBe('over-invalid');
    });

    it('leave target restaura estado dragging', () => {
      manager.registerDropTarget('node-b', ['text']);
      manager.startDrag('node-a', 'text', 'data');
      manager.hoverTarget('node-b');
      manager.leaveTarget();
      expect(manager.getDragState()).toBe('dragging');
    });
  });

  describe('drop', () => {
    it('drop exitoso completa la transferencia', async () => {
      manager.registerDropTarget('node-b', ['text']);
      manager.startDrag('node-a', 'text', 'hello world');
      const result = await manager.drop('node-b');
      expect(result.success).toBe(true);
      expect(result.transferId).toBeTruthy();
      expect(manager.getDragState()).toBe('idle');
    });

    it('drop en target inválido falla', async () => {
      manager.registerDropTarget('node-b', ['image']);
      manager.startDrag('node-a', 'text', 'data');
      const result = await manager.drop('node-b');
      expect(result.success).toBe(false);
      expect(result.error).toBeTruthy();
    });

    it('drop sin drag activo falla', async () => {
      manager.registerDropTarget('node-b', ['text']);
      const result = await manager.drop('node-b');
      expect(result.success).toBe(false);
    });

    it('llama al callback de transferencia', async () => {
      const mockCallback = jest.fn().mockResolvedValue({
        transferId: 'test-id',
        success: true,
      });
      manager.setTransferCallback(mockCallback);
      manager.registerDropTarget('node-b', ['text']);
      manager.startDrag('node-a', 'text', 'payload');
      await manager.drop('node-b');
      expect(mockCallback).toHaveBeenCalledTimes(1);
      const event: NodeTransferEvent = mockCallback.mock.calls[0][0];
      expect(event.source).toBe('node-a');
      expect(event.target).toBe('node-b');
      expect(event.dataType).toBe('text');
      expect(event.payload).toBe('payload');
    });

    it('callback que falla retorna error', async () => {
      const mockCallback = jest.fn().mockRejectedValue(new Error('Network error'));
      manager.setTransferCallback(mockCallback);
      manager.registerDropTarget('node-b', ['text']);
      manager.startDrag('node-a', 'text', 'payload');
      const result = await manager.drop('node-b');
      expect(result.success).toBe(false);
      expect(result.error).toContain('Network error');
    });
  });

  describe('transfer history', () => {
    it('guarda historial de transferencias', async () => {
      manager.registerDropTarget('node-b', ['text']);
      manager.startDrag('node-a', 'text', 'p1');
      await manager.drop('node-b');
      manager.startDrag('node-a', 'text', 'p2');
      await manager.drop('node-b');
      expect(manager.getTransferHistory()).toHaveLength(2);
    });

    it('limpia historial', async () => {
      manager.registerDropTarget('node-b', ['text']);
      manager.startDrag('node-a', 'text', 'p1');
      await manager.drop('node-b');
      manager.clearHistory();
      expect(manager.getTransferHistory()).toHaveLength(0);
    });
  });
});
