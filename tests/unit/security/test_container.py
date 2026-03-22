"""Tests para SecureContainer — Micro-fase 4.4"""

import pytest
from unittest.mock import AsyncMock, patch

from src.security.container import (
    SecureContainer,
    ContainerManifest,
    ContainerSecurityError,
    FORBIDDEN_MOUNTS,
    FORBIDDEN_CAPABILITIES,
)


@pytest.fixture
def container():
    return SecureContainer()


@pytest.fixture
def minimal_manifest():
    return ContainerManifest(image="test-image:1.0")


class TestSecurityArgumentsAlwaysPresent:

    def test_no_new_privileges_always_present(self, container, minimal_manifest):
        args = container.get_run_args(minimal_manifest)
        assert "--security-opt=no-new-privileges:true" in args

    def test_cap_drop_all_always_present(self, container, minimal_manifest):
        args = container.get_run_args(minimal_manifest)
        assert "--cap-drop=ALL" in args

    def test_read_only_always_present(self, container, minimal_manifest):
        args = container.get_run_args(minimal_manifest)
        assert "--read-only" in args

    def test_no_privileged_flag(self, container, minimal_manifest):
        args = container.get_run_args(minimal_manifest)
        assert "--privileged" not in args


class TestDockerSocketForbidden:

    def test_docker_sock_forbidden(self, container):
        manifest = ContainerManifest(
            image="test:1.0",
            extra_mounts=["/var/run/docker.sock:/var/run/docker.sock"],
        )
        with pytest.raises(ContainerSecurityError):
            container.get_run_args(manifest)

    def test_run_docker_sock_forbidden(self, container):
        manifest = ContainerManifest(
            image="test:1.0",
            extra_mounts=["/run/docker.sock:/run/docker.sock"],
        )
        with pytest.raises(ContainerSecurityError):
            container.get_run_args(manifest)

    def test_podman_sock_forbidden(self, container):
        manifest = ContainerManifest(
            image="test:1.0",
            extra_mounts=["/var/run/podman/podman.sock:/run/podman.sock"],
        )
        with pytest.raises(ContainerSecurityError):
            container.get_run_args(manifest)


class TestForbiddenCapabilities:

    def test_sys_admin_forbidden(self, container):
        manifest = ContainerManifest(image="test:1.0", extra_caps=["SYS_ADMIN"])
        with pytest.raises(ContainerSecurityError):
            container.get_run_args(manifest)

    def test_net_raw_forbidden(self, container):
        manifest = ContainerManifest(image="test:1.0", extra_caps=["NET_RAW"])
        with pytest.raises(ContainerSecurityError):
            container.get_run_args(manifest)

    def test_sys_ptrace_forbidden(self, container):
        manifest = ContainerManifest(image="test:1.0", extra_caps=["SYS_PTRACE"])
        with pytest.raises(ContainerSecurityError):
            container.get_run_args(manifest)

    def test_net_admin_forbidden(self, container):
        manifest = ContainerManifest(image="test:1.0", extra_caps=["NET_ADMIN"])
        with pytest.raises(ContainerSecurityError):
            container.get_run_args(manifest)


class TestL5SandboxRestrictions:

    def test_l5_gets_minimal_resources(self, container):
        manifest = ContainerManifest(
            image="ia-node:1.0",
            privilege_level="L5",
        )
        args = container.get_run_args(manifest)
        assert "--network=none" in args
        assert "--read-only" in args
