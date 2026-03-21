/**
 * Tests para API Client — Micro-fase 3.13
 */

import { APIClient, DEFAULT_CONFIG } from '@/lib/api/client';

// Mock fetch
const mockFetch = jest.fn();
global.fetch = mockFetch;

// ReadableStream may not be available in jsdom — provide minimal mock
if (typeof (global as any).ReadableStream === 'undefined') {
  (global as any).ReadableStream = class MockReadableStream {};
}

function mockResponse(data: unknown, status = 200, ok = true) {
  return {
    ok,
    status,
    statusText: ok ? 'OK' : 'Error',
    json: jest.fn().mockResolvedValue(data),
    body: null,
  };
}

describe('APIClient', () => {
  let client: APIClient;

  beforeEach(() => {
    jest.clearAllMocks();
    client = new APIClient({ baseURL: 'http://test:8000/api/v1' });
  });

  describe('get', () => {
    it('hace GET request al path correcto', async () => {
      mockFetch.mockResolvedValue(mockResponse({ ok: true }));
      await client.get('/health');
      expect(mockFetch).toHaveBeenCalledWith(
        'http://test:8000/api/v1/health',
        expect.objectContaining({ method: 'GET' })
      );
    });

    it('retorna data y status', async () => {
      mockFetch.mockResolvedValue(mockResponse({ name: 'YeyoOS' }));
      const result = await client.get('/info');
      expect(result.data).toEqual({ name: 'YeyoOS' });
      expect(result.status).toBe(200);
      expect(result.ok).toBe(true);
    });

    it('maneja path sin slash inicial', async () => {
      mockFetch.mockResolvedValue(mockResponse({}));
      await client.get('health');
      expect(mockFetch).toHaveBeenCalledWith(
        'http://test:8000/api/v1/health',
        expect.anything()
      );
    });

    it('incluye headers correctos', async () => {
      mockFetch.mockResolvedValue(mockResponse({}));
      await client.get('/test');
      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
          }),
        })
      );
    });
  });

  describe('post', () => {
    it('hace POST request con body', async () => {
      mockFetch.mockResolvedValue(mockResponse({ id: 1 }));
      await client.post('/chat', { message: 'hello' });
      expect(mockFetch).toHaveBeenCalledWith(
        'http://test:8000/api/v1/chat',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ message: 'hello' }),
        })
      );
    });

    it('funciona sin body', async () => {
      mockFetch.mockResolvedValue(mockResponse({ ok: true }));
      const result = await client.post('/trigger');
      expect(result.ok).toBe(true);
    });
  });

  describe('put', () => {
    it('hace PUT request', async () => {
      mockFetch.mockResolvedValue(mockResponse({ updated: true }));
      await client.put('/memory/1', { tier: 'HOT' });
      expect(mockFetch).toHaveBeenCalledWith(
        'http://test:8000/api/v1/memory/1',
        expect.objectContaining({ method: 'PUT' })
      );
    });

    it('serializa body en PUT', async () => {
      mockFetch.mockResolvedValue(mockResponse({}));
      await client.put('/node/abc', { active: true });
      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({ body: JSON.stringify({ active: true }) })
      );
    });
  });

  describe('NO tiene metodo delete', () => {
    it('APIClient no tiene delete()', () => {
      expect((client as any).delete).toBeUndefined();
    });

    it('el prototipo no tiene delete', () => {
      expect(Object.getOwnPropertyNames(APIClient.prototype)).not.toContain('delete');
    });
  });

  describe('error handling', () => {
    it('lanza APIError con status y message para 404', async () => {
      mockFetch.mockResolvedValue(mockResponse({ message: 'Not found' }, 404, false));
      await expect(client.get('/missing')).rejects.toEqual(
        expect.objectContaining({
          message: 'Not found',
          status: 404,
        })
      );
    });

    it('lanza APIError para 500', async () => {
      mockFetch.mockResolvedValue(mockResponse({ message: 'Internal error' }, 500, false));
      await expect(client.post('/fail')).rejects.toEqual(
        expect.objectContaining({ status: 500 })
      );
    });

    it('usa statusText si no hay message en el body', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 403,
        statusText: 'Forbidden',
        json: jest.fn().mockResolvedValue({}),
      });
      await expect(client.get('/forbidden')).rejects.toEqual(
        expect.objectContaining({ message: 'Forbidden', status: 403 })
      );
    });
  });

  describe('stream', () => {
    it('hace POST y retorna ReadableStream', async () => {
      const mockBody = new (global as any).ReadableStream();
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        body: mockBody,
      });
      const stream = await client.stream('/chat/stream', { message: 'test' });
      expect(stream).toBeTruthy();
    });

    it('lanza error si no hay body en la respuesta', async () => {
      mockFetch.mockResolvedValue({ ok: true, status: 200, body: null });
      await expect(client.stream('/chat/stream')).rejects.toEqual(
        expect.objectContaining({ message: 'No response body for stream' })
      );
    });

    it('lanza error si stream responde con error', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 503,
        statusText: 'Service Unavailable',
        body: null,
      });
      await expect(client.stream('/chat/stream')).rejects.toEqual(
        expect.objectContaining({ status: 503 })
      );
    });

    it('usa Accept: text/event-stream', async () => {
      mockFetch.mockResolvedValue({ ok: true, status: 200, body: new ReadableStream() });
      await client.stream('/stream');
      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({ 'Accept': 'text/event-stream' }),
        })
      );
    });
  });

  describe('interceptors', () => {
    it('request interceptor modifica config', async () => {
      mockFetch.mockResolvedValue(mockResponse({}));
      client.addRequestInterceptor((config) => ({
        ...config,
        headers: { ...(config.headers as Record<string, string>), 'X-Custom': 'test' },
      }));
      await client.get('/test');
      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({ 'X-Custom': 'test' }),
        })
      );
    });

    it('multiples request interceptors se encadenan', async () => {
      mockFetch.mockResolvedValue(mockResponse({}));
      client.addRequestInterceptor((cfg) => ({
        ...cfg,
        headers: { ...(cfg.headers as Record<string, string>), 'X-A': '1' },
      }));
      client.addRequestInterceptor((cfg) => ({
        ...cfg,
        headers: { ...(cfg.headers as Record<string, string>), 'X-B': '2' },
      }));
      await client.get('/test');
      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({ 'X-A': '1', 'X-B': '2' }),
        })
      );
    });
  });

  describe('getBaseURL', () => {
    it('retorna la baseURL configurada', () => {
      expect(client.getBaseURL()).toBe('http://test:8000/api/v1');
    });
  });

  describe('DEFAULT_CONFIG', () => {
    it('timeout default es 30s', () => {
      expect(DEFAULT_CONFIG.defaultTimeout).toBe(30000);
    });

    it('AI timeout es 120s', () => {
      expect(DEFAULT_CONFIG.aiTimeout).toBe(120000);
    });

    it('baseURL apunta a /api/v1', () => {
      expect(DEFAULT_CONFIG.baseURL).toBe('/api/v1');
    });
  });
});
