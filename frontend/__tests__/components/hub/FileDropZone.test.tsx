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
  const file = new File(['x'.repeat(Math.min(size, 1))], name, { type });
  Object.defineProperty(file, 'size', { value: size });
  return file;
}

function createDragEvent(file: File, overrides?: Partial<{ currentTarget: EventTarget; target: EventTarget }>) {
  return {
    preventDefault: jest.fn(),
    stopPropagation: jest.fn(),
    dataTransfer: {
      files: [file] as unknown as FileList,
      items: [{ kind: 'file', getAsFile: () => file }] as unknown as DataTransferItemList,
    } as unknown as DataTransfer,
    currentTarget: overrides?.currentTarget ?? ({} as EventTarget),
    target: overrides?.target ?? ({} as EventTarget),
  };
}

describe('FileDropZone', () => {
  const mockOnDrop = jest.fn();
  const mockOnError = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ─── categorizeFile ───────────────────────────────────────────────────────

  describe('categorizeFile', () => {
    it('categoriza imagenes por MIME type', () => {
      expect(categorizeFile(createMockFile('photo.jpg', 'image/jpeg'))).toBe('image');
      expect(categorizeFile(createMockFile('photo.png', 'image/png'))).toBe('image');
      expect(categorizeFile(createMockFile('img.webp', 'image/webp'))).toBe('image');
    });

    it('categoriza codigo por MIME type', () => {
      expect(categorizeFile(createMockFile('app.js', 'application/javascript'))).toBe('code');
      expect(categorizeFile(createMockFile('data.json', 'application/json'))).toBe('code');
    });

    it('categoriza codigo por extension', () => {
      expect(categorizeFile(createMockFile('main.ts', ''))).toBe('code');
      expect(categorizeFile(createMockFile('app.py', ''))).toBe('code');
      expect(categorizeFile(createMockFile('lib.rs', ''))).toBe('code');
      expect(categorizeFile(createMockFile('mod.go', ''))).toBe('code');
    });

    it('categoriza PDF', () => {
      expect(categorizeFile(createMockFile('doc.pdf', 'application/pdf'))).toBe('pdf');
    });

    it('categoriza audio', () => {
      expect(categorizeFile(createMockFile('song.mp3', 'audio/mpeg'))).toBe('audio');
      expect(categorizeFile(createMockFile('track.wav', 'audio/wav'))).toBe('audio');
    });

    it('categoriza video', () => {
      expect(categorizeFile(createMockFile('clip.mp4', 'video/mp4'))).toBe('video');
      expect(categorizeFile(createMockFile('film.webm', 'video/webm'))).toBe('video');
    });

    it('retorna unknown para tipos desconocidos', () => {
      expect(categorizeFile(createMockFile('data.xyz', ''))).toBe('unknown');
    });

    it('texto plano es text', () => {
      expect(categorizeFile(createMockFile('notes.txt', 'text/plain'))).toBe('text');
      expect(categorizeFile(createMockFile('readme.md', ''))).toBe('text');
    });
  });

  // ─── rendering ───────────────────────────────────────────────────────────

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

    it('tiene data-testid="file-drop-zone"', () => {
      render(
        <FileDropZone onFileDrop={mockOnDrop}>
          <div>Canvas</div>
        </FileDropZone>
      );
      expect(screen.getByTestId('file-drop-zone')).toBeInTheDocument();
    });
  });

  // ─── drag & drop events ───────────────────────────────────────────────────

  describe('drag events', () => {
    it('muestra overlay al hacer dragEnter con un archivo', () => {
      render(
        <FileDropZone onFileDrop={mockOnDrop}>
          <div>Canvas</div>
        </FileDropZone>
      );
      const zone = screen.getByTestId('file-drop-zone');
      const file = createMockFile('image.png', 'image/png');
      fireEvent.dragEnter(zone, { dataTransfer: { items: [{ kind: 'file', getAsFile: () => file }] } });
      expect(screen.getByTestId('drop-overlay')).toBeInTheDocument();
    });

    it('oculta overlay al hacer dragLeave en el elemento raiz', () => {
      render(
        <FileDropZone onFileDrop={mockOnDrop}>
          <div>Canvas</div>
        </FileDropZone>
      );
      const zone = screen.getByTestId('file-drop-zone');
      const file = createMockFile('image.png', 'image/png');
      fireEvent.dragEnter(zone, { dataTransfer: { items: [{ kind: 'file', getAsFile: () => file }] } });
      expect(screen.getByTestId('drop-overlay')).toBeInTheDocument();

      fireEvent.dragLeave(zone, { currentTarget: zone, target: zone });
      expect(screen.queryByTestId('drop-overlay')).not.toBeInTheDocument();
    });

    it('llama onFileDrop con archivo y categoria en drop', () => {
      render(
        <FileDropZone onFileDrop={mockOnDrop}>
          <div>Canvas</div>
        </FileDropZone>
      );
      const zone = screen.getByTestId('file-drop-zone');
      const file = createMockFile('main.py', 'text/plain', 1024);

      fireEvent.drop(zone, {
        dataTransfer: { files: [file], items: [{ kind: 'file', getAsFile: () => file }] },
      });

      expect(mockOnDrop).toHaveBeenCalledTimes(1);
      expect(mockOnDrop).toHaveBeenCalledWith(
        expect.objectContaining({ file, category: 'text' })
      );
    });

    it('rechaza archivos mayores al limite', () => {
      render(
        <FileDropZone onFileDrop={mockOnDrop} onError={mockOnError} maxSizeMB={10}>
          <div>Canvas</div>
        </FileDropZone>
      );
      const zone = screen.getByTestId('file-drop-zone');
      const bigFile = createMockFile('huge.mp4', 'video/mp4', 20 * 1024 * 1024);

      fireEvent.drop(zone, {
        dataTransfer: { files: [bigFile], items: [{ kind: 'file', getAsFile: () => bigFile }] },
      });

      expect(mockOnDrop).not.toHaveBeenCalled();
      expect(mockOnError).toHaveBeenCalledWith(expect.stringContaining('grande'));
    });

    it('no llama onError si no se pasa y archivo es valido', () => {
      render(
        <FileDropZone onFileDrop={mockOnDrop}>
          <div>Canvas</div>
        </FileDropZone>
      );
      const zone = screen.getByTestId('file-drop-zone');
      const file = createMockFile('code.ts', '', 500);

      fireEvent.drop(zone, {
        dataTransfer: { files: [file], items: [{ kind: 'file', getAsFile: () => file }] },
      });

      expect(mockOnDrop).toHaveBeenCalledTimes(1);
    });
  });

  // ─── constantes ───────────────────────────────────────────────────────────

  describe('constantes', () => {
    it('MAX_SIZE_MB es 100', () => {
      expect(MAX_SIZE_MB).toBe(100);
    });

    it('tiene iconos para todas las categorias', () => {
      const categories: FileCategory[] = ['image', 'text', 'code', 'pdf', 'audio', 'video', 'unknown'];
      categories.forEach((cat) => {
        expect(CATEGORY_ICONS[cat]).toBeDefined();
      });
    });
  });
});
