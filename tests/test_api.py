"""API functional tests using FastAPI TestClient."""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture(scope="module")
def app(tmp_dir):
    """Create a test FastAPI app with isolated config."""
    os.environ["VIDEO_NOTE_DB"] = os.path.join(tmp_dir, "test.db")
    os.environ["VIDEO_NOTE_UPLOAD"] = os.path.join(tmp_dir, "uploads")
    os.environ["VIDEO_NOTE_OUTPUT"] = os.path.join(tmp_dir, "output")

    from src.main import app as fastapi_app
    return fastapi_app


@pytest.fixture
def client(app):
    return TestClient(app, raise_server_exceptions=False)


class TestHealthAPI:
    def test_health(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "llm_model" in data


class TestHistoryAPI:
    def test_history_empty(self, client):
        resp = client.get("/api/history?page=1&size=20")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 0

    def test_history_pagination(self, client):
        resp = client.get("/api/history?page=1&size=5")
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["size"] == 5

    def test_history_invalid_params(self, client):
        resp = client.get("/api/history?page=0")
        assert resp.status_code == 422

    def test_history_size_too_large(self, client):
        resp = client.get("/api/history?page=1&size=200")
        assert resp.status_code == 422


class TestNoteStylesAPI:
    def test_note_styles_include_detailed(self, client):
        resp = client.get("/api/note-styles")
        assert resp.status_code == 200
        assert "detailed" in resp.json()["styles"]


class TestUploadAPI:
    def test_upload_no_file(self, client):
        resp = client.post("/api/upload")
        assert resp.status_code == 422

    def test_upload_unsupported_format(self, client):
        resp = client.post("/api/upload", files={"file": ("test.txt", b"hello", "text/plain")})
        assert resp.status_code == 400
        assert "Unsupported format" in resp.json()["detail"]

    def test_upload_valid_format(self, client):
        """Test upload with a minimal valid video file header."""
        # Create a minimal MP4 file (just the ftyp box)
        ftyp = b'\x00\x00\x00\x20ftypisom\x00\x00\x02\x00isomiso2mp41'
        resp = client.post("/api/upload",
            files={"file": ("test.mp4", ftyp, "video/mp4")},
            data={"language": "zh", "note_style": "standard"})
        # Should either succeed (200) or fail with a processing error (500), not 400/422
        assert resp.status_code in (200, 500)

    def test_upload_detailed_style_is_preserved(self):
        import asyncio
        import io
        from starlette.datastructures import UploadFile
        from src.api.upload import upload_video

        engine = MagicMock()
        engine.dedup.process_upload = AsyncMock(return_value=("hash", Path("/tmp/test.mp4"), False))
        engine.checkpoint.find_task_by_hash.return_value = {"id": "existing-task"}
        file = UploadFile(filename="test.mp4", file=io.BytesIO(b"video"))

        with patch("src.api.upload.get_engine", return_value=engine):
            result = asyncio.run(upload_video(file=file, note_style="detailed"))

        assert result["note_style"] == "detailed"

    def test_unknown_upload_style_falls_back_to_standard(self):
        import asyncio
        import io
        from starlette.datastructures import UploadFile
        from src.api.upload import upload_video

        engine = MagicMock()
        engine.dedup.process_upload = AsyncMock(return_value=("hash", Path("/tmp/test.mp4"), False))
        engine.checkpoint.find_task_by_hash.return_value = {"id": "existing-task"}
        file = UploadFile(filename="test.mp4", file=io.BytesIO(b"video"))

        with patch("src.api.upload.get_engine", return_value=engine):
            result = asyncio.run(upload_video(file=file, note_style="unknown"))

        assert result["note_style"] == "standard"


class TestTaskAPI:
    def test_task_status_not_found(self, client):
        resp = client.get("/api/task/nonexistent/status")
        assert resp.status_code == 404

    def test_task_retry_not_found(self, client):
        resp = client.post("/api/task/nonexistent/retry")
        assert resp.status_code in (400, 404, 500)


class TestNoteAPI:
    def test_note_content_not_found(self, client):
        resp = client.get("/api/note/nonexistent/content")
        assert resp.status_code == 404

    def test_note_versions_not_found(self, client):
        resp = client.get("/api/note/nonexistent/versions")
        assert resp.status_code == 200  # Returns empty list for nonexistent task

    def test_note_download_not_found(self, client):
        resp = client.get("/api/note/nonexistent")
        assert resp.status_code == 404

    def test_pdf_renderer_rejects_invalid_data(self):
        from src.api.note import _validate_pdf
        with pytest.raises(RuntimeError):
            _validate_pdf(b'{"detail":"not a PDF"}')

    def test_export_helpers_return_video_filename_and_valid_pdf(self):
        from src.api.note import _markdown_to_html, _render_pdf, _safe_filename

        pdf_bytes = _render_pdf(_markdown_to_html("# Export test\n\nContent"))
        assert pdf_bytes.startswith(b"%PDF-")
        header = _safe_filename("视频名称", "pdf")
        assert 'filename="____.pdf"' in header
        assert "filename*=UTF-8''" in header

    def test_polish_detailed_style_is_preserved(self):
        import asyncio
        from src.api.note import polish_note

        engine = MagicMock()
        engine.checkpoint.get_task.return_value = {
            "note_style": "standard",
            "note_path": "",
            "language": "zh",
            "original_filename": "test.mp4",
            "total_tokens": 0,
        }
        engine.checkpoint.get_note_versions.return_value = [{"content": "Original note"}]
        engine.ai.generate_note = AsyncMock(return_value=("Detailed note", 12))
        engine.checkpoint.add_note_version.return_value = {"style": "detailed"}

        with patch("src.api.note.get_engine", return_value=engine):
            result = asyncio.run(polish_note("task-1", {"style": "detailed"}))

        assert result["version"]["style"] == "detailed"
        assert engine.ai.generate_note.await_args.args[-1] == "detailed"
        assert engine.checkpoint.add_note_version.call_args.kwargs["style"] == "detailed"

    def test_polish_unknown_style_is_rejected(self):
        import asyncio
        from fastapi import HTTPException
        from src.api.note import polish_note

        engine = MagicMock()
        engine.checkpoint.get_task.return_value = {"note_style": "standard"}
        with patch("src.api.note.get_engine", return_value=engine):
            with pytest.raises(HTTPException) as exc:
                asyncio.run(polish_note("task-1", {"style": "unknown"}))

        assert exc.value.status_code == 422
        engine.ai.generate_note.assert_not_called()


class TestSettingsAPI:
    def test_get_settings(self, client):
        resp = client.get("/api/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert "language" in data or "provider" in data

    def test_update_settings(self, client):
        resp = client.put("/api/settings", json={"language": "en"})
        assert resp.status_code == 200


class TestCollectionsAPI:
    def test_get_collections(self, client):
        resp = client.get("/api/collections")
        assert resp.status_code == 200
        data = resp.json()
        assert "collections" in data

    def test_create_collection(self, client):
        resp = client.post("/api/collections", json={"name": "Test API Col", "description": "Test"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Test API Col"

    def test_create_collection_empty_name(self, client):
        resp = client.post("/api/collections", json={"name": ""})
        assert resp.status_code == 400


class TestFavoritesAPI:
    def test_get_favorites(self, client):
        resp = client.get("/api/favorites")
        assert resp.status_code == 200
        assert "favorites" in resp.json()

    def test_toggle_favorite_not_found(self, client):
        resp = client.post("/api/favorites/nonexistent")
        # Should handle gracefully
        assert resp.status_code in (200, 404, 500)


class TestRAGAPI:
    def test_rag_ask_empty(self, client):
        resp = client.post("/api/rag/ask", json={"question": ""})
        assert resp.status_code == 400

    def test_rag_ask_no_notes(self, client):
        resp = client.post("/api/rag/ask", json={"question": "What is this about?"})
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data