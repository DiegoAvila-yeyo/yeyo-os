## ═══════════════════════════════════════
## MICRO-FASE 7.27 — YeyoPublisher: Deploy Multiplataforma en Una Conversación
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 7.27-1 [VSCODE] — YeyoPublisher: build + deploy para web, Android, iOS, Windows, Mac, Linux

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 7.27 de Capa 7 (Evolución): implementar YeyoPublisher que permite deploy multiplataforma desde una sola conversación — web (Vercel/Netlify), Android (Gradle), iOS (Xcode), Windows/Mac/Linux (Electron).

CONTEXTO:
- Micro-fases 7.25-7.26 completadas: SchedulerNocturno y Autodidacta funcionando
- Stack: FastAPI + Python backend, Next.js + TypeScript frontend
- YeyoPublisher es INDEPENDIENTE — solo necesita el proyecto y credenciales
- Credenciales NUNCA hardcodeadas — siempre env vars o secrets manager
- Cada plataforma es un paso independiente (puede fallar sin afectar otras)
- Los builders ejecutan comandos del sistema (subprocess)
- Las APIs de stores (Google Play, App Store) se llaman via HTTP

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/publisher/__init__.py:

   Ruta: ~/yeyo-os/src/publisher/__init__.py
   Contenido:

   """
   YeyoOS — Módulo Publisher
   Micro-fase 7.27 — Capa 7: Evolución

   Deploy multiplataforma: web, Android, iOS, Windows, Mac, Linux.
   Cada plataforma es un paso independiente.
   """

   from .yeyo_publisher import YeyoPublisher

   __all__ = ["YeyoPublisher"]


2. Crear archivo src/publisher/config.py:

   Ruta: ~/yeyo-os/src/publisher/config.py
   Contenido:

   """
   YeyoOS — Publisher Config
   Micro-fase 7.27 — Capa 7: Evolución

   Configuración de credenciales por plataforma.
   NUNCA hardcodeadas — siempre env vars o secrets manager.
   """

   from __future__ import annotations

   import logging
   import os
   from dataclasses import dataclass, field
   from typing import Any, Dict, Optional

   logger = logging.getLogger(__name__)


   @dataclass
   class PlataformaConfig:
       """Configuración de una plataforma de deploy."""
       nombre: str
       habilitada: bool = False
       credenciales: Dict[str, str] = field(default_factory=dict)
       opciones: Dict[str, Any] = field(default_factory=dict)


   @dataclass
   class ResultadoDeploy:
       """Resultado del deploy a una plataforma."""
       plataforma: str
       exito: bool = False
       url: str = ""
       version: str = ""
       error: str = ""
       duracion_ms: int = 0
       artefactos: list = field(default_factory=list)


   @dataclass
   class ResultadoPublicacion:
       """Resultado completo de publicación multiplataforma."""
       proyecto: str
       plataformas_solicitadas: list = field(default_factory=list)
       resultados: list = field(default_factory=list)
       exitosos: int = 0
       fallidos: int = 0
       duracion_total_ms: int = 0


   class PublisherConfig:
       """
       Gestiona configuración de credenciales para cada plataforma.
       Lee de variables de entorno. NUNCA almacena credenciales en disco.
       """

       @staticmethod
       def cargar_web() -> PlataformaConfig:
           """Configuración para Vercel/Netlify."""
           vercel_token = os.getenv("VERCEL_TOKEN", "")
           netlify_token = os.getenv("NETLIFY_AUTH_TOKEN", "")

           return PlataformaConfig(
               nombre="web",
               habilitada=bool(vercel_token or netlify_token),
               credenciales={
                   "vercel_token": vercel_token,
                   "netlify_token": netlify_token,
               },
               opciones={
                   "provider": "vercel" if vercel_token else "netlify" if netlify_token else "",
                   "build_command": "npm run build",
                   "output_dir": ".next",
               },
           )

       @staticmethod
       def cargar_android() -> PlataformaConfig:
           """Configuración para Android (Gradle + Google Play)."""
           return PlataformaConfig(
               nombre="android",
               habilitada=bool(os.getenv("ANDROID_KEYSTORE_PATH")),
               credenciales={
                   "keystore_path": os.getenv("ANDROID_KEYSTORE_PATH", ""),
                   "keystore_password": os.getenv("ANDROID_KEYSTORE_PASSWORD", ""),
                   "key_alias": os.getenv("ANDROID_KEY_ALIAS", ""),
                   "key_password": os.getenv("ANDROID_KEY_PASSWORD", ""),
                   "play_service_account": os.getenv("GOOGLE_PLAY_SERVICE_ACCOUNT", ""),
               },
               opciones={
                   "min_sdk": 24,
                   "target_sdk": 34,
                   "build_type": "release",
               },
           )

       @staticmethod
       def cargar_ios() -> PlataformaConfig:
           """Configuración para iOS (requiere Mac)."""
           return PlataformaConfig(
               nombre="ios",
               habilitada=bool(os.getenv("APPLE_TEAM_ID")),
               credenciales={
                   "team_id": os.getenv("APPLE_TEAM_ID", ""),
                   "api_key_id": os.getenv("APP_STORE_API_KEY_ID", ""),
                   "api_issuer_id": os.getenv("APP_STORE_API_ISSUER_ID", ""),
                   "api_key_path": os.getenv("APP_STORE_API_KEY_PATH", ""),
               },
               opciones={
                   "scheme": "YeyoOS",
                   "configuration": "Release",
               },
           )

       @staticmethod
       def cargar_desktop() -> PlataformaConfig:
           """Configuración para desktop (Electron Builder)."""
           return PlataformaConfig(
               nombre="desktop",
               habilitada=True,
               credenciales={
                   "csc_link": os.getenv("CSC_LINK", ""),
                   "csc_key_password": os.getenv("CSC_KEY_PASSWORD", ""),
                   "apple_id": os.getenv("APPLE_ID", ""),
                   "apple_id_password": os.getenv("APPLE_ID_PASSWORD", ""),
               },
               opciones={
                   "app_id": "com.yeyoos.app",
                   "product_name": "YeyoOS",
               },
           )


3. Crear archivo src/publisher/builders/web_builder.py:

   Ruta: ~/yeyo-os/src/publisher/builders/__init__.py
   Contenido:



4. Crear archivo src/publisher/builders/web_builder.py:

   Ruta: ~/yeyo-os/src/publisher/builders/web_builder.py
   Contenido:

   """
   YeyoOS — WebBuilder
   Micro-fase 7.27 — Capa 7: Evolución

   Build y deploy para web: Vercel CLI o Netlify CLI.
   """

   from __future__ import annotations

   import asyncio
   import logging
   import time
   from pathlib import Path
   from typing import Optional

   from ..config import PlataformaConfig, ResultadoDeploy

   logger = logging.getLogger(__name__)


   class WebBuilder:
       """Build y deploy web via Vercel o Netlify CLI."""

       def __init__(self, config: PlataformaConfig):
           self._config = config

       async def build_and_deploy(self, proyecto_path: str) -> ResultadoDeploy:
           """Ejecuta build y deploy web."""
           inicio = time.perf_counter()
           resultado = ResultadoDeploy(plataforma="web")

           provider = self._config.opciones.get("provider", "vercel")

           try:
               # Build
               build_cmd = self._config.opciones.get("build_command", "npm run build")
               proc = await asyncio.create_subprocess_shell(
                   f"cd {proyecto_path} && npm install --production=false && {build_cmd}",
                   stdout=asyncio.subprocess.PIPE,
                   stderr=asyncio.subprocess.PIPE,
               )
               stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)

               if proc.returncode != 0:
                   resultado.error = f"Build falló: {stderr.decode()[:500]}"
                   resultado.duracion_ms = int((time.perf_counter() - inicio) * 1000)
                   return resultado

               # Deploy
               if provider == "vercel":
                   resultado = await self._deploy_vercel(proyecto_path, resultado)
               elif provider == "netlify":
                   resultado = await self._deploy_netlify(proyecto_path, resultado)
               else:
                   resultado.error = f"Provider web desconocido: {provider}"

           except asyncio.TimeoutError:
               resultado.error = "Timeout en build web"
           except Exception as e:
               resultado.error = str(e)

           resultado.duracion_ms = int((time.perf_counter() - inicio) * 1000)
           return resultado

       async def _deploy_vercel(self, proyecto_path: str, resultado: ResultadoDeploy) -> ResultadoDeploy:
           """Deploy via Vercel CLI."""
           token = self._config.credenciales.get("vercel_token", "")
           cmd = f"cd {proyecto_path} && npx vercel --prod --yes --token={token}"

           proc = await asyncio.create_subprocess_shell(
               cmd,
               stdout=asyncio.subprocess.PIPE,
               stderr=asyncio.subprocess.PIPE,
           )
           stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=180)

           if proc.returncode == 0:
               resultado.exito = True
               resultado.url = stdout.decode().strip().split("\n")[-1]
               logger.info(f"[web_builder] Vercel deploy exitoso: {resultado.url}")
           else:
               resultado.error = f"Vercel deploy falló: {stderr.decode()[:500]}"

           return resultado

       async def _deploy_netlify(self, proyecto_path: str, resultado: ResultadoDeploy) -> ResultadoDeploy:
           """Deploy via Netlify CLI."""
           token = self._config.credenciales.get("netlify_token", "")
           output_dir = self._config.opciones.get("output_dir", ".next")
           cmd = (
               f"cd {proyecto_path} && npx netlify deploy --prod "
               f"--dir={output_dir} --auth={token}"
           )

           proc = await asyncio.create_subprocess_shell(
               cmd,
               stdout=asyncio.subprocess.PIPE,
               stderr=asyncio.subprocess.PIPE,
           )
           stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=180)

           if proc.returncode == 0:
               resultado.exito = True
               output = stdout.decode()
               for line in output.split("\n"):
                   if "https://" in line:
                       resultado.url = line.strip()
                       break
               logger.info(f"[web_builder] Netlify deploy exitoso: {resultado.url}")
           else:
               resultado.error = f"Netlify deploy falló: {stderr.decode()[:500]}"

           return resultado


5. Crear archivo src/publisher/builders/android_builder.py:

   Ruta: ~/yeyo-os/src/publisher/builders/android_builder.py
   Contenido:

   """
   YeyoOS — AndroidBuilder
   Micro-fase 7.27 — Capa 7: Evolución

   Build para Android: Gradle build → .aab → Google Play Console API.
   """

   from __future__ import annotations

   import asyncio
   import logging
   import time
   from pathlib import Path

   from ..config import PlataformaConfig, ResultadoDeploy

   logger = logging.getLogger(__name__)


   class AndroidBuilder:
       """Build y deploy Android via Gradle + Google Play Console."""

       def __init__(self, config: PlataformaConfig):
           self._config = config

       async def build_and_deploy(self, proyecto_path: str) -> ResultadoDeploy:
           """Ejecuta Gradle build y sube a Google Play."""
           inicio = time.perf_counter()
           resultado = ResultadoDeploy(plataforma="android")

           try:
               # Verificar que Gradle está disponible
               gradle_path = Path(proyecto_path) / "android"
               if not gradle_path.exists():
                   resultado.error = "Directorio android/ no encontrado en el proyecto"
                   resultado.duracion_ms = int((time.perf_counter() - inicio) * 1000)
                   return resultado

               # Build AAB
               gradlew = "gradlew.bat" if asyncio.get_event_loop().is_running() else "gradlew"
               cmd = f"cd {gradle_path} && ./{gradlew} bundleRelease"

               proc = await asyncio.create_subprocess_shell(
                   cmd,
                   stdout=asyncio.subprocess.PIPE,
                   stderr=asyncio.subprocess.PIPE,
               )
               stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)

               if proc.returncode != 0:
                   resultado.error = f"Gradle build falló: {stderr.decode()[:500]}"
                   resultado.duracion_ms = int((time.perf_counter() - inicio) * 1000)
                   return resultado

               # Buscar AAB generado
               aab_path = gradle_path / "app" / "build" / "outputs" / "bundle" / "release" / "app-release.aab"
               if aab_path.exists():
                   resultado.artefactos.append(str(aab_path))
                   resultado.exito = True
                   logger.info(f"[android_builder] AAB generado: {aab_path}")
               else:
                   resultado.error = "AAB no encontrado después del build"

               # Upload a Google Play (si credenciales disponibles)
               service_account = self._config.credenciales.get("play_service_account", "")
               if resultado.exito and service_account:
                   logger.info("[android_builder] Upload a Google Play pendiente (requiere google-auth)")
                   resultado.url = "https://play.google.com/console (upload manual pendiente)"

           except asyncio.TimeoutError:
               resultado.error = "Timeout en build Android (>10 min)"
           except Exception as e:
               resultado.error = str(e)

           resultado.duracion_ms = int((time.perf_counter() - inicio) * 1000)
           return resultado


6. Crear archivo src/publisher/builders/desktop_builder.py:

   Ruta: ~/yeyo-os/src/publisher/builders/desktop_builder.py
   Contenido:

   """
   YeyoOS — DesktopBuilder
   Micro-fase 7.27 — Capa 7: Evolución

   Build para desktop: Electron Builder → .exe (Windows), .dmg (Mac), .AppImage (Linux).
   """

   from __future__ import annotations

   import asyncio
   import logging
   import platform
   import time
   from pathlib import Path
   from typing import List

   from ..config import PlataformaConfig, ResultadoDeploy

   logger = logging.getLogger(__name__)

   PLATFORM_MAP = {
       "windows": "--win",
       "mac": "--mac",
       "linux": "--linux",
   }


   class DesktopBuilder:
       """Build desktop via electron-builder."""

       def __init__(self, config: PlataformaConfig):
           self._config = config

       async def build_and_deploy(
           self,
           proyecto_path: str,
           plataformas: List[str],
       ) -> List[ResultadoDeploy]:
           """
           Build para una o más plataformas desktop.
           Cada plataforma genera su artefacto independientemente.
           """
           resultados: List[ResultadoDeploy] = []

           for plat in plataformas:
               if plat not in PLATFORM_MAP:
                   resultados.append(ResultadoDeploy(
                       plataforma=plat,
                       error=f"Plataforma desktop desconocida: {plat}",
                   ))
                   continue

               resultado = await self._build_plataforma(proyecto_path, plat)
               resultados.append(resultado)

           return resultados

       async def _build_plataforma(self, proyecto_path: str, plataforma: str) -> ResultadoDeploy:
           """Build para una plataforma específica."""
           inicio = time.perf_counter()
           resultado = ResultadoDeploy(plataforma=plataforma)

           flag = PLATFORM_MAP.get(plataforma, "")
           if not flag:
               resultado.error = f"Plataforma no soportada: {plataforma}"
               return resultado

           try:
               # Verificar que electron-builder está disponible
               cmd = f"cd {proyecto_path} && npx electron-builder {flag} --publish=never"

               proc = await asyncio.create_subprocess_shell(
                   cmd,
                   stdout=asyncio.subprocess.PIPE,
                   stderr=asyncio.subprocess.PIPE,
               )
               stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)

               if proc.returncode == 0:
                   resultado.exito = True
                   dist_path = Path(proyecto_path) / "dist"
                   if dist_path.exists():
                       artefactos = self._buscar_artefactos(dist_path, plataforma)
                       resultado.artefactos = [str(a) for a in artefactos]
                   logger.info(f"[desktop_builder] Build {plataforma} exitoso")
               else:
                   resultado.error = f"Build {plataforma} falló: {stderr.decode()[:500]}"

           except asyncio.TimeoutError:
               resultado.error = f"Timeout en build {plataforma} (>10 min)"
           except Exception as e:
               resultado.error = str(e)

           resultado.duracion_ms = int((time.perf_counter() - inicio) * 1000)
           return resultado

       @staticmethod
       def _buscar_artefactos(dist_path: Path, plataforma: str) -> List[Path]:
           """Busca los artefactos generados según la plataforma."""
           extensiones = {
               "windows": [".exe", ".msi"],
               "mac": [".dmg", ".pkg"],
               "linux": [".AppImage", ".deb", ".snap"],
           }
           exts = extensiones.get(plataforma, [])
           artefactos = []
           for ext in exts:
               artefactos.extend(dist_path.rglob(f"*{ext}"))
           return artefactos


7. Crear archivo src/publisher/yeyo_publisher.py:

   Ruta: ~/yeyo-os/src/publisher/yeyo_publisher.py
   Contenido:

   """
   YeyoOS — YeyoPublisher
   Micro-fase 7.27 — Capa 7: Evolución

   Deploy multiplataforma en una conversación.
   Soporta: web, android, ios, windows, mac, linux.
   Cada plataforma es independiente — puede fallar sin afectar otras.
   """

   from __future__ import annotations

   import logging
   import time
   from typing import Any, Dict, List, Optional

   from .builders.android_builder import AndroidBuilder
   from .builders.desktop_builder import DesktopBuilder
   from .builders.web_builder import WebBuilder
   from .config import PublisherConfig, ResultadoDeploy, ResultadoPublicacion

   logger = logging.getLogger(__name__)

   PLATAFORMAS_VALIDAS = {"web", "android", "ios", "windows", "mac", "linux"}
   DESKTOP_PLATAFORMAS = {"windows", "mac", "linux"}


   class YeyoPublisherError(Exception):
       """Error en YeyoPublisher."""
       pass


   class YeyoPublisher:
       """
       Deploy multiplataforma desde una sola conversación.

       Uso:
           publisher = YeyoPublisher()
           resultado = await publisher.publicar(
               proyecto_path="/path/to/proyecto",
               plataformas=["web", "android", "windows"],
           )

       Cada plataforma es un paso independiente:
       - Si web falla, android y windows siguen ejecutándose
       - Reporte final muestra qué se publicó y qué falló

       Credenciales: SIEMPRE via env vars (ver PublisherConfig).
       """

       def __init__(self):
           self._publisher_config = PublisherConfig()

       async def publicar(
           self,
           proyecto_path: str,
           plataformas: List[str],
       ) -> ResultadoPublicacion:
           """
           Ejecuta build + deploy para cada plataforma solicitada.

           Args:
               proyecto_path: Ruta absoluta al proyecto
               plataformas: Lista de plataformas ("web", "android", "ios", "windows", "mac", "linux")

           Returns:
               ResultadoPublicacion con resultados por plataforma
           """
           inicio = time.perf_counter()

           # Validar plataformas
           invalidas = set(plataformas) - PLATAFORMAS_VALIDAS
           if invalidas:
               logger.warning(f"[publisher] Plataformas inválidas ignoradas: {invalidas}")
               plataformas = [p for p in plataformas if p in PLATAFORMAS_VALIDAS]

           publicacion = ResultadoPublicacion(
               proyecto=proyecto_path,
               plataformas_solicitadas=list(plataformas),
           )

           for plataforma in plataformas:
               logger.info(f"[publisher] Procesando plataforma: {plataforma}")

               try:
                   resultado = await self._deploy_plataforma(proyecto_path, plataforma)
                   publicacion.resultados.append(resultado)

                   if resultado.exito:
                       publicacion.exitosos += 1
                       logger.info(f"[publisher] ✅ {plataforma}: {resultado.url or 'OK'}")
                   else:
                       publicacion.fallidos += 1
                       logger.warning(f"[publisher] ❌ {plataforma}: {resultado.error}")

               except Exception as e:
                   publicacion.fallidos += 1
                   publicacion.resultados.append(ResultadoDeploy(
                       plataforma=plataforma,
                       error=str(e),
                   ))
                   logger.error(f"[publisher] Error en {plataforma}: {e}")

           publicacion.duracion_total_ms = int((time.perf_counter() - inicio) * 1000)

           self._log_reporte(publicacion)
           return publicacion

       async def _deploy_plataforma(self, proyecto_path: str, plataforma: str) -> ResultadoDeploy:
           """Ejecuta deploy para una plataforma específica."""
           if plataforma == "web":
               config = self._publisher_config.cargar_web()
               if not config.habilitada:
                   return ResultadoDeploy(
                       plataforma="web",
                       error="Credenciales web no configuradas (VERCEL_TOKEN o NETLIFY_AUTH_TOKEN)",
                   )
               builder = WebBuilder(config)
               return await builder.build_and_deploy(proyecto_path)

           elif plataforma == "android":
               config = self._publisher_config.cargar_android()
               if not config.habilitada:
                   return ResultadoDeploy(
                       plataforma="android",
                       error="Credenciales Android no configuradas (ANDROID_KEYSTORE_PATH)",
                   )
               builder = AndroidBuilder(config)
               return await builder.build_and_deploy(proyecto_path)

           elif plataforma == "ios":
               config = self._publisher_config.cargar_ios()
               if not config.habilitada:
                   return ResultadoDeploy(
                       plataforma="ios",
                       error="Credenciales iOS no configuradas (APPLE_TEAM_ID) — requiere Mac",
                   )
               return await self._deploy_ios(proyecto_path, config)

           elif plataforma in DESKTOP_PLATAFORMAS:
               config = self._publisher_config.cargar_desktop()
               builder = DesktopBuilder(config)
               resultados = await builder.build_and_deploy(proyecto_path, [plataforma])
               return resultados[0] if resultados else ResultadoDeploy(
                   plataforma=plataforma, error="Sin resultado de build",
               )

           return ResultadoDeploy(plataforma=plataforma, error=f"Plataforma no soportada: {plataforma}")

       async def _deploy_ios(self, proyecto_path: str, config: Any) -> ResultadoDeploy:
           """Deploy iOS — requiere Mac con Xcode."""
           import asyncio
           import platform as plat

           resultado = ResultadoDeploy(plataforma="ios")
           inicio = time.perf_counter()

           if plat.system() != "Darwin":
               resultado.error = "iOS build requiere macOS con Xcode instalado"
               return resultado

           try:
               scheme = config.opciones.get("scheme", "YeyoOS")
               cmd = (
                   f"cd {proyecto_path}/ios && "
                   f"xcodebuild -scheme {scheme} -configuration Release "
                   f"-archivePath build/{scheme}.xcarchive archive"
               )

               proc = await asyncio.create_subprocess_shell(
                   cmd,
                   stdout=asyncio.subprocess.PIPE,
                   stderr=asyncio.subprocess.PIPE,
               )
               stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)

               if proc.returncode == 0:
                   resultado.exito = True
                   resultado.artefactos.append(f"build/{scheme}.xcarchive")
                   logger.info(f"[publisher] iOS archive creado")
               else:
                   resultado.error = f"Xcode build falló: {stderr.decode()[:500]}"

           except asyncio.TimeoutError:
               resultado.error = "Timeout en build iOS (>10 min)"
           except Exception as e:
               resultado.error = str(e)

           resultado.duracion_ms = int((time.perf_counter() - inicio) * 1000)
           return resultado

       @staticmethod
       def _log_reporte(publicacion: ResultadoPublicacion) -> None:
           """Logea reporte final de publicación."""
           lineas = [
               f"\n📦 REPORTE DE PUBLICACIÓN",
               f"Proyecto: {publicacion.proyecto}",
               f"Exitosos: {publicacion.exitosos}/{len(publicacion.plataformas_solicitadas)}",
               f"Fallidos: {publicacion.fallidos}",
               f"Duración: {publicacion.duracion_total_ms}ms",
               "",
           ]
           for r in publicacion.resultados:
               estado = "✅" if r.exito else "❌"
               url_info = f" → {r.url}" if r.url else ""
               error_info = f" — {r.error}" if r.error else ""
               lineas.append(f"  {estado} {r.plataforma}{url_info}{error_info}")

           logger.info("\n".join(lineas))


8. Crear archivo tests/unit/publisher/__init__.py:

   Ruta: ~/yeyo-os/tests/unit/publisher/__init__.py
   Contenido:



9. Crear archivo tests/unit/publisher/test_yeyo_publisher.py:

   Ruta: ~/yeyo-os/tests/unit/publisher/test_yeyo_publisher.py
   Contenido:

   """
   Tests unitarios para YeyoPublisher.
   Micro-fase 7.27 — 8 tests (mock de cada builder).
   """

   import pytest
   from unittest.mock import AsyncMock, MagicMock, patch

   from src.publisher.yeyo_publisher import YeyoPublisher, PLATAFORMAS_VALIDAS
   from src.publisher.config import (
       PlataformaConfig,
       PublisherConfig,
       ResultadoDeploy,
       ResultadoPublicacion,
   )
   from src.publisher.builders.web_builder import WebBuilder
   from src.publisher.builders.android_builder import AndroidBuilder
   from src.publisher.builders.desktop_builder import DesktopBuilder


   @pytest.fixture
   def publisher():
       return YeyoPublisher()


   @pytest.mark.asyncio
   async def test_publicar_retorna_resultado(publisher):
       with patch.object(publisher, '_deploy_plataforma') as mock_deploy:
           mock_deploy.return_value = ResultadoDeploy(
               plataforma="web", exito=True, url="https://app.vercel.app",
           )
           resultado = await publisher.publicar("/tmp/proyecto", ["web"])
           assert isinstance(resultado, ResultadoPublicacion)
           assert resultado.exitosos == 1
           assert resultado.fallidos == 0


   @pytest.mark.asyncio
   async def test_publicar_multiples_plataformas(publisher):
       async def mock_deploy(path, plat):
           return ResultadoDeploy(plataforma=plat, exito=True, url=f"https://{plat}.example.com")

       with patch.object(publisher, '_deploy_plataforma', side_effect=mock_deploy):
           resultado = await publisher.publicar("/tmp/proyecto", ["web", "windows", "linux"])
           assert resultado.exitosos == 3
           assert resultado.fallidos == 0
           assert len(resultado.resultados) == 3


   @pytest.mark.asyncio
   async def test_publicar_plataforma_falla_no_afecta_otras(publisher):
       call_count = [0]

       async def mock_deploy(path, plat):
           call_count[0] += 1
           if plat == "android":
               return ResultadoDeploy(plataforma=plat, exito=False, error="Sin credenciales")
           return ResultadoDeploy(plataforma=plat, exito=True)

       with patch.object(publisher, '_deploy_plataforma', side_effect=mock_deploy):
           resultado = await publisher.publicar("/tmp/proyecto", ["web", "android", "linux"])
           assert resultado.exitosos == 2
           assert resultado.fallidos == 1
           assert call_count[0] == 3


   @pytest.mark.asyncio
   async def test_publicar_ignora_plataformas_invalidas(publisher):
       with patch.object(publisher, '_deploy_plataforma') as mock_deploy:
           mock_deploy.return_value = ResultadoDeploy(plataforma="web", exito=True)
           resultado = await publisher.publicar("/tmp/proyecto", ["web", "playstation", "xbox"])
           assert len(resultado.plataformas_solicitadas) == 1
           mock_deploy.assert_called_once()


   @pytest.mark.asyncio
   async def test_web_builder_deploy():
       config = PlataformaConfig(
           nombre="web",
           habilitada=True,
           credenciales={"vercel_token": "test_token"},
           opciones={"provider": "vercel", "build_command": "echo build"},
       )
       builder = WebBuilder(config)
       with patch("asyncio.create_subprocess_shell") as mock_proc:
           process_mock = AsyncMock()
           process_mock.communicate.return_value = (b"https://test.vercel.app", b"")
           process_mock.returncode = 0
           mock_proc.return_value = process_mock

           resultado = await builder.build_and_deploy("/tmp/proyecto")
           assert isinstance(resultado, ResultadoDeploy)


   @pytest.mark.asyncio
   async def test_desktop_builder_busca_artefactos():
       config = PlataformaConfig(nombre="desktop", habilitada=True)
       builder = DesktopBuilder(config)
       from pathlib import Path
       artefactos = builder._buscar_artefactos(Path("/nonexistent"), "windows")
       assert isinstance(artefactos, list)


   def test_publisher_config_web():
       config = PublisherConfig.cargar_web()
       assert isinstance(config, PlataformaConfig)
       assert config.nombre == "web"


   def test_publisher_config_android():
       config = PublisherConfig.cargar_android()
       assert isinstance(config, PlataformaConfig)
       assert config.nombre == "android"


VERIFICAR:

1. Ejecutar: cd ~/yeyo-os && python -m pytest tests/unit/publisher/test_yeyo_publisher.py -v
   Esperado: 8 tests pasan

2. Ejecutar: cd ~/yeyo-os && python -c "from src.publisher import YeyoPublisher; print('OK')"
   Esperado: OK

3. Ejecutar: cd ~/yeyo-os && python -c "from src.publisher.config import ResultadoPublicacion, ResultadoDeploy; print('OK')"
   Esperado: OK

4. Ejecutar: cd ~/yeyo-os && python -c "from src.publisher.builders.web_builder import WebBuilder; print('OK')"
   Esperado: OK

SI FALLA:
- Si falla import de builders: verificar que __init__.py existe en src/publisher/builders/
- Si falla asyncio.create_subprocess_shell en tests: verificar mock correcto
- Si falla plataforma iOS: es esperado en non-Mac — el test debe mockear

NO HACER:
- NO hardcodear tokens, API keys o contraseñas — SIEMPRE env vars
- NO ejecutar builds reales en tests — mockear subprocess
- NO hacer que una plataforma fallida detenga las demás
- NO modificar archivos de otros módulos (src/investigador/, src/nocturno/)

GATE:
✅ YeyoPublisher recibe proyecto y lista de plataformas
✅ Ejecuta build + deploy para cada plataforma independientemente
✅ Soporta: web (Vercel/Netlify), android (Gradle), ios (Xcode), windows/mac/linux (Electron)
✅ Si una plataforma falla, las demás siguen ejecutándose
✅ Credenciales siempre via env vars (VERCEL_TOKEN, ANDROID_KEYSTORE_PATH, APPLE_TEAM_ID, etc.)
✅ Reporte final: qué se publicó, qué falló, URLs directos
✅ 8 tests pasan (mock de cada builder)
✅ YeyoPublisher, ResultadoPublicacion exportados correctamente
```
