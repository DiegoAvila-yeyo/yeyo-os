"""Tests para YeyoNet models."""
import pytest
from datetime import datetime, timedelta, timezone

from pydantic import ValidationError

from src.yeyonet.models import (
    InviteRequest,
    JobStatus,
    JobType,
    NodeResources,
    NodeRole,
    NodeStatus,
    Permission,
    RegisterRequest,
    SatelliteMode,
    YeyoNetInvitation,
    YeyoNetJob,
    YeyoNetNode,
)


class TestEnums:
    """Tests for all YeyoNet enums."""

    def test_node_role_values(self):
        assert NodeRole.CENTRAL == "central"
        assert NodeRole.SATELLITE == "satellite"

    def test_satellite_mode_values(self):
        assert SatelliteMode.COMPLETO == "completo"
        assert SatelliteMode.LIGERO == "ligero"
        assert SatelliteMode.MINIMO == "minimo"

    def test_node_status_values(self):
        assert NodeStatus.ONLINE == "online"
        assert NodeStatus.IDLE == "idle"
        assert NodeStatus.OFFLINE == "offline"

    def test_permission_values(self):
        assert Permission.CHAT == "chat"
        assert Permission.GRAFOS == "grafos"
        assert Permission.MEMORIA == "memoria"
        assert Permission.CONTROL == "control"

    def test_job_type_values(self):
        assert JobType.IMAGE_GENERATE == "image_generate"
        assert JobType.VIDEO_RENDER == "video_render"
        assert JobType.TEXT_INFERENCE == "text_inference"
        assert JobType.TRAINING_STEP == "training_step"
        assert JobType.MEMORY_SYNC == "memory_sync"
        assert JobType.CUSTOM == "custom"

    def test_job_status_values(self):
        assert JobStatus.QUEUED == "queued"
        assert JobStatus.ASSIGNED == "assigned"
        assert JobStatus.RUNNING == "running"
        assert JobStatus.COMPLETED == "completed"
        assert JobStatus.FAILED == "failed"
        assert JobStatus.CANCELLED == "cancelled"


class TestNodeResources:
    """Tests for NodeResources model."""

    def test_defaults(self):
        r = NodeResources()
        assert r.cpu_percent == 0.0
        assert r.ram_free_gb == 0.0
        assert r.gpu_name is None
        assert r.gpu_vram_mb == 0
        assert r.gpu_usage_percent == 0.0
        assert r.ollama_models == []
        assert r.active_jobs == 0

    def test_custom_values(self):
        r = NodeResources(
            cpu_percent=45.2,
            ram_free_gb=8.5,
            gpu_name="RTX 4090",
            gpu_vram_mb=24576,
            gpu_usage_percent=30.0,
            ollama_models=["llama3", "mistral"],
            active_jobs=2,
        )
        assert r.gpu_name == "RTX 4090"
        assert r.ollama_models == ["llama3", "mistral"]


class TestYeyoNetNode:
    """Tests for YeyoNetNode model."""

    def test_defaults(self):
        node = YeyoNetNode(name="Test")
        assert node.name == "Test"
        assert node.role == NodeRole.SATELLITE
        assert node.mode == SatelliteMode.COMPLETO
        assert node.status == NodeStatus.OFFLINE
        assert node.permissions == [Permission.CHAT]
        assert node.visibility_level == 1

    def test_id_is_uuid_string(self):
        node = YeyoNetNode(name="Test")
        # Should be a valid UUID string
        import uuid
        uuid.UUID(node.id)

    def test_visibility_level_bounds(self):
        YeyoNetNode(name="Test", visibility_level=1)
        YeyoNetNode(name="Test", visibility_level=4)
        with pytest.raises(ValidationError):
            YeyoNetNode(name="Test", visibility_level=0)
        with pytest.raises(ValidationError):
            YeyoNetNode(name="Test", visibility_level=5)


class TestYeyoNetInvitation:
    """Tests for YeyoNetInvitation model."""

    def test_is_expired_future(self):
        inv = YeyoNetInvitation(
            code="YEYO-ABCD-EFGH-JKLM",
            satellite_name="Test",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        assert not inv.is_expired

    def test_is_expired_past(self):
        inv = YeyoNetInvitation(
            code="YEYO-ABCD-EFGH-JKLM",
            satellite_name="Test",
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        assert inv.is_expired

    def test_is_expired_naive_datetime(self):
        """Naive datetimes are treated as UTC."""
        inv = YeyoNetInvitation(
            code="YEYO-ABCD-EFGH-JKLM",
            satellite_name="Test",
            expires_at=datetime.utcnow() - timedelta(hours=1),
        )
        assert inv.is_expired

    def test_is_available(self):
        inv = YeyoNetInvitation(
            code="YEYO-ABCD-EFGH-JKLM",
            satellite_name="Test",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            used=False,
        )
        assert inv.is_available

    def test_is_not_available_when_used(self):
        inv = YeyoNetInvitation(
            code="YEYO-ABCD-EFGH-JKLM",
            satellite_name="Test",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            used=True,
        )
        assert not inv.is_available

    def test_is_not_available_when_expired(self):
        inv = YeyoNetInvitation(
            code="YEYO-ABCD-EFGH-JKLM",
            satellite_name="Test",
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
            used=False,
        )
        assert not inv.is_available


class TestYeyoNetJob:
    """Tests for YeyoNetJob model."""

    def test_defaults(self):
        job = YeyoNetJob(type=JobType.IMAGE_GENERATE)
        assert job.status == JobStatus.QUEUED
        assert job.progress == 0
        assert job.priority == 5
        assert job.attempt == 1
        assert job.max_attempts == 3
        assert job.timeout_seconds == 600

    def test_priority_bounds(self):
        YeyoNetJob(type=JobType.CUSTOM, priority=1)
        YeyoNetJob(type=JobType.CUSTOM, priority=10)
        with pytest.raises(ValidationError):
            YeyoNetJob(type=JobType.CUSTOM, priority=0)
        with pytest.raises(ValidationError):
            YeyoNetJob(type=JobType.CUSTOM, priority=11)


class TestInviteRequest:
    """Tests for InviteRequest validation."""

    def test_valid_request(self):
        req = InviteRequest(satellite_name="MiSatelite")
        assert req.satellite_name == "MiSatelite"
        assert req.permissions == [Permission.CHAT]
        assert req.visibility_level == 1
        assert req.expires_in_days == 7

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            InviteRequest(satellite_name="")

    def test_name_too_long_rejected(self):
        with pytest.raises(ValidationError):
            InviteRequest(satellite_name="A" * 101)

    def test_visibility_bounds(self):
        with pytest.raises(ValidationError):
            InviteRequest(satellite_name="Test", visibility_level=0)
        with pytest.raises(ValidationError):
            InviteRequest(satellite_name="Test", visibility_level=5)

    def test_expires_in_days_bounds(self):
        with pytest.raises(ValidationError):
            InviteRequest(satellite_name="Test", expires_in_days=0)
        with pytest.raises(ValidationError):
            InviteRequest(satellite_name="Test", expires_in_days=31)


class TestRegisterRequest:
    """Tests for RegisterRequest validation."""

    def test_valid_code(self):
        req = RegisterRequest(code="YEYO-ABCD-EFGH-JKLM")
        assert req.code == "YEYO-ABCD-EFGH-JKLM"
        assert req.mode == SatelliteMode.COMPLETO

    def test_code_too_short(self):
        with pytest.raises(ValidationError):
            RegisterRequest(code="YEYO-ABCD")

    def test_code_too_long(self):
        with pytest.raises(ValidationError):
            RegisterRequest(code="YEYO-ABCD-EFGH-JKLM-EXTRA")
