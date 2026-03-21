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

export const DEFAULT_CONFIG: APIClientConfig = {
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

  public async get<T>(
    path: string,
    options?: { timeout?: number; signal?: AbortSignal }
  ): Promise<APIResponse<T>> {
    return this.request<T>('GET', path, options);
  }

  public async post<T>(
    path: string,
    body?: unknown,
    options?: { timeout?: number; signal?: AbortSignal }
  ): Promise<APIResponse<T>> {
    return this.request<T>('POST', path, { body, ...options });
  }

  public async put<T>(
    path: string,
    body?: unknown,
    options?: { timeout?: number; signal?: AbortSignal }
  ): Promise<APIResponse<T>> {
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
