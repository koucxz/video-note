"""Test suite for VideoNote core modules."""
import os
import sys
import tempfile
import asyncio
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def checkpoint(tmp_dir):
    from src.core.checkpoint import CheckpointManager
    db_path = os.path.join(tmp_dir, "test.db")
    mgr = CheckpointManager(db_path)
    yield mgr
    mgr.conn.close()


@pytest.fixture
def dedup(tmp_dir):
    from src.core.dedup import FileDeduplicator
    return FileDeduplicator(os.path.join(tmp_dir, "uploads"))


class TestCheckpointManager:
    def test_init_creates_db(self, checkpoint, tmp_dir):
        assert Path(os.path.join(tmp_dir, "test.db")).exists()

    def test_save_and_get_task(self, checkpoint):
        from src.models.task import Task
        task = Task(id="t1", video_hash="abc", original_filename="demo.mp4", video_path="/tmp/demo.mp4")
        checkpoint.save_task(task)
        result = checkpoint.get_task("t1")
        assert result is not None
        assert result["original_filename"] == "demo.mp4"
        assert result["language"] == "zh"

    def test_update_task(self, checkpoint):
        from src.models.task import Task, TaskStatus
        task = Task(id="t2", video_hash="def", original_filename="test.mp4", video_path="/tmp/test.mp4")
        checkpoint.save_task(task)
        checkpoint.update_task("t2", status=TaskStatus.FAILED.value, error="oops", error_kind="api")
        result = checkpoint.get_task("t2")
        assert result["status"] == "failed"
        assert result["error_kind"] == "api"

    def test_delete_task(self, checkpoint):
        from src.models.task import Task
        task = Task(id="t-del", video_hash="x", original_filename="d.mp4", video_path="/d.mp4")
        checkpoint.save_task(task)
        checkpoint.delete_task("t-del")
        assert checkpoint.get_task("t-del") is None

    def test_find_task_by_hash(self, checkpoint):
        from src.models.task import Task, TaskStatus
        task = Task(id="h1", video_hash="unique123", original_filename="x.mp4", video_path="/x.mp4")
        checkpoint.save_task(task)
        checkpoint.update_task("h1", status=TaskStatus.COMPLETED.value, completed_at="2025-01-01")
        found = checkpoint.find_task_by_hash("unique123")
        assert found is not None
        assert found["id"] == "h1"

    def test_reset_running_to_failed(self, checkpoint):
        from src.models.task import Task, TaskStatus
        task = Task(id="z1", video_hash="z", original_filename="z.mp4", video_path="/z.mp4")
        checkpoint.save_task(task)
        checkpoint.update_task("z1", status=TaskStatus.PROCESSING.value)
        count = checkpoint.reset_running_to_failed()
        assert count >= 1
        result = checkpoint.get_task("z1")
        assert result["status"] == "failed"


class TestFileDeduplicator:
    def test_new_file(self, dedup):
        content = b"hello video"
        hash_val, path, is_new = asyncio.run(dedup.process_upload(content, "test.mp4"))
        assert is_new is True
        assert path.exists()

    def test_duplicate_file(self, dedup):
        content = b"duplicate"
        _, _, is_new1 = asyncio.run(dedup.process_upload(content, "a.mp4"))
        _, _, is_new2 = asyncio.run(dedup.process_upload(content, "b.mp4"))
        assert is_new1 is True
        assert is_new2 is False

    def test_different_content(self, dedup):
        _, p1, _ = asyncio.run(dedup.process_upload(b"AAA", "a.mp4"))
        _, p2, _ = asyncio.run(dedup.process_upload(b"BBB", "b.mp4"))
        assert p1 != p2


class TestConfig:
    def test_load_defaults(self):
        from src.config.settings import AppConfig
        cfg = AppConfig.load.__func__(AppConfig, config_path="/nonexistent.yaml")
        assert cfg.provider.type == "openai"
        assert cfg.asr.enabled is False

    def test_load_yaml_overrides_model(self, tmp_dir):
        import yaml
        yaml_path = os.path.join(tmp_dir, "test.yaml")
        with open(yaml_path, "w") as f:
            yaml.safe_dump({
                "provider": {"model": "test-model", "api_key": "sk-test"},
            }, f)
        from src.config.settings import AppConfig
        cfg = AppConfig.load.__func__(AppConfig, config_path=yaml_path)
        assert cfg.provider.model == "test-model"
        assert cfg.provider.api_key == "sk-test"


class TestClassifyError:
    def test_network(self):
        from src.services.ai_service import classify_error
        assert classify_error(Exception("Connection timed out")) == "network"

    def test_api(self):
        from src.services.ai_service import classify_error
        assert classify_error(Exception("429 rate limit")) == "api"

    def test_ffmpeg(self):
        from src.services.ai_service import classify_error
        assert classify_error(Exception("ffmpeg failed")) == "ffmpeg"

    def test_unknown(self):
        from src.services.ai_service import classify_error
        assert classify_error(Exception("something")) == "unknown"
