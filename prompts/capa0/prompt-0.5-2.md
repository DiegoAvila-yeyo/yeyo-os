## ═══════════════════════════════════════
## MICRO-FASE 0.5 — Node.js 20 + Scaffold
## Tipo: MIXTA | Prompts: 2 (1 CLI + 1 VSCODE)
## ═══════════════════════════════════════

### PROMPT 0.5-2 [VSCODE] — Crear scaffold del proyecto Next.js

```
Estamos construyendo YeyoOS. Micro-fase 0.5, Prompt 2 de 2: crear el scaffold base del frontend con Next.js 14.

PREREQUISITO: Node.js 20 + pnpm instalados (Prompt 0.5-1).

Abre el directorio ~/yeyo-os en VS Code.

CREAR:
1. Inicializar Next.js en subdirectorio frontend/:
   cd ~/yeyo-os
   pnpm create next-app frontend --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"

2. Entrar al directorio y agregar dependencias base:
   cd frontend
   pnpm add zustand
   pnpm add pixi.js@^8.0.0
   pnpm add socket.io-client
   pnpm add -D @types/node

3. Crear estructura de carpetas:
   mkdir -p src/components/{hub,nodes,chat,common}
   mkdir -p src/lib/{api,store,utils}
   mkdir -p src/hooks
   mkdir -p src/types

4. Crear archivo src/types/index.ts con tipos base:
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

5. Crear archivo src/lib/store/hub-store.ts:
   // Zustand store base — Micro-fase 0.5
   import { create } from 'zustand';
   import type { Node } from '@/types';
   
   interface HubState {
     nodes: Node[];
     selectedNodeId: string | null;
     addNode: (node: Node) => void;
     selectNode: (id: string | null) => void;
     updateNodePosition: (id: string, x: number, y: number) => void;
   }
   
   export const useHubStore = create<HubState>((set) => ({
     nodes: [],
     selectedNodeId: null,
     addNode: (node) => set((state) => ({ nodes: [...state.nodes, node] })),
     selectNode: (id) => set({ selectedNodeId: id }),
     updateNodePosition: (id, x, y) =>
       set((state) => ({
         nodes: state.nodes.map((n) =>
           n.id === id ? { ...n, position: { x, y } } : n
         ),
       })),
   }));

6. Verificar que compila:
   pnpm build

VERIFICAR:
- [ ] Build exitoso: `cd frontend && pnpm build` → sin errores
- [ ] Estructura existe: `ls src/components/` → hub, nodes, chat, common
- [ ] Tipos creados: `cat src/types/index.ts` → Node, NodeType, Memory
- [ ] Store creado: `cat src/lib/store/hub-store.ts` → useHubStore
- [ ] Dev server arranca: `pnpm dev` → localhost:3000 responde (detener después)

NO HACER:
- No crear componentes UI aún (eso es Capa 3)
- No conectar a PostgreSQL/Redis desde frontend
- No instalar PixiJS en detalle aún (solo el paquete)

GATE: Next.js 14 scaffold compila, estructura de carpetas lista, tipos base definidos, Zustand store base funcional.
```
