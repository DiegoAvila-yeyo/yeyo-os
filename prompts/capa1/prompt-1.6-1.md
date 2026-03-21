## ═══════════════════════════════════════
## MICRO-FASE 1.6 — API Base (FastAPI)
## Tipo: VSCODE | Prompts: 2 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 1.6-1 [VSCODE] — Crear skeleton de API con FastAPI

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 1.6, Prompt 1 de 2: crear el skeleton de la API REST con FastAPI.

CONTEXTO:
- Micro-fases 1.0-1.5 completadas: interfaces, config, factory listos
- API es el punto de entrada HTTP para el frontend Next.js
- FastAPI con health endpoint, CORS, y estructura para endpoints futuros
- CORS: solo http://localhost:3000 (frontend Next.js)
- Puerto: 8000
- Versión: v1

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Instalar dependencias:
   cd ~/yeyo-os
   source .venv/bin/activate
   pip install fastapi "uvicorn[standard]"

2. Crear estructura de directorios:
   mkdir -p src/api

3. Crear archivo src/api/__init__.py:

   Ruta: ~/yeyo-os/src/api/__init__.py
   Contenido: (archivo vacío)

4. Crear archivo src/api/main.py:

   Ruta: ~/yeyo-os/src/api/main.py
   Contenido:

   """
   YeyoOS — API Base (FastAPI)
   Micro-fase 1.6 — Capa 1: Esqueleto
   
   Skeleton de la API REST.
   Endpoints: /health, /api/v1/status
   CORS configurado para frontend Next.js en localhost:3000.
   """
   
   import time
   from contextlib import asynccontextmanager
   
   from fastapi import FastAPI
   from fastapi.middleware.cors import CORSMiddleware
   from fastapi.responses import JSONResponse
   
   
   _start_time: float = 0.0
   
   
   @asynccontextmanager
   async def lifespan(app: FastAPI):
       """Lifecycle de la aplicación: startup y shutdown."""
       global _start_time
       _start_time = time.time()
       yield
   
   
   app = FastAPI(
       title="YeyoOS API",
       description="API REST para YeyoOS — OS AI-nativo",
       version="0.1.0",
       lifespan=lifespan,
   )
   
   # CORS — solo frontend local en desarrollo
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["http://localhost:3000"],
       allow_credentials=True,
       allow_methods=["GET", "POST", "PUT", "DELETE"],
       allow_headers=["*"],
   )
   
   
   @app.get("/health")
   async def health():
       """
       Health check básico de la API.
       Retorna status y uptime.
       """
       uptime = time.time() - _start_time if _start_time else 0
       return JSONResponse(
           content={
               "status": "healthy",
               "version": "0.1.0",
               "uptime_seconds": round(uptime, 2),
           }
       )
   
   
   @app.get("/api/v1/status")
   async def status():
       """
       Status detallado del sistema.
       En Capa 2 se conectará con HealthChecker real.
       """
       uptime = time.time() - _start_time if _start_time else 0
       return JSONResponse(
           content={
               "status": "operational",
               "version": "0.1.0",
               "uptime_seconds": round(uptime, 2),
               "services": {
                   "api": "up",
                   "postgresql": "pending",
                   "redis": "pending",
                   "ollama": "pending",
                   "gpu": "pending",
               },
           }
       )

5. Crear archivo src/api/run.py (script de arranque):

   Ruta: ~/yeyo-os/src/api/run.py
   Contenido:

   """Script para arrancar el servidor YeyoOS API."""
   
   import uvicorn
   
   
   def main():
       uvicorn.run(
           "src.api.main:app",
           host="0.0.0.0",
           port=8000,
           reload=True,
           log_level="info",
       )
   
   
   if __name__ == "__main__":
       main()

6. Verificar que el servidor arranca:
   cd ~/yeyo-os
   python -m src.api.run &
   sleep 2
   curl http://localhost:8000/health
   curl http://localhost:8000/api/v1/status
   # Detener el servidor después de verificar
   kill %1

VERIFICAR:
- [ ] Archivo src/api/main.py existe con app FastAPI
- [ ] /health retorna JSON con status "healthy"
- [ ] /api/v1/status retorna JSON con services
- [ ] CORS middleware configurado
- [ ] Server arranca en puerto 8000
- [ ] Import funciona: `from src.api.main import app`

SI FALLA:
- fastapi no instalado: `pip install fastapi`
- uvicorn no instalado: `pip install "uvicorn[standard]"`
- Puerto 8000 ocupado: `lsof -i :8000` → matar proceso
- Import error en run.py: verificar que se ejecuta desde ~/yeyo-os

NO HACER:
- No conectar a bases de datos en el health check (eso es Capa 2)
- No agregar autenticación todavía
- No crear endpoints de chat/memoria aún
- No agregar más orígenes CORS

GATE: FastAPI arranca, /health retorna 200, /api/v1/status retorna JSON, CORS configurado para localhost:3000.
```
