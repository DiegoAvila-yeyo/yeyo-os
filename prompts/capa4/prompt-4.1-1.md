## ═══════════════════════════════════════
## MICRO-FASE 4.1 — YEYO-PKG Builder
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 4.1-1 [VSCODE] — Construir paquetes .ypkg desde código fuente

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 4.1 de Capa 4 (Sistema Nervioso): crear el builder que construye paquetes .ypkg desde código fuente.

CONTEXTO:
- Micro-fase 4.0 completada: ManifestParser y PackageManifest validando correctamente
- YEYO-PKG: formato .ypkg = tar.gz con manifest.yml + imagen container + bundle UI + assets + firma SHA-256
- Container isolation: Podman (NUNCA Docker). Docker socket JAMÁS montado
- El builder lee manifest.yml, construye la imagen con Podman, empaqueta todo en .ypkg
- Output: packages/{name}-{version}.ypkg

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/pkg/builder.py:

   Ruta: ~/yeyo-os/src/pkg/builder.py
   Contenido:

   """
   YeyoOS — YEYO-PKG Package Builder
   Micro-fase 4.1 — Capa 4: Sistema Nervioso

   Construye paquetes .ypkg desde código fuente.
   Usa Podman (NUNCA Docker) para construir imágenes de container.
   """

   import os
   import hashlib
   import tarfile
   import tempfile
   import asyncio
   import shutil
   import json
   from datetime import datetime, timezone
   from pathlib import Path

   from .manifest import ManifestParser, PackageManifest


   class BuildError(Exception):
       """Error durante la construcción de un paquete."""
       pass


   class PackageBuilder:
       """Construye paquetes .ypkg desde un directorio fuente."""

       def __init__(self, output_dir: str = "packages"):
           self.output_dir = Path(output_dir)
           self.output_dir.mkdir(parents=True, exist_ok=True)

       async def build(self, source_dir: str) -> str:
           """
           Construye un paquete .ypkg desde un directorio fuente.
           Retorna la ruta al archivo .ypkg generado.
           """
           source = Path(source_dir)
           if not source.is_dir():
               raise BuildError(f"Directorio fuente no existe: {source_dir}")

           manifest_path = source / "manifest.yml"
           if not manifest_path.exists():
               raise BuildError(f"manifest.yml no encontrado en {source_dir}")

           manifest = ManifestParser.parse_file(str(manifest_path))

           with tempfile.TemporaryDirectory(prefix="yeyo-build-") as build_dir:
               build_path = Path(build_dir)

               self._copy_manifest(manifest_path, build_path)
               await self._build_container_image(manifest, source, build_path)
               self._bundle_ui_assets(manifest, source, build_path)
               self._copy_assets(source, build_path)

               signature = self._generate_signature(build_path)
               self._write_build_metadata(manifest, signature, build_path)

               ypkg_path = self._create_package(manifest, build_path)

           return str(ypkg_path)

       def _copy_manifest(self, manifest_path: Path, build_dir: Path) -> None:
           """Copia el manifest.yml al directorio de build."""
           shutil.copy2(manifest_path, build_dir / "manifest.yml")

       async def _build_container_image(
           self, manifest: PackageManifest, source: Path, build_dir: Path
       ) -> None:
           """Construye la imagen de container con Podman (NUNCA Docker)."""
           dockerfile = source / "Containerfile"
           if not dockerfile.exists():
               dockerfile = source / "Dockerfile"

           if not dockerfile.exists():
               self._create_default_containerfile(source, manifest)
               dockerfile = source / "Containerfile"

           image_tag = manifest.container.image
           proc = await asyncio.create_subprocess_exec(
               "podman", "build",
               "-t", image_tag,
               "-f", str(dockerfile),
               str(source),
               stdout=asyncio.subprocess.PIPE,
               stderr=asyncio.subprocess.PIPE,
           )
           stdout, stderr = await proc.communicate()

           if proc.returncode != 0:
               raise BuildError(
                   f"Podman build falló (exit {proc.returncode}): {stderr.decode()}"
               )

           image_file = build_dir / "container-image.tar"
           proc_save = await asyncio.create_subprocess_exec(
               "podman", "save",
               "-o", str(image_file),
               image_tag,
               stdout=asyncio.subprocess.PIPE,
               stderr=asyncio.subprocess.PIPE,
           )
           stdout_save, stderr_save = await proc_save.communicate()

           if proc_save.returncode != 0:
               raise BuildError(
                   f"Podman save falló (exit {proc_save.returncode}): {stderr_save.decode()}"
               )

       def _create_default_containerfile(self, source: Path, manifest: PackageManifest) -> None:
           """Crea un Containerfile por defecto si no existe."""
           containerfile_content = """FROM docker.io/library/node:20-alpine
   WORKDIR /app
   COPY . .
   RUN if [ -f package.json ]; then npm ci --production; fi
   USER 1000
   EXPOSE 3000
   CMD ["node", "index.js"]
   """
           (source / "Containerfile").write_text(containerfile_content)

       def _bundle_ui_assets(
           self, manifest: PackageManifest, source: Path, build_dir: Path
       ) -> None:
           """Empaqueta los assets de UI (entry_point y archivos relacionados)."""
           ui_dir = source / "ui"
           if not ui_dir.exists():
               ui_dir = source / "frontend"
           if not ui_dir.exists():
               ui_dir = source

           bundle_dir = build_dir / "ui"
           bundle_dir.mkdir(exist_ok=True)

           entry = source / manifest.entry_point
           if entry.exists():
               shutil.copy2(entry, bundle_dir / manifest.entry_point)

           for ext in ["*.html", "*.css", "*.js", "*.svg", "*.png", "*.jpg"]:
               for f in ui_dir.glob(ext):
                   shutil.copy2(f, bundle_dir / f.name)

       def _copy_assets(self, source: Path, build_dir: Path) -> None:
           """Copia assets adicionales (icons, etc.)."""
           assets_dir = source / "assets"
           if assets_dir.exists():
               shutil.copytree(assets_dir, build_dir / "assets")

       def _generate_signature(self, build_dir: Path) -> str:
           """Genera firma SHA-256 del contenido del paquete."""
           hasher = hashlib.sha256()
           for file_path in sorted(build_dir.rglob("*")):
               if file_path.is_file():
                   hasher.update(file_path.name.encode())
                   hasher.update(file_path.read_bytes())
           return f"sha256:{hasher.hexdigest()}"

       def _write_build_metadata(
           self, manifest: PackageManifest, signature: str, build_dir: Path
       ) -> None:
           """Escribe metadata de build en el paquete."""
           metadata = {
               "name": manifest.name,
               "version": manifest.version,
               "built_at": datetime.now(timezone.utc).isoformat(),
               "signature": signature,
               "builder_version": "0.1.0",
           }
           (build_dir / "build-metadata.json").write_text(
               json.dumps(metadata, indent=2)
           )

       def _create_package(self, manifest: PackageManifest, build_dir: Path) -> Path:
           """Crea el archivo .ypkg (tar.gz) final."""
           pkg_name = f"{manifest.name}-{manifest.version}.ypkg"
           ypkg_path = self.output_dir / pkg_name

           with tarfile.open(ypkg_path, "w:gz") as tar:
               for item in sorted(build_dir.rglob("*")):
                   arcname = item.relative_to(build_dir)
                   tar.add(item, arcname=str(arcname))

           return ypkg_path

       def validate_source(self, source_dir: str) -> dict:
           """Valida un directorio fuente antes de construir."""
           source = Path(source_dir)
           issues = []

           if not source.is_dir():
               issues.append(f"Directorio no existe: {source_dir}")
               return {"valid": False, "issues": issues}

           manifest_path = source / "manifest.yml"
           if not manifest_path.exists():
               issues.append("manifest.yml no encontrado")
               return {"valid": False, "issues": issues}

           try:
               manifest = ManifestParser.parse_file(str(manifest_path))
           except Exception as e:
               issues.append(f"Manifest inválido: {e}")
               return {"valid": False, "issues": issues}

           has_containerfile = (source / "Containerfile").exists() or (source / "Dockerfile").exists()
           if not has_containerfile:
               issues.append("Containerfile no encontrado (se generará uno por defecto)")

           entry = source / manifest.entry_point
           if not entry.exists():
               issues.append(f"Entry point no encontrado: {manifest.entry_point}")

           return {
               "valid": len([i for i in issues if "no encontrado" not in i or "manifest" in i.lower()]) == 0,
               "issues": issues,
               "manifest": manifest,
           }

2. Actualizar archivo src/pkg/__init__.py:

   Ruta: ~/yeyo-os/src/pkg/__init__.py
   Contenido:
   from .manifest import ManifestParser, PackageManifest
   from .builder import PackageBuilder, BuildError

3. Crear archivo tests/unit/pkg/test_builder.py:

   Ruta: ~/yeyo-os/tests/unit/pkg/test_builder.py
   Contenido:

   """Tests para YEYO-PKG Builder — Micro-fase 4.1"""

   import os
   import json
   import tarfile
   import tempfile
   import pytest
   from unittest.mock import AsyncMock, patch, MagicMock
   from pathlib import Path

   from src.pkg.builder import PackageBuilder, BuildError
   from src.pkg.manifest import ManifestParser


   VALID_MANIFEST_YAML = """
   name: "test-node"
   version: "1.0.0"
   author: "TestAuthor"
   description: "Test node package"
   type: "node"
   icon: "test.svg"
   entry_point: "index.html"
   container:
     image: "yeyo-test:1.0.0"
     memory_limit: "256m"
     cpu_limit: "0.5"
     network: "none"
   permissions:
     - "memory.read"
   privilege_level: "L2"
   """


   @pytest.fixture
   def temp_source_dir():
       """Crea un directorio fuente temporal con manifest válido."""
       with tempfile.TemporaryDirectory(prefix="yeyo-test-src-") as d:
           manifest_path = Path(d) / "manifest.yml"
           manifest_path.write_text(VALID_MANIFEST_YAML)

           entry_point = Path(d) / "index.html"
           entry_point.write_text("<html><body>Test Node</body></html>")

           containerfile = Path(d) / "Containerfile"
           containerfile.write_text("FROM alpine:latest\nCMD [\"echo\", \"hello\"]\n")

           yield d


   @pytest.fixture
   def temp_output_dir():
       """Crea un directorio de output temporal."""
       with tempfile.TemporaryDirectory(prefix="yeyo-test-out-") as d:
           yield d


   class TestPackageBuilder:
       """Tests para PackageBuilder."""

       def test_builder_creates_output_dir(self, temp_output_dir):
           output = os.path.join(temp_output_dir, "new_packages")
           builder = PackageBuilder(output_dir=output)
           assert Path(output).exists()

       @pytest.mark.asyncio
       async def test_build_rejects_missing_source_dir(self, temp_output_dir):
           builder = PackageBuilder(output_dir=temp_output_dir)
           with pytest.raises(BuildError, match="no existe"):
               await builder.build("/nonexistent/path")

       @pytest.mark.asyncio
       async def test_build_rejects_missing_manifest(self, temp_output_dir):
           with tempfile.TemporaryDirectory() as empty_dir:
               builder = PackageBuilder(output_dir=temp_output_dir)
               with pytest.raises(BuildError, match="manifest.yml"):
                   await builder.build(empty_dir)

       @pytest.mark.asyncio
       async def test_build_produces_ypkg_file(self, temp_source_dir, temp_output_dir):
           builder = PackageBuilder(output_dir=temp_output_dir)

           mock_proc = AsyncMock()
           mock_proc.returncode = 0
           mock_proc.communicate = AsyncMock(return_value=(b"ok", b""))

           with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
               ypkg_path = await builder.build(temp_source_dir)

           assert ypkg_path.endswith(".ypkg")
           assert os.path.exists(ypkg_path)
           assert "test-node-1.0.0.ypkg" in ypkg_path

       @pytest.mark.asyncio
       async def test_build_includes_manifest_in_package(self, temp_source_dir, temp_output_dir):
           builder = PackageBuilder(output_dir=temp_output_dir)

           mock_proc = AsyncMock()
           mock_proc.returncode = 0
           mock_proc.communicate = AsyncMock(return_value=(b"ok", b""))

           with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
               ypkg_path = await builder.build(temp_source_dir)

           with tarfile.open(ypkg_path, "r:gz") as tar:
               names = tar.getnames()
               assert "manifest.yml" in names

       @pytest.mark.asyncio
       async def test_build_includes_build_metadata(self, temp_source_dir, temp_output_dir):
           builder = PackageBuilder(output_dir=temp_output_dir)

           mock_proc = AsyncMock()
           mock_proc.returncode = 0
           mock_proc.communicate = AsyncMock(return_value=(b"ok", b""))

           with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
               ypkg_path = await builder.build(temp_source_dir)

           with tarfile.open(ypkg_path, "r:gz") as tar:
               names = tar.getnames()
               assert "build-metadata.json" in names
               metadata_file = tar.extractfile("build-metadata.json")
               metadata = json.loads(metadata_file.read())
               assert metadata["name"] == "test-node"
               assert metadata["version"] == "1.0.0"
               assert "signature" in metadata
               assert metadata["signature"].startswith("sha256:")

       @pytest.mark.asyncio
       async def test_build_generates_signature(self, temp_source_dir, temp_output_dir):
           builder = PackageBuilder(output_dir=temp_output_dir)

           mock_proc = AsyncMock()
           mock_proc.returncode = 0
           mock_proc.communicate = AsyncMock(return_value=(b"ok", b""))

           with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
               ypkg_path = await builder.build(temp_source_dir)

           with tarfile.open(ypkg_path, "r:gz") as tar:
               metadata_file = tar.extractfile("build-metadata.json")
               metadata = json.loads(metadata_file.read())
               assert metadata["signature"].startswith("sha256:")
               assert len(metadata["signature"]) > 10

       @pytest.mark.asyncio
       async def test_build_fails_on_podman_error(self, temp_source_dir, temp_output_dir):
           builder = PackageBuilder(output_dir=temp_output_dir)

           mock_proc = AsyncMock()
           mock_proc.returncode = 1
           mock_proc.communicate = AsyncMock(return_value=(b"", b"build error"))

           with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
               with pytest.raises(BuildError, match="Podman build falló"):
                   await builder.build(temp_source_dir)

       @pytest.mark.asyncio
       async def test_build_uses_podman_not_docker(self, temp_source_dir, temp_output_dir):
           builder = PackageBuilder(output_dir=temp_output_dir)

           mock_proc = AsyncMock()
           mock_proc.returncode = 0
           mock_proc.communicate = AsyncMock(return_value=(b"ok", b""))

           with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
               await builder.build(temp_source_dir)

           calls = mock_exec.call_args_list
           for call in calls:
               assert call[0][0] == "podman", "Debe usar Podman, NUNCA Docker"

       def test_validate_source_valid(self, temp_source_dir):
           builder = PackageBuilder()
           result = builder.validate_source(temp_source_dir)
           assert result["manifest"] is not None

       def test_validate_source_missing_dir(self):
           builder = PackageBuilder()
           result = builder.validate_source("/nonexistent")
           assert result["valid"] is False
           assert len(result["issues"]) > 0

       def test_validate_source_missing_manifest(self):
           with tempfile.TemporaryDirectory() as empty_dir:
               builder = PackageBuilder()
               result = builder.validate_source(empty_dir)
               assert result["valid"] is False

4. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   pip install pytest-asyncio
   python -m pytest tests/unit/pkg/test_builder.py -v

VERIFICAR:
- [ ] Archivo src/pkg/builder.py existe con PackageBuilder
- [ ] Build produce archivo .ypkg (tar.gz) con nombre correcto
- [ ] Manifest incluido dentro del paquete
- [ ] Build metadata con firma SHA-256 generada
- [ ] Podman usado en TODOS los comandos (NUNCA Docker)
- [ ] Build falla si Podman falla
- [ ] Build falla si no hay manifest.yml
- [ ] validate_source detecta problemas antes de construir
- [ ] TODOS los tests pasan

SI FALLA:
- pytest-asyncio no instalado: pip install pytest-asyncio
- Mock de subprocess: verificar que AsyncMock se usa correctamente
- Permisos de directorio temporal: verificar que tempfile funciona

NO HACER:
- No usar Docker en ningún lugar — SOLO Podman
- No montar Docker socket
- No instalar el paquete (eso es micro-fase 4.2)
- No conectar con base de datos de paquetes

GATE: PackageBuilder construye .ypkg válidos con Podman, incluye manifest y signature, rechaza sources inválidos, todos los tests pasan.
```
