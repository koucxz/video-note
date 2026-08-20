"""Engine unit tests with mocked AI service."""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


class TestClampParam:
    def test_clamp_normal(self):
        from src.core.engine import _clamp_param
        assert _clamp_param("keyframe_interval", 30) == 30

    def test_clamp_below_min(self):
        from src.core.engine import _clamp_param
        assert _clamp_param("keyframe_interval", 1) == 10

    def test_clamp_above_max(self):
        from src.core.engine import _clamp_param
        assert _clamp_param("keyframe_interval", 999) == 120

    def test_clamp_segment_duration(self):
        from src.core.engine import _clamp_param
        assert _clamp_param("segment_duration", 30) == 60
        assert _clamp_param("segment_duration", 600) == 600
        assert _clamp_param("segment_duration", 9999) == 1800

    def test_clamp_concurrency(self):
        from src.core.engine import _clamp_param
        assert _clamp_param("max_concurrent_tasks", 0) == 1
        assert _clamp_param("max_concurrent_tasks", 3) == 3
        assert _clamp_param("max_concurrent_tasks", 10) == 5


class TestWithRetry:
    def test_retry_on_transient(self):
        import asyncio
        from src.services.ai_service import with_retry
        call_count = 0

        @with_retry(max_retries=3, base_delay=0.01)
        async def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("429 rate limit")
            return "success"

        result = asyncio.run(flaky())
        assert result == "success"
        assert call_count == 3

    def test_no_retry_on_permanent(self):
        import asyncio
        from src.services.ai_service import with_retry

        @with_retry(max_retries=3, base_delay=0.01)
        async def permanent_fail():
            raise ValueError("bad input")

        with pytest.raises(ValueError, match="bad input"):
            asyncio.run(permanent_fail())

    def test_retry_exhausted(self):
        import asyncio
        from src.services.ai_service import with_retry

        @with_retry(max_retries=2, base_delay=0.01)
        async def always_fail():
            raise Exception("500 server error")

        with pytest.raises(Exception, match="500"):
            asyncio.run(always_fail())


class TestClassifyErrorExtended:
    def test_timeout(self):
        from src.services.ai_service import classify_error
        assert classify_error(Exception("Connection timed out")) == "network"

    def test_ssl(self):
        from src.services.ai_service import classify_error
        assert classify_error(Exception("SSL handshake failed")) == "network"

    def test_format(self):
        from src.services.ai_service import classify_error
        assert classify_error(Exception("Unsupported format")) == "format"

    def test_no_such_file(self):
        from src.services.ai_service import classify_error
        assert classify_error(Exception("No such file or directory")) == "format"

    def test_401(self):
        from src.services.ai_service import classify_error
        assert classify_error(Exception("401 Unauthorized")) == "api"

    def test_429(self):
        from src.services.ai_service import classify_error
        assert classify_error(Exception("429 Too Many Requests")) == "api"


class TestNoteStylePrompts:
    def test_all_styles_defined(self):
        from src.services.ai_service import NOTE_STYLE_PROMPTS
        for style in ("standard", "summary", "action", "academic", "creative", "detailed"):
            assert style in NOTE_STYLE_PROMPTS
            assert "zh" in NOTE_STYLE_PROMPTS[style]
            assert "en" in NOTE_STYLE_PROMPTS[style]

    def test_prompts_not_empty(self):
        from src.services.ai_service import NOTE_STYLE_PROMPTS
        for style, langs in NOTE_STYLE_PROMPTS.items():
            for lang, prompt in langs.items():
                assert len(prompt) > 10, f"{style}/{lang} prompt too short"

    def test_detailed_prompt_has_distinct_coverage_requirements(self):
        from src.services.ai_service import NOTE_STYLE_PROMPTS
        assert NOTE_STYLE_PROMPTS["detailed"]["zh"] != NOTE_STYLE_PROMPTS["standard"]["zh"]
        assert NOTE_STYLE_PROMPTS["detailed"]["en"] != NOTE_STYLE_PROMPTS["standard"]["en"]
        assert "时间戳" in NOTE_STYLE_PROMPTS["detailed"]["zh"]
        assert "timestamps" in NOTE_STYLE_PROMPTS["detailed"]["en"].lower()

    def test_unknown_style_prompt_falls_back_to_standard(self):
        from src.services.ai_service import get_note_style_prompt
        assert get_note_style_prompt("unknown", "zh") == get_note_style_prompt("standard", "zh")


class TestTaskModel:
    def test_task_defaults(self):
        from src.models.task import Task, TaskStatus, ProcessingStage
        task = Task(id="t1", video_hash="h1", original_filename="test.mp4", video_path="/tmp/test.mp4")
        assert task.status == TaskStatus.PENDING
        assert task.stage == ProcessingStage.QUEUED
        assert task.language == "zh"
        assert task.note_style == "standard"
        assert task.progress == 0.0

    def test_task_status_enum(self):
        from src.models.task import TaskStatus
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.PROCESSING.value == "processing"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"

    def test_processing_stages(self):
        from src.models.task import ProcessingStage
        stages = list(ProcessingStage)
        assert len(stages) >= 8
        assert ProcessingStage.QUEUED.value == "queued"
        assert ProcessingStage.COMPLETED.value == "completed"