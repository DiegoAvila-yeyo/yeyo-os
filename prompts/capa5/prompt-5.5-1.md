## ═══════════════════════════════════════
## MICRO-FASE 5.5 — Video Node (FFmpeg)
## Tipo: VSCODE | Prompts: 2 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 5.5-1 [VSCODE] — Procesamiento de video con FFmpeg desde lenguaje natural

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 5.5 de Capa 5 (Órganos): crear el Video Node que procesa video via FFmpeg a partir de comandos en lenguaje natural.

CONTEXTO:
- Micro-fases 5.0-5.4 completadas: NodeBase, Chat, Image, MiniChat v1
- Usuario dice "recorta del minuto 2 al 5" → IA genera comando ffmpeg → SE VALIDA → se ejecuta
- CRÍTICO: IA genera el comando ffmpeg pero DEBE ser validado antes de ejecución
- Banned flags: -y (overwrite sin confirmar), rm, pipes peligrosos, acceso fuera de directorio
- Todas las operaciones en directorio temporal PRIMERO, luego se mueven al final
- Frontend: preview de video, input de comandos, timeline, barra de progreso
- Hardware: GTX 1060 3GB VRAM, 16GB RAM

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear estructura:
   mkdir -p src/nodes/video
   mkdir -p tests/unit/nodes/video
   mkdir -p frontend/src/components/nodes/video

2. Crear archivo src/nodes/video/__init__.py:

   Ruta: ~/yeyo-os/src/nodes/video/__init__.py
   Contenido:
   from .service import VideoNode
   from .ffmpeg_validator import FFmpegValidator

3. Crear archivo src/nodes/video/service.py:

   Ruta: ~/yeyo-os/src/nodes/video/service.py
   Contenido:

   """
   YeyoOS — Video Node
   Micro-fase 5.5 — Capa 5: Órganos

   Procesamiento de video con FFmpeg desde lenguaje natural.
   CRÍTICO: Todos los comandos ffmpeg son VALIDADOS antes de ejecutar.
   Operaciones en directorio temporal, luego se mueven al destino final.
   """

   import uuid
   import asyncio
   import tempfile
   import shutil
   from pathlib import Path
   from datetime import datetime, timezone
   from typing import Optional
   from dataclasses import dataclass, field

   from src.nodes.base import NodeBase, PrivilegeLevel
   from src.nodes.video.ffmpeg_validator import FFmpegValidator, ValidationResult


   @dataclass
   class VideoJob:
       """Trabajo de procesamiento de video."""
       id: str
       command: str
       validated_command: str
       status: str = "pending"  # pending | running | completed | failed
       progress: float = 0.0
       output_path: Optional[str] = None
       error: Optional[str] = None
       created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
       completed_at: Optional[datetime] = None


   class VideoNode(NodeBase):
       """
       Nodo de Video — órgano de procesamiento audiovisual de YeyoOS.
       FFmpeg desde lenguaje natural con validación de seguridad.
       """

       def __init__(self):
           super().__init__(
               name="Video",
               version="1.0.0",
               privilege_level=PrivilegeLevel.SANDBOX,
               container_config={
                   "memory_limit": "2g",
                   "cpu_shares": 1024,
                   "capabilities": ["ffmpeg"],
               },
           )
           self._validator = FFmpegValidator()
           self._jobs: dict[str, VideoJob] = {}
           self._temp_dir: Optional[Path] = None

       async def initialize(self) -> None:
           """Inicializa directorio temporal para operaciones."""
           self._temp_dir = Path(tempfile.mkdtemp(prefix="yeyo-video-"))

       async def render_ui(self) -> dict:
           return {
               "component": "VideoNode",
               "props": {
                   "jobs": [
                       {
                           "id": j.id, "status": j.status,
                           "progress": j.progress, "command": j.command,
                       }
                       for j in self._jobs.values()
                   ],
               },
           }

       async def process(self, input_data: dict) -> dict:
           """Procesa comando de video."""
           action = input_data.get("action", "process")

           if action == "process":
               return await self._process_natural_language(
                   input_data.get("command", ""),
                   input_data.get("input_file", ""),
               )
           elif action == "status":
               return self._get_job_status(input_data.get("job_id", ""))
           else:
               return {"error": f"Acción desconocida: {action}"}

       async def cleanup(self) -> None:
           """Limpia directorio temporal y trabajos."""
           if self._temp_dir and self._temp_dir.exists():
               shutil.rmtree(self._temp_dir, ignore_errors=True)
           self._jobs.clear()

       # ═══════════════════════════════════
       # MÉTODOS ESPECÍFICOS
       # ═══════════════════════════════════

       async def _process_natural_language(self, command: str, input_file: str) -> dict:
           """
           Convierte lenguaje natural → comando ffmpeg → valida → ejecuta.
           FLUJO:
           1. IA genera comando ffmpeg desde texto natural
           2. FFmpegValidator valida el comando
           3. Si válido → ejecuta en directorio temporal
           4. Mueve resultado al destino final
           """
           if not command.strip():
               return {"error": "Comando vacío"}

           # 1. Generar comando ffmpeg con IA
           ffmpeg_command = await self._generate_ffmpeg_command(command, input_file)

           # 2. VALIDAR SIEMPRE
           validation = self._validator.validate(ffmpeg_command)
           if not validation.is_valid:
               return {
                   "error": "Comando rechazado por seguridad",
                   "reason": validation.reason,
                   "blocked_patterns": validation.blocked_patterns,
               }

           # 3. Crear job y ejecutar
           job = VideoJob(
               id=f"vjob-{uuid.uuid4().hex[:8]}",
               command=command,
               validated_command=validation.sanitized_command,
           )
           self._jobs[job.id] = job

           # 4. Ejecutar en directorio temporal
           result = await self._execute_ffmpeg(job)
           return result

       async def _generate_ffmpeg_command(self, natural_command: str, input_file: str) -> str:
           """Usa Ollama para generar comando ffmpeg desde lenguaje natural."""
           from src.ia.ollama_provider import OllamaProvider

           provider = OllamaProvider()
           response = await provider.generate(
               prompt=f"Convert this natural language video editing command to an ffmpeg command.\n"
                       f"Input file: {input_file}\n"
                       f"Command: {natural_command}\n"
                       f"Only return the ffmpeg command, nothing else. Do not use -y flag.",
               system="You are an ffmpeg expert. Generate safe ffmpeg commands. "
                      "NEVER use -y flag. NEVER use rm. "
                      "Output to a file with descriptive name. "
                      "Use -c copy when possible for speed.",
               temperature=0.3,
           )
           return response.content.strip()

       async def _execute_ffmpeg(self, job: VideoJob) -> dict:
           """Ejecuta comando ffmpeg en directorio temporal."""
           job.status = "running"

           try:
               process = await asyncio.create_subprocess_shell(
                   job.validated_command,
                   cwd=str(self._temp_dir),
                   stdout=asyncio.subprocess.PIPE,
                   stderr=asyncio.subprocess.PIPE,
               )

               stdout, stderr = await asyncio.wait_for(
                   process.communicate(), timeout=300,  # 5 min timeout
               )

               if process.returncode == 0:
                   job.status = "completed"
                   job.progress = 100.0
                   job.completed_at = datetime.now(timezone.utc)
                   return {
                       "job_id": job.id,
                       "status": "completed",
                       "output": stdout.decode() if stdout else "",
                   }
               else:
                   job.status = "failed"
                   job.error = stderr.decode() if stderr else "Unknown error"
                   return {"job_id": job.id, "status": "failed", "error": job.error}

           except asyncio.TimeoutError:
               job.status = "failed"
               job.error = "Timeout: operación excedió 5 minutos"
               return {"job_id": job.id, "status": "failed", "error": job.error}

       def _get_job_status(self, job_id: str) -> dict:
           if job_id not in self._jobs:
               return {"error": "Job no encontrado"}
           job = self._jobs[job_id]
           return {
               "job_id": job.id,
               "status": job.status,
               "progress": job.progress,
               "error": job.error,
           }

4. Crear archivo frontend/src/components/nodes/video/VideoNode.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/nodes/video/VideoNode.tsx
   Contenido:

   /**
    * YeyoOS — Video Node Frontend
    * Micro-fase 5.5 — Capa 5: Órganos
    */

   'use client';

   import React, { useState } from 'react';
   import NodeWrapper from '../NodeWrapper';

   interface VideoJob {
     id: string;
     status: string;
     progress: number;
     command: string;
   }

   interface VideoNodeProps {
     nodeId: string;
     jobs: VideoJob[];
     onProcess: (command: string, inputFile: string) => void;
     onClose: (nodeId: string) => void;
   }

   export default function VideoNode({
     nodeId,
     jobs,
     onProcess,
     onClose,
   }: VideoNodeProps) {
     const [command, setCommand] = useState('');
     const [inputFile, setInputFile] = useState('');

     const handleProcess = () => {
       if (!command.trim()) return;
       onProcess(command.trim(), inputFile);
       setCommand('');
     };

     return (
       <NodeWrapper nodeId={nodeId} title="Video" icon="🎬" onClose={onClose}>
         <div className="flex flex-col h-full gap-3">
           {/* Video preview placeholder */}
           <div className="aspect-video bg-gray-800 rounded-lg flex items-center
                           justify-center text-gray-500 border border-gray-700">
             <span>📹 Arrastra un video aquí o selecciona archivo</span>
           </div>

           {/* Command input */}
           <div className="space-y-2">
             <input
               type="text"
               value={inputFile}
               onChange={(e) => setInputFile(e.target.value)}
               placeholder="Archivo de entrada..."
               className="w-full px-3 py-1 text-sm bg-gray-700 text-white
                          rounded border border-gray-600 focus:outline-none"
             />
             <div className="flex gap-2">
               <input
                 type="text"
                 value={command}
                 onChange={(e) => setCommand(e.target.value)}
                 onKeyDown={(e) => e.key === 'Enter' && handleProcess()}
                 placeholder="Ej: recorta del minuto 2 al 5..."
                 className="flex-1 px-3 py-2 text-sm bg-gray-700 text-white
                            rounded-lg border border-gray-600 focus:border-green-500
                            focus:outline-none"
               />
               <button
                 onClick={handleProcess}
                 disabled={!command.trim()}
                 className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm
                            hover:bg-green-500 disabled:opacity-50"
               >
                 ▶ Procesar
               </button>
             </div>
           </div>

           {/* Jobs */}
           <div className="flex-1 overflow-y-auto space-y-2">
             {jobs.map((job) => (
               <div key={job.id} className="px-3 py-2 bg-gray-800 rounded-lg
                                            border border-gray-700">
                 <div className="flex justify-between text-xs">
                   <span className="text-gray-300 truncate">{job.command}</span>
                   <span className={`font-medium ${
                     job.status === 'completed' ? 'text-green-400' :
                     job.status === 'failed' ? 'text-red-400' :
                     job.status === 'running' ? 'text-yellow-400' : 'text-gray-400'
                   }`}>
                     {job.status}
                   </span>
                 </div>
                 {job.status === 'running' && (
                   <div className="mt-1 w-full bg-gray-700 rounded-full h-1">
                     <div
                       className="bg-green-500 h-1 rounded-full transition-all"
                       style={{ width: `${job.progress}%` }}
                     />
                   </div>
                 )}
               </div>
             ))}
           </div>
         </div>
       </NodeWrapper>
     );
   }

5. Ejecutar tests: (no hay tests aún — tests de validación en prompt 5.5-2)

VERIFICAR:
- [ ] VideoNode hereda de NodeBase
- [ ] Lenguaje natural → ffmpeg command via Ollama
- [ ] Todas las operaciones en directorio temporal
- [ ] Jobs trackean status y progreso
- [ ] Frontend con preview, input, timeline, progreso
- [ ] Timeout de 5 minutos para operaciones largas

SI FALLA:
- Import error: verificar __init__.py
- ffmpeg no instalado: es requisito del sistema, no de Python
- tempfile: debería funcionar en cualquier sistema

NO HACER:
- No implementar validación aquí (eso es prompt 5.5-2)
- No implementar subtítulos/TTS (eso es 5.6)
- No ejecutar sin validación JAMÁS

GATE: VideoNode procesa video desde lenguaje natural, jobs con status tracking, operaciones en temp dir, frontend con preview y progreso. Validación en siguiente prompt.
```
