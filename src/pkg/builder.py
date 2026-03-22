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
