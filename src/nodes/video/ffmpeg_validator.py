"""
YeyoOS — FFmpeg Command Validator
Micro-fase 5.5 — Capa 5: Órganos

CRÍTICO: Valida TODOS los comandos ffmpeg antes de ejecución.
La IA genera comandos, pero este validador es la puerta de seguridad.
"""

import re
from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """Resultado de validación de comando ffmpeg."""
    is_valid: bool
    sanitized_command: str = ""
    reason: str = ""
    blocked_patterns: list[str] = field(default_factory=list)


# Patrones PROHIBIDOS — NUNCA deben aparecer en un comando ffmpeg
BANNED_PATTERNS = [
    r"-y\b",                    # Overwrite sin confirmar
    r"\brm\b",                  # Borrar archivos
    r";\s*",                    # Encadenamiento de comandos
    r"&&",                      # Encadenamiento AND
    r"\|\|",                    # Encadenamiento OR
    r"\|(?!\s*ffmpeg)",         # Pipes (excepto pipe a otro ffmpeg)
    r"`[^`]*`",                 # Backtick command substitution
    r"\$\(",                    # Command substitution
    r"\$\{",                    # Variable expansion
    r"/dev/",                   # Acceso a dispositivos
    r"/etc/",                   # Acceso a configuración del sistema
    r"/proc/",                  # Acceso a procesos
    r"/sys/",                   # Acceso a sistema
    r"/root/",                  # Acceso a root home
    r"\.\./",                   # Directory traversal
    r"\bsudo\b",               # Escalamiento de privilegios
    r"\bchmod\b",              # Cambio de permisos
    r"\bchown\b",              # Cambio de propietario
    r"\bcurl\b",               # Descarga de red
    r"\bwget\b",               # Descarga de red
    r"\bnc\b",                 # Netcat
    r"\btelnet\b",             # Telnet
    r">/dev/tcp",              # TCP redirect
    r"\bmkfifo\b",             # Named pipes
]

# Flags SEGUROS de ffmpeg que se permiten
SAFE_FLAGS = {
    "-i", "-ss", "-t", "-to", "-c", "-c:v", "-c:a",
    "-codec", "-vcodec", "-acodec", "-vf", "-af",
    "-map", "-b:v", "-b:a", "-r", "-s", "-aspect",
    "-f", "-an", "-vn", "-sn", "-shortest",
    "-threads", "-preset", "-crf", "-qp",
    "-pix_fmt", "-movflags", "-metadata",
    "-loglevel", "-stats", "-progress",
    "-filter_complex", "-lavfi",
    "-hwaccel", "-vaapi_device",
    "-srt", "-sub_charenc",
}


class FFmpegValidator:
    """
    Validador de seguridad para comandos FFmpeg.
    TODOS los comandos generados por IA pasan por aquí.
    """

    def validate(self, command: str) -> ValidationResult:
        """
        Valida un comando ffmpeg.
        Retorna ValidationResult con is_valid y comando sanitizado.
        """
        if not command or not command.strip():
            return ValidationResult(
                is_valid=False,
                reason="Comando vacío",
            )

        command = command.strip()

        # Debe empezar con ffmpeg o ffprobe
        if not command.startswith(("ffmpeg", "ffprobe")):
            return ValidationResult(
                is_valid=False,
                reason="Comando debe empezar con ffmpeg o ffprobe",
            )

        # Verificar patrones prohibidos
        blocked = []
        for pattern in BANNED_PATTERNS:
            if re.search(pattern, command):
                blocked.append(pattern)

        if blocked:
            return ValidationResult(
                is_valid=False,
                reason="Comando contiene patrones prohibidos",
                blocked_patterns=blocked,
            )

        # Verificar que no tiene paths absolutos peligrosos
        if self._has_dangerous_paths(command):
            return ValidationResult(
                is_valid=False,
                reason="Comando accede a rutas fuera del directorio de trabajo",
            )

        # Comando válido — sanitizar
        sanitized = self._sanitize(command)

        return ValidationResult(
            is_valid=True,
            sanitized_command=sanitized,
        )

    def _has_dangerous_paths(self, command: str) -> bool:
        """Detecta paths absolutos peligrosos."""
        dangerous_dirs = ["/bin", "/sbin", "/usr", "/var", "/tmp/../"]
        for d in dangerous_dirs:
            if d in command:
                return True
        return False

    def _sanitize(self, command: str) -> str:
        """Sanitiza el comando removiendo flags innecesarios."""
        sanitized = re.sub(r"\s+-y\b", "", command)
        sanitized = re.sub(r"\s+", " ", sanitized).strip()
        return sanitized

    def validate_output_path(self, path: str, allowed_dir: str) -> bool:
        """Verifica que el path de salida está dentro del directorio permitido."""
        from pathlib import Path as P
        try:
            output = P(path).resolve()
            allowed = P(allowed_dir).resolve()
            return str(output).startswith(str(allowed))
        except Exception:
            return False
