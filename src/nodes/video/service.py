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
                process.communicate(), timeout=300,
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
