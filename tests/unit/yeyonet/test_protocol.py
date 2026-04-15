"""Tests para YeyoNet protocol."""
import json
import time
import uuid

import pytest

from src.yeyonet.protocol import (
    MessageType,
    NetMessage,
    make_auth,
    make_heartbeat,
    make_job_assign,
    make_job_progress,
    make_job_result,
    make_resource_report,
)


class TestMessageType:
    """Tests for MessageType enum."""

    def test_control_types_exist(self):
        assert MessageType.HEARTBEAT == "heartbeat"
        assert MessageType.AUTH == "auth"
        assert MessageType.AUTH_OK == "auth_ok"
        assert MessageType.AUTH_FAIL == "auth_fail"
        assert MessageType.ACK == "ack"

    def test_job_types_exist(self):
        assert MessageType.JOB_ASSIGN == "job_assign"
        assert MessageType.JOB_ACCEPT == "job_accept"
        assert MessageType.JOB_REJECT == "job_reject"
        assert MessageType.JOB_PROGRESS == "job_progress"
        assert MessageType.JOB_RESULT == "job_result"
        assert MessageType.JOB_CANCEL == "job_cancel"

    def test_memory_types_exist(self):
        assert MessageType.MEMORY_SYNC == "memory_sync"
        assert MessageType.MEMORY_SYNC_ACK == "memory_sync_ack"

    def test_command_types_exist(self):
        assert MessageType.COMMAND == "command"
        assert MessageType.COMMAND_RESULT == "command_result"

    def test_status_types_exist(self):
        assert MessageType.STATUS_UPDATE == "status_update"
        assert MessageType.RESOURCE_REPORT == "resource_report"


class TestNetMessage:
    """Tests for NetMessage."""

    def test_auto_generated_msg_id(self):
        msg = NetMessage(type=MessageType.HEARTBEAT)
        assert msg.msg_id
        uuid.UUID(msg.msg_id)  # validates it's a UUID

    def test_auto_generated_timestamp(self):
        before = time.time()
        msg = NetMessage(type=MessageType.HEARTBEAT)
        after = time.time()
        assert before <= msg.timestamp <= after

    def test_unique_msg_ids(self):
        ids = {NetMessage(type=MessageType.HEARTBEAT).msg_id for _ in range(100)}
        assert len(ids) == 100

    def test_default_fields(self):
        msg = NetMessage(type=MessageType.ACK)
        assert msg.from_node == ""
        assert msg.to_node == ""
        assert msg.payload == {}
        assert msg.reply_to is None

    def test_serialization_roundtrip(self):
        msg = NetMessage(
            type=MessageType.JOB_ASSIGN,
            from_node="central",
            to_node="sat-1",
            payload={"key": "value", "nested": {"x": 1}},
        )
        json_str = msg.to_json()
        restored = NetMessage.from_json(json_str)

        assert restored.msg_id == msg.msg_id
        assert restored.type == MessageType.JOB_ASSIGN
        assert restored.from_node == "central"
        assert restored.to_node == "sat-1"
        assert restored.payload == {"key": "value", "nested": {"x": 1}}
        assert restored.timestamp == msg.timestamp

    def test_to_json_is_valid_json(self):
        msg = NetMessage(type=MessageType.HEARTBEAT, from_node="node-1")
        parsed = json.loads(msg.to_json())
        assert parsed["type"] == "heartbeat"
        assert parsed["from_node"] == "node-1"

    def test_ack_creation(self):
        original = NetMessage(
            type=MessageType.JOB_ASSIGN,
            from_node="central",
            to_node="sat-1",
        )
        ack = original.ack(payload={"status": "ok"})

        assert ack.type == MessageType.ACK
        assert ack.from_node == "sat-1"
        assert ack.to_node == "central"
        assert ack.reply_to == original.msg_id
        assert ack.payload == {"status": "ok"}

    def test_ack_default_empty_payload(self):
        original = NetMessage(type=MessageType.HEARTBEAT, from_node="node-1")
        ack = original.ack()
        assert ack.payload == {}


class TestFactoryHelpers:
    """Tests for factory helper functions."""

    def test_make_auth(self):
        msg = make_auth("node-123", "token-abc")
        assert msg.type == MessageType.AUTH
        assert msg.from_node == "node-123"
        assert msg.payload["auth_token"] == "token-abc"

    def test_make_heartbeat(self):
        msg = make_heartbeat("node-456")
        assert msg.type == MessageType.HEARTBEAT
        assert msg.from_node == "node-456"

    def test_make_resource_report(self):
        resources = {"cpu_percent": 25.0, "ram_free_gb": 8.0}
        msg = make_resource_report("node-789", resources)
        assert msg.type == MessageType.RESOURCE_REPORT
        assert msg.from_node == "node-789"
        assert msg.payload == resources

    def test_make_job_assign(self):
        msg = make_job_assign(
            from_node="central",
            to_node="sat-1",
            job_id="job-abc",
            job_type="image_generate",
            payload={"prompt": "a cat"},
        )
        assert msg.type == MessageType.JOB_ASSIGN
        assert msg.from_node == "central"
        assert msg.to_node == "sat-1"
        assert msg.payload["job_id"] == "job-abc"
        assert msg.payload["job_type"] == "image_generate"
        assert msg.payload["prompt"] == "a cat"

    def test_make_job_progress(self):
        msg = make_job_progress("node-1", "job-x", 50, "halfway done")
        assert msg.type == MessageType.JOB_PROGRESS
        assert msg.from_node == "node-1"
        assert msg.payload["job_id"] == "job-x"
        assert msg.payload["progress"] == 50
        assert msg.payload["detail"] == "halfway done"

    def test_make_job_result_success(self):
        msg = make_job_result("node-1", "job-x", success=True, data={"url": "/img.png"})
        assert msg.type == MessageType.JOB_RESULT
        assert msg.payload["success"] is True
        assert msg.payload["data"] == {"url": "/img.png"}
        assert msg.payload["error"] == ""

    def test_make_job_result_failure(self):
        msg = make_job_result("node-1", "job-x", success=False, error="OOM")
        assert msg.payload["success"] is False
        assert msg.payload["error"] == "OOM"
