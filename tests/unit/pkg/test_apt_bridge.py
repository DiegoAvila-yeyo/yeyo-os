"""Tests para AptBridge — Micro-fase 4.10"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.pkg.apt_bridge import AptBridge, AptBridgeError, HostAptForbiddenError


class TestAptBridgeSecurity:
    """Verificar que apt en host SIEMPRE está bloqueado."""

    def test_install_on_host_always_raises(self):
        bridge = AptBridge()
        with pytest.raises(HostAptForbiddenError, match="PROHIBIDO"):
            bridge.install_on_host(["curl"])

    def test_remove_from_host_always_raises(self):
        bridge = AptBridge()
        with pytest.raises(HostAptForbiddenError, match="PROHIBIDO"):
            bridge.remove_from_host(["curl"])

    def test_install_empty_list_raises(self):
        bridge = AptBridge()
        with pytest.raises(AptBridgeError):
            import asyncio
            asyncio.run(bridge.install_in_container("container-id", []))

    def test_install_no_container_id_raises(self):
        bridge = AptBridge()
        with pytest.raises(AptBridgeError):
            import asyncio
            asyncio.run(bridge.install_in_container("", ["curl"]))


class TestAptBridgeValidation:
    """Tests de validación de nombres de paquetes."""

    def test_valid_package_names(self):
        bridge = AptBridge()
        for name in ["curl", "python3", "git", "build-essential", "libssl-dev"]:
            assert bridge._validate_package_name(name) is True

    def test_invalid_package_names(self):
        bridge = AptBridge()
        for name in ["", "pkg with spaces", "A" * 129, "pkg;rm -rf /", "../etc"]:
            assert bridge._validate_package_name(name) is False

    def test_invalid_package_name_in_install_raises(self):
        bridge = AptBridge()
        with pytest.raises(AptBridgeError, match="inválido"):
            import asyncio
            asyncio.run(bridge.install_in_container("container-id", ["pkg;evil"]))


class TestAptBridgeContainerOps:

    @pytest.mark.asyncio
    async def test_install_in_container_success(self):
        bridge = AptBridge()
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_exec.return_value = mock_proc

            result = await bridge.install_in_container("container-123", ["curl"])
            assert result.success is True
            assert "curl" in result.packages

    @pytest.mark.asyncio
    async def test_install_in_container_failure(self):
        bridge = AptBridge()
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.returncode = 1
            mock_proc.communicate = AsyncMock(return_value=(b"", b"Package not found"))
            mock_exec.return_value = mock_proc

            result = await bridge.install_in_container("container-123", ["nonexistent-pkg"])
            assert result.success is False
            assert result.error is not None

    @pytest.mark.asyncio
    async def test_get_installed_empty_initially(self):
        bridge = AptBridge()
        installed = await bridge.get_installed("container-123")
        assert installed == []

    @pytest.mark.asyncio
    async def test_get_installed_after_install(self):
        bridge = AptBridge()
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_exec.return_value = mock_proc

            await bridge.install_in_container("container-1", ["curl", "git"])
            installed = await bridge.get_installed("container-1")
            assert "curl" in installed
            assert "git" in installed
