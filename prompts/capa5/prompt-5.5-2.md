## ═══════════════════════════════════════
## MICRO-FASE 5.5 — Video Node (FFmpeg Validation)
## Tipo: VSCODE | Prompts: 2 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 5.5-2 [VSCODE] — Validación de seguridad de comandos FFmpeg + Tests

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 5.5 (parte 2) de Capa 5 (Órganos): crear el validador de seguridad para comandos FFmpeg y los tests completos del Video Node.

CONTEXTO:
- Prompt 5.5-1 completado: VideoNode con servicio, jobs, frontend
- CRÍTICO: la IA genera comandos ffmpeg pero DEBEN ser validados antes de ejecutar
- Banned: -y (overwrite), rm, pipes a shell, acceso fuera de directorio de trabajo
- Banned: patrones peligrosos como /dev/, /etc/, /proc/, comando encadenado (;, &&, ||)
- Whitelist de flags seguros: -i, -ss, -t, -to, -c, -codec, -vf, -af, -map, etc.
- Todas las operaciones en directorio temporal

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/nodes/video/ffmpeg_validator.py:

   Ruta: ~/yeyo-os/src/nodes/video/ffmpeg_validator.py
   Contenido:

   """
   YeyoOS — FFmpeg Command Validator
   Micro-fase 5.5 — Capa 5: Órganos

   CRÍTICO: Valida TODOS los comandos ffmpeg antes de ejecución.
   La IA genera comandos, pero este validador es la puerta de seguridad.
   """

   import re
   import shlex
   from dataclasses import dataclass, field
   from typing import Optional


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
       r"\brm\s+-rf\b",            # Borrar recursivo
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
       r"\.\.(/|\\)",              # Directory traversal
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
                   reason=f"Comando contiene patrones prohibidos",
                   blocked_patterns=blocked,
               )

           # Verificar que no tiene paths absolutos fuera del directorio de trabajo
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
           # Paths absolutos que no son archivos de entrada/salida normales
           dangerous_dirs = ["/bin", "/sbin", "/usr", "/var", "/tmp/../"]
           for d in dangerous_dirs:
               if d in command:
                   return True
           return False

       def _sanitize(self, command: str) -> str:
           """Sanitiza el comando removiendo flags innecesarios."""
           # Remover -y si se coló
           sanitized = re.sub(r"\s+-y\b", "", command)
           # Remover espacios múltiples
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

2. Crear archivo tests/unit/nodes/video/__init__.py (vacío):

   Ruta: ~/yeyo-os/tests/unit/nodes/video/__init__.py
   Contenido: (archivo vacío)

3. Crear archivo tests/unit/nodes/video/test_video_node.py:

   Ruta: ~/yeyo-os/tests/unit/nodes/video/test_video_node.py
   Contenido:

   """Tests para Video Node + FFmpeg Validator — Micro-fase 5.5"""

   import pytest
   from src.nodes.video.ffmpeg_validator import FFmpegValidator, ValidationResult


   class TestFFmpegValidatorSafe:
       """Tests para comandos seguros que deben pasar."""

       def setup_method(self):
           self.validator = FFmpegValidator()

       def test_simple_trim(self):
           result = self.validator.validate(
               "ffmpeg -i input.mp4 -ss 00:02:00 -to 00:05:00 -c copy output.mp4"
           )
           assert result.is_valid is True

       def test_concat(self):
           result = self.validator.validate(
               "ffmpeg -i part1.mp4 -i part2.mp4 -filter_complex concat=n=2 output.mp4"
           )
           assert result.is_valid is True

       def test_ffprobe_allowed(self):
           result = self.validator.validate(
               "ffprobe -i input.mp4 -loglevel quiet"
           )
           assert result.is_valid is True

       def test_resize(self):
           result = self.validator.validate(
               "ffmpeg -i input.mp4 -vf scale=1280:720 output.mp4"
           )
           assert result.is_valid is True

       def test_audio_extract(self):
           result = self.validator.validate(
               "ffmpeg -i input.mp4 -vn -c:a copy output.mp3"
           )
           assert result.is_valid is True


   class TestFFmpegValidatorDangerous:
       """Tests para comandos peligrosos que DEBEN ser rechazados."""

       def setup_method(self):
           self.validator = FFmpegValidator()

       def test_overwrite_flag_blocked(self):
           result = self.validator.validate(
               "ffmpeg -y -i input.mp4 output.mp4"
           )
           assert result.is_valid is False
           assert len(result.blocked_patterns) > 0

       def test_rm_blocked(self):
           result = self.validator.validate(
               "ffmpeg -i input.mp4 output.mp4; rm -rf /"
           )
           assert result.is_valid is False

       def test_command_chain_semicolon_blocked(self):
           result = self.validator.validate(
               "ffmpeg -i input.mp4 output.mp4; echo pwned"
           )
           assert result.is_valid is False

       def test_command_chain_and_blocked(self):
           result = self.validator.validate(
               "ffmpeg -i input.mp4 output.mp4 && rm -rf /"
           )
           assert result.is_valid is False

       def test_backtick_substitution_blocked(self):
           result = self.validator.validate(
               "ffmpeg -i `cat /etc/passwd` output.mp4"
           )
           assert result.is_valid is False

       def test_dollar_substitution_blocked(self):
           result = self.validator.validate(
               "ffmpeg -i $(whoami) output.mp4"
           )
           assert result.is_valid is False

       def test_dev_access_blocked(self):
           result = self.validator.validate(
               "ffmpeg -i /dev/video0 output.mp4"
           )
           assert result.is_valid is False

       def test_etc_access_blocked(self):
           result = self.validator.validate(
               "ffmpeg -i /etc/passwd output.mp4"
           )
           assert result.is_valid is False

       def test_directory_traversal_blocked(self):
           result = self.validator.validate(
               "ffmpeg -i ../../etc/passwd output.mp4"
           )
           assert result.is_valid is False

       def test_sudo_blocked(self):
           result = self.validator.validate(
               "sudo ffmpeg -i input.mp4 output.mp4"
           )
           assert result.is_valid is False

       def test_curl_blocked(self):
           result = self.validator.validate(
               "ffmpeg -i input.mp4 output.mp4; curl evil.com"
           )
           assert result.is_valid is False

       def test_non_ffmpeg_command_blocked(self):
           result = self.validator.validate(
               "rm -rf /important/files"
           )
           assert result.is_valid is False

       def test_empty_command_blocked(self):
           result = self.validator.validate("")
           assert result.is_valid is False


   class TestFFmpegValidatorOutputPath:
       """Tests para validación de paths de salida."""

       def setup_method(self):
           self.validator = FFmpegValidator()

       def test_valid_output_path(self):
           assert self.validator.validate_output_path(
               "/tmp/yeyo-video/output.mp4", "/tmp/yeyo-video"
           ) is True

       def test_outside_path_rejected(self):
           assert self.validator.validate_output_path(
               "/etc/output.mp4", "/tmp/yeyo-video"
           ) is False

4. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/nodes/video/test_video_node.py -v

VERIFICAR:
- [ ] FFmpegValidator bloquea TODOS los patrones peligrosos
- [ ] Comandos seguros (trim, concat, resize, extract audio) pasan
- [ ] -y flag SIEMPRE bloqueado
- [ ] Encadenamiento (;, &&, ||) SIEMPRE bloqueado
- [ ] Command substitution (``, $()) SIEMPRE bloqueado
- [ ] Acceso a /dev/, /etc/, /proc/, /sys/ SIEMPRE bloqueado
- [ ] Directory traversal (../) SIEMPRE bloqueado
- [ ] Output path validado dentro del directorio permitido
- [ ] TODOS los tests pasan

SI FALLA:
- Regex: verificar que los patrones regex son correctos
- Import error: verificar __init__.py
- shlex: viene con Python estándar

NO HACER:
- No relajar NINGUNA validación de seguridad
- No permitir -y bajo ninguna circunstancia
- No permitir acceso fuera del directorio temporal
- No implementar subtítulos (eso es 5.6)

GATE: FFmpegValidator bloquea todos los patrones peligrosos, permite comandos seguros, valida paths de salida, todos los tests de seguridad pasan.
```
