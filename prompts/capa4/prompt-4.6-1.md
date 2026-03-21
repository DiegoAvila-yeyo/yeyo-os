## ═══════════════════════════════════════
## MICRO-FASE 4.6 — Node Communication (Drag & Drop)
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 4.6-1 [VSCODE] — Comunicación entre nodos por drag & drop

```
Estamos construyendo YeyoOS, un OS AI-nativo con interfaz Neural Hub. Esta es la micro-fase 4.6 de Capa 4 (Sistema Nervioso): crear el sistema de comunicación entre nodos por drag & drop.

CONTEXTO:
- Micro-fases 4.0-4.5 completadas: Manifest, Builder, Installer, Permissions, Container Security, Privileges
- Capa 3 tiene el Neural Hub canvas con nodos satélite
- El usuario arrastra datos de un nodo a otro (drag & drop)
- Tipos de datos: text, image, file, code, pipeline
- Visual feedback: ghost element, valid/invalid drop targets
- Los eventos se emiten al backend para procesamiento

Abre el directorio ~/yeyo-os/frontend en VS Code.

CREAR:

1. Crear directorio si no existe:
   mkdir -p src/lib/node-comm

2. Crear archivo src/lib/node-comm/types.ts:

   Ruta: ~/yeyo-os/frontend/src/lib/node-comm/types.ts
   Contenido:

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

3. Crear archivo src/lib/node-comm/drag-drop.ts:

   Ruta: ~/yeyo-os/frontend/src/lib/node-comm/drag-drop.ts
   Contenido:

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

4. Crear archivo src/lib/node-comm/index.ts:

   Ruta: ~/yeyo-os/frontend/src/lib/node-comm/index.ts
   Contenido:

   export { NodeDragDropManager } from './drag-drop';
   export type {
     NodeDataType,
     NodeDragData,
     NodeDropTarget,
     NodeTransferEvent,
     NodeTransferResult,
     DragState,
   } from './types';
   export type { TransferCallback } from './drag-drop';

5. Crear archivo __tests__/lib/node-comm/drag-drop.test.ts:

   Ruta: ~/yeyo-os/frontend/__tests__/lib/node-comm/drag-drop.test.ts
   Contenido:

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
         manager.startDrag('node-a', 'text', 'hello');
         manager.hoverTarget('node-b');
         expect(manager.getDragState()).toBe('over-valid');
       });

       it('hover en target inválido cambia estado a over-invalid', () => {
         manager.registerDropTarget('node-b', ['image']);
         manager.startDrag('node-a', 'text', 'hello');
         manager.hoverTarget('node-b');
         expect(manager.getDragState()).toBe('over-invalid');
       });

       it('leave target vuelve a dragging', () => {
         manager.registerDropTarget('node-b', ['text']);
         manager.startDrag('node-a', 'text', 'hello');
         manager.hoverTarget('node-b');
         manager.leaveTarget();
         expect(manager.getDragState()).toBe('dragging');
       });
     });

     describe('drop', () => {
       it('drop en target válido transfiere datos', async () => {
         manager.registerDropTarget('node-b', ['text']);
         manager.startDrag('node-a', 'text', 'hello world');
         const result = await manager.drop('node-b');
         expect(result.success).toBe(true);
         expect(result.transferId).toContain('transfer-');
       });

       it('drop en target inválido falla', async () => {
         manager.registerDropTarget('node-b', ['image']);
         manager.startDrag('node-a', 'text', 'hello');
         const result = await manager.drop('node-b');
         expect(result.success).toBe(false);
         expect(result.error).toBeDefined();
       });

       it('drop sin drag activo falla', async () => {
         const result = await manager.drop('node-b');
         expect(result.success).toBe(false);
       });

       it('drop invoca transfer callback', async () => {
         const mockCallback = jest.fn().mockResolvedValue({
           transferId: 'test-id',
           success: true,
         } as NodeTransferResult);

         manager.setTransferCallback(mockCallback);
         manager.registerDropTarget('node-b', ['text']);
         manager.startDrag('node-a', 'text', 'data');
         await manager.drop('node-b');

         expect(mockCallback).toHaveBeenCalledTimes(1);
         const event = mockCallback.mock.calls[0][0] as NodeTransferEvent;
         expect(event.source).toBe('node-a');
         expect(event.target).toBe('node-b');
         expect(event.dataType).toBe('text');
       });

       it('drop resetea estado a idle', async () => {
         manager.registerDropTarget('node-b', ['text']);
         manager.startDrag('node-a', 'text', 'hello');
         await manager.drop('node-b');
         expect(manager.getDragState()).toBe('idle');
       });
     });

     describe('transfer history', () => {
       it('registra transferencias completadas', async () => {
         manager.registerDropTarget('node-b', ['text']);
         manager.startDrag('node-a', 'text', 'hello');
         await manager.drop('node-b');

         const history = manager.getTransferHistory();
         expect(history).toHaveLength(1);
         expect(history[0].source).toBe('node-a');
         expect(history[0].target).toBe('node-b');
       });

       it('limpia historial', async () => {
         manager.registerDropTarget('node-b', ['text']);
         manager.startDrag('node-a', 'text', 'hello');
         await manager.drop('node-b');

         manager.clearHistory();
         expect(manager.getTransferHistory()).toHaveLength(0);
       });
     });
   });

6. Ejecutar tests:
   cd ~/yeyo-os/frontend
   npx jest __tests__/lib/node-comm/drag-drop.test.ts --no-cache

VERIFICAR:
- [ ] Archivos src/lib/node-comm/types.ts, drag-drop.ts, index.ts existen
- [ ] Drag inicia correctamente con sourceNodeId, dataType, payload
- [ ] Targets válidos se resaltan (over-valid), inválidos se rechazan (over-invalid)
- [ ] Drop en target válido transfiere datos y genera transferId
- [ ] Drop en target inválido falla con error descriptivo
- [ ] No se puede hacer drop en el mismo nodo fuente
- [ ] Transfer callback se invoca correctamente
- [ ] Historial de transferencias funciona
- [ ] Estado vuelve a idle después de drop
- [ ] TODOS los tests pasan

SI FALLA:
- Import paths: verificar que @/lib/node-comm resuelve correctamente
- Jest: verificar configuración de TypeScript en jest.config
- Async: verificar que los tests usan async/await correctamente

NO HACER:
- No implementar rendering visual (eso lo hace el componente React)
- No conectar con WebSocket directamente (eso es otro módulo)
- No procesar los datos transferidos (solo rutear)

GATE: NodeDragDropManager gestiona drag & drop entre nodos, valida targets, emite eventos, registra historial, todos los tests pasan.
```
