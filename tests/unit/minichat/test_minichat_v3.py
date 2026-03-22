"""Tests para MiniChat v3 Actions — Micro-fase 5.19"""

import pytest
from src.minichat.actions import (
    ActionDetector, ActionExecutor, ActionType, DetectedAction,
)


class TestActionDetection:

    def setup_method(self):
        self.detector = ActionDetector()

    def test_detect_generate_image(self):
        action = self.detector.detect("genera una imagen de un gato", "image")
        assert action.action_type == ActionType.GENERATE_IMAGE
        assert action.requires_confirmation is True

    def test_detect_describe_image(self):
        action = self.detector.detect("describe esta imagen", "image")
        assert action.action_type == ActionType.DESCRIBE_IMAGE

    def test_detect_execute_code(self):
        action = self.detector.detect("ejecuta este código", "code")
        assert action.action_type == ActionType.EXECUTE_CODE

    def test_detect_explain_code(self):
        action = self.detector.detect("explica este código", "code")
        assert action.action_type == ActionType.EXPLAIN_CODE

    def test_detect_trim_video(self):
        action = self.detector.detect("recorta del minuto 2 al 5", "video")
        assert action.action_type == ActionType.TRIM_VIDEO
        assert "2" in action.parameters.get("groups", [])
        assert "5" in action.parameters.get("groups", [])

    def test_detect_transcribe_video(self):
        action = self.detector.detect("transcribe este video", "video")
        assert action.action_type == ActionType.TRANSCRIBE_VIDEO

    def test_detect_search_files(self):
        action = self.detector.detect("busca mis documentos", "files")
        assert action.action_type == ActionType.SEARCH_FILES

    def test_detect_summarize_page(self):
        action = self.detector.detect("resume esta página", "browser")
        assert action.action_type == ActionType.SUMMARIZE_PAGE

    def test_non_action_message_detected(self):
        action = self.detector.detect("hola, cómo estás?", "image")
        assert action.action_type == ActionType.NONE
        assert action.requires_confirmation is False

    def test_wrong_node_no_action(self):
        action = self.detector.detect("genera una imagen", "code")
        assert action.action_type == ActionType.NONE


class TestActionExecution:

    def test_confirm_action(self):
        executor = ActionExecutor()
        executor.confirm_action("action-123")
        assert executor.is_confirmed("action-123") is True

    def test_unconfirmed_action(self):
        executor = ActionExecutor()
        assert executor.is_confirmed("action-999") is False

    @pytest.mark.asyncio
    async def test_execute_without_confirmation_returns_prompt(self):
        executor = ActionExecutor()
        action = DetectedAction(
            action_type=ActionType.GENERATE_IMAGE,
            confidence=0.8,
            parameters={"groups": ["un gato"]},
            requires_confirmation=True,
            description="Generar imagen",
        )
        result = await executor.execute(action, "image", "node-1", "action-1")
        assert result["requires_confirmation"] is True
        assert "action_id" in result


class TestActionBuildData:

    def setup_method(self):
        self.executor = ActionExecutor()

    def test_build_generate_image(self):
        action = DetectedAction(
            action_type=ActionType.GENERATE_IMAGE,
            confidence=0.8,
            parameters={"groups": ["un gato"]},
        )
        data = self.executor._build_process_data(action, "image")
        assert data["action"] == "generate"
        assert data["prompt"] == "un gato"

    def test_build_execute_code(self):
        action = DetectedAction(
            action_type=ActionType.EXECUTE_CODE,
            confidence=0.8,
            parameters={},
        )
        data = self.executor._build_process_data(action, "code")
        assert data["action"] == "execute"

    def test_build_trim_video(self):
        action = DetectedAction(
            action_type=ActionType.TRIM_VIDEO,
            confidence=0.8,
            parameters={"groups": ["2", "5"]},
        )
        data = self.executor._build_process_data(action, "video")
        assert data["action"] == "process"
        assert "2" in data["command"]
        assert "5" in data["command"]

    def test_build_search_files(self):
        action = DetectedAction(
            action_type=ActionType.SEARCH_FILES,
            confidence=0.8,
            parameters={"groups": ["documentos"]},
        )
        data = self.executor._build_process_data(action, "files")
        assert data["action"] == "search"
        assert data["query"] == "documentos"

    def test_build_summarize_page(self):
        action = DetectedAction(
            action_type=ActionType.SUMMARIZE_PAGE,
            confidence=0.8,
            parameters={},
        )
        data = self.executor._build_process_data(action, "browser")
        assert data["action"] == "summarize"
