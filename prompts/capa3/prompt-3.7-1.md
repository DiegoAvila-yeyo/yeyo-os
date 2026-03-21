## ═══════════════════════════════════════
## MICRO-FASE 3.7 — File Drop Zone
## Tipo: VSCODE | Prompts: 1 | Complejidad: Simple
## ═══════════════════════════════════════

### PROMPT 3.7-1 [VSCODE] — Zona de drop de archivos sobre el canvas

```
Estamos construyendo YeyoOS, un OS AI-nativo con interfaz Neural Hub. Esta es la micro-fase 3.7 de Capa 3 (Cuerpo): crear la zona de drop de archivos sobre el canvas.

CONTEXTO:
- Micro-fases 3.0-3.6 completadas: Canvas, nodos, chat, MiniChat
- Los usuarios arrastran archivos al canvas para procesarlos con IA
- Overlay visual al arrastrar un archivo sobre el canvas
- Tipos aceptados: imágenes, texto, código, PDF, audio, video
- Max file size: 100MB
- Rutea al nodo apropiado según el tipo de archivo

Abre el directorio ~/yeyo-os/frontend en VS Code.

CREAR:

1. Crear archivo src/components/hub/FileDropZone.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/hub/FileDropZone.tsx
   Contenido:

   /**
    * YeyoOS — FileDropZone (Zona de Drop de Archivos)
    * Micro-fase 3.7 — Capa 3: Cuerpo
    *
    * Overlay global para drag & drop de archivos sobre el canvas.
    * Rutea archivos al nodo apropiado según su tipo.
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

   const MAX_SIZE_MB = 100;
   const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;

   const MIME_CATEGORIES: Record<string, FileCategory> = {
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

   const EXT_CATEGORIES: Record<string, FileCategory> = {
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

   const CATEGORY_ICONS: Record<FileCategory, string> = {
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
           onError?.(`Archivo demasiado grande: ${(file.size / 1024 / 1024).toFixed(1)}MB. Máximo: ${maxSizeMB}MB.`);
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
               <p className="text-blue-300 text-lg font-medium">
                 Soltar archivo aquí
               </p>
               {dragFileName && (
                 <p className="text-blue-400/70 text-sm mt-1">{dragFileName}</p>
               )}
             </div>
           </div>
         )}
       </div>
     );
   }

   export { MAX_SIZE_MB, MAX_SIZE_BYTES, MIME_CATEGORIES, EXT_CATEGORIES, CATEGORY_ICONS };

2. Crear archivo __tests__/components/hub/FileDropZone.test.tsx:

   Ruta: ~/yeyo-os/frontend/__tests__/components/hub/FileDropZone.test.tsx
   Contenido:

   /**
    * Tests para FileDropZone — Micro-fase 3.7
    */

   import { render, screen, fireEvent } from '@testing-library/react';
   import FileDropZone, {
     categorizeFile,
     MAX_SIZE_MB,
     CATEGORY_ICONS,
   } from '@/components/hub/FileDropZone';
   import type { FileCategory, DroppedFile } from '@/components/hub/FileDropZone';

   function createMockFile(name: string, type: string, size: number = 1024): File {
     const file = new File(['x'.repeat(size)], name, { type });
     Object.defineProperty(file, 'size', { value: size });
     return file;
   }

   function createDropEvent(file: File): Partial<React.DragEvent> {
     return {
       preventDefault: jest.fn(),
       stopPropagation: jest.fn(),
       dataTransfer: {
         files: [file] as unknown as FileList,
         items: [{ kind: 'file', getAsFile: () => file }] as unknown as DataTransferItemList,
       } as unknown as DataTransfer,
       currentTarget: null as unknown as EventTarget,
       target: null as unknown as EventTarget,
     };
   }

   describe('FileDropZone', () => {
     const mockOnDrop = jest.fn();
     const mockOnError = jest.fn();

     beforeEach(() => {
       jest.clearAllMocks();
     });

     describe('categorizeFile', () => {
       it('categoriza imágenes por MIME type', () => {
         expect(categorizeFile(createMockFile('photo.jpg', 'image/jpeg'))).toBe('image');
         expect(categorizeFile(createMockFile('photo.png', 'image/png'))).toBe('image');
       });

       it('categoriza código por MIME type', () => {
         expect(categorizeFile(createMockFile('app.js', 'application/javascript'))).toBe('code');
       });

       it('categoriza código por extensión', () => {
         expect(categorizeFile(createMockFile('main.ts', ''))).toBe('code');
         expect(categorizeFile(createMockFile('app.py', ''))).toBe('code');
         expect(categorizeFile(createMockFile('lib.rs', ''))).toBe('code');
       });

       it('categoriza PDF', () => {
         expect(categorizeFile(createMockFile('doc.pdf', 'application/pdf'))).toBe('pdf');
       });

       it('categoriza audio', () => {
         expect(categorizeFile(createMockFile('song.mp3', 'audio/mpeg'))).toBe('audio');
       });

       it('categoriza video', () => {
         expect(categorizeFile(createMockFile('clip.mp4', 'video/mp4'))).toBe('video');
       });

       it('retorna unknown para tipos desconocidos', () => {
         expect(categorizeFile(createMockFile('data.xyz', ''))).toBe('unknown');
       });

       it('texto plano es text', () => {
         expect(categorizeFile(createMockFile('notes.txt', 'text/plain'))).toBe('text');
       });
     });

     describe('rendering', () => {
       it('renderiza children', () => {
         render(
           <FileDropZone onFileDrop={mockOnDrop}>
             <div data-testid="child">Canvas</div>
           </FileDropZone>
         );
         expect(screen.getByTestId('child')).toBeInTheDocument();
       });

       it('no muestra overlay por defecto', () => {
         render(
           <FileDropZone onFileDrop={mockOnDrop}>
             <div>Canvas</div>
           </FileDropZone>
         );
         expect(screen.queryByTestId('drop-overlay')).not.toBeInTheDocument();
       });
     });

     describe('constantes', () => {
       it('MAX_SIZE_MB es 100', () => {
         expect(MAX_SIZE_MB).toBe(100);
       });

       it('tiene iconos para todas las categorías', () => {
         const categories: FileCategory[] = ['image', 'text', 'code', 'pdf', 'audio', 'video', 'unknown'];
         categories.forEach((cat) => {
           expect(CATEGORY_ICONS[cat]).toBeDefined();
         });
       });
     });
   });

3. Ejecutar tests:
   cd ~/yeyo-os/frontend
   npx jest __tests__/components/hub/FileDropZone.test.tsx --no-cache

VERIFICAR:
- [ ] Archivo src/components/hub/FileDropZone.tsx existe
- [ ] categorizeFile detecta correctamente: image, text, code, pdf, audio, video
- [ ] Overlay aparece al arrastrar archivo sobre la zona
- [ ] Muestra icono según tipo de archivo
- [ ] Rechaza archivos >100MB con mensaje de error
- [ ] Llama onFileDrop con el archivo y su categoría
- [ ] TODOS los tests pasan

SI FALLA:
- DragEvent mock: verificar estructura de dataTransfer
- File mock: usar Object.defineProperty para size
- React DragEvent types: importar de React, no del DOM global

NO HACER:
- No procesar el archivo (solo rutear al nodo correcto)
- No subir al servidor (eso lo hace el nodo destino)
- No soportar múltiples archivos simultáneos (uno a la vez)

GATE: FileDropZone detecta tipos, muestra overlay, valida tamaño, rutea correctamente, todos los tests pasan.
```
