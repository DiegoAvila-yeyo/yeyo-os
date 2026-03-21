## ═══════════════════════════════════════
## MICRO-FASE 3.13 — API Client
## Tipo: VSCODE | Prompts: 1 | Complejidad: Simple
## ═══════════════════════════════════════

### PROMPT 3.13-1 [VSCODE] — Cliente HTTP para REST API con streaming

```
Estamos construyendo YeyoOS, un OS AI-nativo con interfaz Neural Hub. Esta es la micro-fase 3.13 de Capa 3 (Cuerpo): crear el cliente HTTP para la REST API.

CONTEXTO:
- Micro-fases 3.0-3.12 completadas: Canvas, nodos, chat, stores, WebSocket
- Fetch wrapper con error handling, timeouts, streaming
- Métodos: get, post, put (NO delete — las memorias NUNCA se borran)
- Timeout: 30s default, 120s para requests de IA
- Streaming via ReadableStream para respuestas de IA
- Base URL configurable

Abre el directorio ~/yeyo-os/frontend en VS Code.

CREAR:

1. Crear archivo src/lib/api/client.ts:

   Ruta: ~/yeyo-os/frontend/src/lib/api/client.ts
   Contenido:

   /**
    * YeyoOS — API Client (Cliente HTTP REST)
    * Micro-fase 3.13 — Capa 3: Cuerpo
    *
    * Fetch wrapper con error handling, timeouts y streaming.
    * ⚠️ NO tiene método delete(). Las memorias NUNCA se borran.
    */

   export interface APIClientConfig {
     baseURL: string;
     defaultTimeout: number;
     aiTimeout: number;
   }

   export interface APIResponse<T = unknown> {
     data: T;
     status: number;
     ok: boolean;
   }

   export interface APIError {
     message: string;
     status: number;
     detail?: string;
   }

   export type RequestInterceptor = (config: RequestInit) => RequestInit;
   export type ResponseInterceptor = (response: Response) => Response;

   const DEFAULT_CONFIG: APIClientConfig = {
     baseURL: '/api/v1',
     defaultTimeout: 30000,
     aiTimeout: 120000,
   };

   export class APIClient {
     private config: APIClientConfig;
     private requestInterceptors: RequestInterceptor[] = [];
     private responseInterceptors: ResponseInterceptor[] = [];

     constructor(config: Partial<APIClientConfig> = {}) {
       this.config = { ...DEFAULT_CONFIG, ...config };
     }

     public addRequestInterceptor(interceptor: RequestInterceptor): void {
       this.requestInterceptors.push(interceptor);
     }

     public addResponseInterceptor(interceptor: ResponseInterceptor): void {
       this.responseInterceptors.push(interceptor);
     }

     private getHeaders(): Record<string, string> {
       return {
         'Content-Type': 'application/json',
         'Accept': 'application/json',
       };
     }

     private buildURL(path: string): string {
       const base = this.config.baseURL.replace(/\/$/, '');
       const cleanPath = path.startsWith('/') ? path : `/${path}`;
       return `${base}${cleanPath}`;
     }

     private async request<T>(
       method: string,
       path: string,
       options: {
         body?: unknown;
         timeout?: number;
         signal?: AbortSignal;
         headers?: Record<string, string>;
       } = {}
     ): Promise<APIResponse<T>> {
       const url = this.buildURL(path);
       const timeout = options.timeout ?? this.config.defaultTimeout;

       const controller = new AbortController();
       const timeoutId = setTimeout(() => controller.abort(), timeout);

       let config: RequestInit = {
         method,
         headers: { ...this.getHeaders(), ...options.headers },
         signal: options.signal ?? controller.signal,
       };

       if (options.body !== undefined) {
         config.body = JSON.stringify(options.body);
       }

       for (const interceptor of this.requestInterceptors) {
         config = interceptor(config);
       }

       try {
         let response = await fetch(url, config);

         for (const interceptor of this.responseInterceptors) {
           response = interceptor(response);
         }

         if (!response.ok) {
           const errorBody = await response.json().catch(() => ({}));
           const error: APIError = {
             message: errorBody.message ?? response.statusText,
             status: response.status,
             detail: errorBody.detail,
           };
           throw error;
         }

         const data = await response.json() as T;
         return {
           data,
           status: response.status,
           ok: true,
         };
       } catch (err) {
         if ((err as Error).name === 'AbortError') {
           throw {
             message: `Request timeout after ${timeout}ms`,
             status: 408,
           } as APIError;
         }
         throw err;
       } finally {
         clearTimeout(timeoutId);
       }
     }

     public async get<T>(path: string, options?: { timeout?: number; signal?: AbortSignal }): Promise<APIResponse<T>> {
       return this.request<T>('GET', path, options);
     }

     public async post<T>(path: string, body?: unknown, options?: { timeout?: number; signal?: AbortSignal }): Promise<APIResponse<T>> {
       return this.request<T>('POST', path, { body, ...options });
     }

     public async put<T>(path: string, body?: unknown, options?: { timeout?: number; signal?: AbortSignal }): Promise<APIResponse<T>> {
       return this.request<T>('PUT', path, { body, ...options });
     }

     public async stream(
       path: string,
       body?: unknown,
       options?: { signal?: AbortSignal }
     ): Promise<ReadableStream<Uint8Array>> {
       const url = this.buildURL(path);
       const controller = new AbortController();
       const timeoutId = setTimeout(() => controller.abort(), this.config.aiTimeout);

       let config: RequestInit = {
         method: 'POST',
         headers: {
           'Content-Type': 'application/json',
           'Accept': 'text/event-stream',
         },
         signal: options?.signal ?? controller.signal,
       };

       if (body !== undefined) {
         config.body = JSON.stringify(body);
       }

       for (const interceptor of this.requestInterceptors) {
         config = interceptor(config);
       }

       try {
         const response = await fetch(url, config);

         if (!response.ok) {
           throw {
             message: `Stream error: ${response.statusText}`,
             status: response.status,
           } as APIError;
         }

         if (!response.body) {
           throw {
             message: 'No response body for stream',
             status: 500,
           } as APIError;
         }

         clearTimeout(timeoutId);
         return response.body;
       } catch (err) {
         clearTimeout(timeoutId);
         throw err;
       }
     }

     public getBaseURL(): string {
       return this.config.baseURL;
     }
   }

   export const apiClient = new APIClient();

   export { DEFAULT_CONFIG };

2. Crear archivo __tests__/lib/api/client.test.ts:

   Ruta: ~/yeyo-os/frontend/__tests__/lib/api/client.test.ts
   Contenido:

   /**
    * Tests para API Client — Micro-fase 3.13
    */

   import { APIClient, DEFAULT_CONFIG } from '@/lib/api/client';
   import type { APIError } from '@/lib/api/client';

   // Mock fetch
   const mockFetch = jest.fn();
   global.fetch = mockFetch;

   function mockResponse(data: unknown, status = 200, ok = true) {
     return {
       ok,
       status,
       statusText: ok ? 'OK' : 'Error',
       json: jest.fn().mockResolvedValue(data),
       body: new ReadableStream(),
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
     });

     describe('NO tiene método delete', () => {
       it('APIClient no tiene delete()', () => {
         expect((client as any).delete).toBeUndefined();
       });
     });

     describe('error handling', () => {
       it('lanza APIError para respuestas no-ok', async () => {
         mockFetch.mockResolvedValue(mockResponse({ message: 'Not found' }, 404, false));
         await expect(client.get('/missing')).rejects.toEqual(
           expect.objectContaining({
             message: 'Not found',
             status: 404,
           })
         );
       });
     });

     describe('stream', () => {
       it('hace POST y retorna ReadableStream', async () => {
         const mockBody = new ReadableStream();
         mockFetch.mockResolvedValue({
           ok: true,
           status: 200,
           body: mockBody,
         });
         const stream = await client.stream('/chat/stream', { message: 'test' });
         expect(stream).toBeInstanceOf(ReadableStream);
       });

       it('lanza error si no hay body', async () => {
         mockFetch.mockResolvedValue({
           ok: true,
           status: 200,
           body: null,
         });
         await expect(client.stream('/chat/stream')).rejects.toEqual(
           expect.objectContaining({
             message: 'No response body for stream',
           })
         );
       });
     });

     describe('interceptors', () => {
       it('request interceptor modifica config', async () => {
         mockFetch.mockResolvedValue(mockResponse({}));
         client.addRequestInterceptor((config) => ({
           ...config,
           headers: { ...config.headers as Record<string, string>, 'X-Custom': 'test' },
         }));
         await client.get('/test');
         expect(mockFetch).toHaveBeenCalledWith(
           expect.any(String),
           expect.objectContaining({
             headers: expect.objectContaining({ 'X-Custom': 'test' }),
           })
         );
       });
     });

     describe('buildURL', () => {
       it('construye URL correctamente', () => {
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
     });
   });

3. Ejecutar tests:
   cd ~/yeyo-os/frontend
   npx jest __tests__/lib/api/client.test.ts --no-cache

VERIFICAR:
- [ ] Archivo src/lib/api/client.ts existe
- [ ] Métodos: get, post, put, stream (NO delete)
- [ ] buildURL construye paths correctos
- [ ] Error handling para respuestas no-ok
- [ ] Timeout: 30s default, 120s para AI
- [ ] Streaming retorna ReadableStream
- [ ] Request interceptors funcionan
- [ ] TODOS los tests pasan

SI FALLA:
- Fetch mock: verificar que global.fetch está mockeado
- AbortController: verificar soporte en el entorno de test
- ReadableStream: disponible en Node 18+ / jsdom moderno

NO HACER:
- NO agregar método delete() — las memorias NUNCA se borran
- No implementar auth/tokens (eso viene después)
- No crear retry logic (el WebSocket maneja la resiliencia)

GATE: APIClient tiene get/post/put/stream, error handling, timeouts, interceptors, NO tiene delete, todos los tests pasan.
```
