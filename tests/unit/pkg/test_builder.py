"""Tests para PackageBuilder — Micro-fase 4.1"""

import os
import pytest
import tarfile
import tempfile
import hashlib
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

from src.pkg.builder import PackageBuilder, BuildError


def create_test_source(tmpdir: str) -> str:
    """Crea un directorio source de prueba con manifest y archivos mínimos."""
    source = Path(tmpdir) / "source"
    source.mkdir()

    manifest_yaml = """name: test-pkg
version: 1.0.0
author: Test Author
description: Test package
type: node
container:
  image: test-pkg:1.0.0
  memory_limit: 256m
  cpu_limit: '0.5'
  network: none
permissions:
  - memory.read
privilege_level: L2
"""
    (source / "manifest.yml").write_text(manifest_yaml)
    (source / "index.html").write_text("<html>Hello World</html>")
    (source / "Containerfile").write_text(
        "FROM alpine:latest\nRUN echo hello\nCMD [\"echo\", \"world\"]"
    )
    return str(source)


class TestPackageBuilderValidacion:

    def test_validate_source_valid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = create_test_source(tmpdir)
            builder = PackageBuilder(output_dir=os.path.join(tmpdir, "output"))
            result = builder.validate_source(source)
            assert result["valid"] is True
            assert "manifest" in result

    def test_validate_source_no_directory(self):
        builder = PackageBuilder()
        result = builder.validate_source("/nonexistent/directory")
        assert result["valid"] is False
        assert len(result["issues"]) > 0

    def test_validate_source_no_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "empty_source"
            source.mkdir()
            builder = PackageBuilder(output_dir=os.path.join(tmpdir, "output"))
            result = builder.validate_source(str(source))
            assert result["valid"] is False
            any_manifest_issue = any("manifest" in issue.lower() for issue in result["issues"])
            assert any_manifest_issue

    def test_validate_source_invalid_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "bad_source"
            source.mkdir()
            (source / "manifest.yml").write_text("invalid: yaml: content: here:")
            builder = PackageBuilder()
            result = builder.validate_source(str(source))
            assert result["valid"] is False


class TestSignatureGeneration:

    def test_signature_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            build_dir = Path(tmpdir) / "build"
            build_dir.mkdir()
            (build_dir / "file.txt").write_text("contenido")

            builder = PackageBuilder()
            sig1 = builder._generate_signature(build_dir)
            sig2 = builder._generate_signature(build_dir)
            assert sig1 == sig2

    def test_signature_changes_with_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            build_dir1 = Path(tmpdir) / "build1"
            build_dir1.mkdir()
            (build_dir1 / "file.txt").write_text("contenido A")

            build_dir2 = Path(tmpdir) / "build2"
            build_dir2.mkdir()
            (build_dir2 / "file.txt").write_text("contenido B")

            builder = PackageBuilder()
            sig1 = builder._generate_signature(build_dir1)
            sig2 = builder._generate_signature(build_dir2)
            assert sig1 != sig2

    def test_signature_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            build_dir = Path(tmpdir) / "build"
            build_dir.mkdir()
            (build_dir / "test.txt").write_text("test")

            builder = PackageBuilder()
            sig = builder._generate_signature(build_dir)
            assert sig.startswith("sha256:")
            assert len(sig) == 7 + 64  # "sha256:" + 64 hex chars
