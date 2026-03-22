"""Tests para ManifestParser y PackageManifest — Micro-fase 4.0"""

import pytest
from pydantic import ValidationError

from src.pkg.manifest import (
    ManifestParser,
    PackageManifest,
    PackageType,
    PrivilegeLevel,
    ValidPermission,
    VALID_PERMISSIONS,
)

VALID_MANIFEST_DICT = {
    "name": "mi-paquete",
    "version": "1.0.0",
    "author": "YeyoOS Dev",
    "description": "Un paquete de prueba",
    "type": "node",
    "container": {
        "image": "mi-paquete:1.0.0",
        "memory_limit": "512m",
        "cpu_limit": "1.0",
        "network": "none",
    },
    "permissions": ["memory.read"],
    "privilege_level": "L2",
}


class TestManifestParserBasic:
    def test_parse_valid_manifest(self):
        manifest = ManifestParser.parse(VALID_MANIFEST_DICT)
        assert manifest.name == "mi-paquete"
        assert manifest.version == "1.0.0"
        assert manifest.author == "YeyoOS Dev"
        assert manifest.type == PackageType.NODE

    def test_parse_returns_package_manifest_instance(self):
        manifest = ManifestParser.parse(VALID_MANIFEST_DICT)
        assert isinstance(manifest, PackageManifest)

    def test_parse_yaml_string(self):
        yaml_content = """
name: test-pkg
version: 1.0.0
author: Test Author
description: Test package
type: node
container:
  image: test-pkg:1.0.0
  network: none
"""
        manifest = ManifestParser.parse_yaml(yaml_content)
        assert manifest.name == "test-pkg"
        assert manifest.version == "1.0.0"


class TestNameValidation:
    def test_valid_names_accepted(self):
        for name in ["mi-paquete", "test123", "pkg-v2", "a"]:
            data = {**VALID_MANIFEST_DICT, "name": name}
            manifest = ManifestParser.parse(data)
            assert manifest.name == name

    def test_uppercase_name_rejected(self):
        with pytest.raises(ValidationError):
            ManifestParser.parse({**VALID_MANIFEST_DICT, "name": "Mi-Paquete"})

    def test_name_with_spaces_rejected(self):
        with pytest.raises(ValidationError):
            ManifestParser.parse({**VALID_MANIFEST_DICT, "name": "mi paquete"})

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            ManifestParser.parse({**VALID_MANIFEST_DICT, "name": ""})


class TestVersionValidation:
    def test_valid_semver_accepted(self):
        for version in ["1.0.0", "2.3.4", "0.0.1", "100.200.300"]:
            data = {**VALID_MANIFEST_DICT, "version": version}
            manifest = ManifestParser.parse(data)
            assert manifest.version == version

    def test_invalid_version_rejected(self):
        for version in ["1.0", "v1.0.0", "1.0.0.0", "latest"]:
            with pytest.raises(ValidationError):
                ManifestParser.parse({**VALID_MANIFEST_DICT, "version": version})


class TestPermissionsValidation:
    def test_valid_permissions_accepted(self):
        data = {
            **VALID_MANIFEST_DICT,
            "permissions": ["memory.read", "memory.write", "gpu.inference"],
        }
        manifest = ManifestParser.parse(data)
        assert len(manifest.permissions) == 3

    def test_invalid_permission_rejected(self):
        with pytest.raises(ValidationError):
            ManifestParser.parse({
                **VALID_MANIFEST_DICT,
                "permissions": ["invalid.permission"],
            })

    def test_empty_permissions_accepted(self):
        data = {**VALID_MANIFEST_DICT, "permissions": []}
        manifest = ManifestParser.parse(data)
        assert manifest.permissions == []


class TestPrivilegeLevelValidation:
    def test_l0_root_rejected(self):
        with pytest.raises(ValidationError):
            ManifestParser.parse({**VALID_MANIFEST_DICT, "privilege_level": "L0"})

    def test_l1_to_l5_accepted(self):
        for level in ["L1", "L2", "L3", "L4", "L5"]:
            data = {**VALID_MANIFEST_DICT, "privilege_level": level}
            manifest = ManifestParser.parse(data)
            assert manifest.privilege_level.value == level


class TestContainerConfig:
    def test_valid_networks_accepted(self):
        for network in ["none", "host", "bridge"]:
            data = {
                **VALID_MANIFEST_DICT,
                "container": {**VALID_MANIFEST_DICT["container"], "network": network},
            }
            manifest = ManifestParser.parse(data)
            assert manifest.container.network == network

    def test_invalid_network_rejected(self):
        with pytest.raises(ValidationError):
            ManifestParser.parse({
                **VALID_MANIFEST_DICT,
                "container": {**VALID_MANIFEST_DICT["container"], "network": "overlay"},
            })
