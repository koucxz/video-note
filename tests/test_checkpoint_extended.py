"""Extended tests for CheckpointManager: note versions, collections, favorites, pagination."""
import os
import sys
import tempfile
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
def task_factory(checkpoint):
    """Create tasks for testing."""
    from src.models.task import Task, TaskStatus
    created = []

    def _create(task_id=None, filename="test.mp4", status=TaskStatus.COMPLETED, note_style="standard"):
        import uuid
        tid = task_id or str(uuid.uuid4())[:8]
        task = Task(
            id=tid,
            video_hash=f"hash_{tid}",
            original_filename=filename,
            video_path=f"/tmp/{filename}",
            note_style=note_style,
        )
        checkpoint.save_task(task)
        if status != TaskStatus.PENDING:
            checkpoint.update_task(tid, status=status.value)
        created.append(tid)
        return tid

    yield _create


class TestNoteVersions:
    def test_add_version(self, checkpoint, task_factory):
        tid = task_factory()
        ver = checkpoint.add_note_version(tid, "# Test Note\nContent here", source="generated")
        assert ver["task_id"] == tid
        assert ver["version_num"] == 1
        assert ver["content"] == "# Test Note\nContent here"
        assert ver["source"] == "generated"

    def test_multiple_versions(self, checkpoint, task_factory):
        tid = task_factory()
        checkpoint.add_note_version(tid, "Version 1", source="generated")
        checkpoint.add_note_version(tid, "Version 2", source="manual")
        checkpoint.add_note_version(tid, "Version 3", source="repolish")
        versions = checkpoint.get_note_versions(tid)
        assert len(versions) == 3
        assert versions[0]["version_num"] == 1
        assert versions[1]["version_num"] == 2
        assert versions[2]["version_num"] == 3
        assert versions[2]["source"] == "repolish"

    def test_get_note_version(self, checkpoint, task_factory):
        tid = task_factory()
        ver = checkpoint.add_note_version(tid, "Content", source="generated")
        fetched = checkpoint.get_note_version(tid, ver["id"])
        assert fetched is not None
        assert fetched["content"] == "Content"
        assert fetched["id"] == ver["id"]

    def test_get_nonexistent_version(self, checkpoint, task_factory):
        tid = task_factory()
        assert checkpoint.get_note_version(tid, "nonexistent") is None

    def test_delete_version(self, checkpoint, task_factory):
        tid = task_factory()
        v1 = checkpoint.add_note_version(tid, "V1")
        v2 = checkpoint.add_note_version(tid, "V2")
        assert checkpoint.delete_note_version(tid, v1["id"]) is True
        versions = checkpoint.get_note_versions(tid)
        assert len(versions) == 1
        assert versions[0]["content"] == "V2"

    def test_cannot_delete_last_version(self, checkpoint, task_factory):
        tid = task_factory()
        v1 = checkpoint.add_note_version(tid, "Only version")
        assert checkpoint.delete_note_version(tid, v1["id"]) is False
        versions = checkpoint.get_note_versions(tid)
        assert len(versions) == 1

    def test_revert_to_version(self, checkpoint, task_factory):
        tid = task_factory()
        v1 = checkpoint.add_note_version(tid, "Original")
        checkpoint.add_note_version(tid, "Changed")
        # Revert to first version creates a new version with original content
        reverted = checkpoint.revert_to_version(tid, v1["id"])
        assert reverted is not None
        assert reverted["source"] == "reverted"
        assert reverted["content"] == "Original"
        all_versions = checkpoint.get_note_versions(tid)
        assert len(all_versions) == 3  # Original + Changed + Reverted

    def test_detailed_style_round_trips_and_reverts(self, checkpoint, task_factory):
        tid = task_factory(note_style="detailed")
        original = checkpoint.add_note_version(tid, "Detailed original", source="generated", style="detailed")
        checkpoint.add_note_version(tid, "Changed", source="manual", style="standard")
        fetched = checkpoint.get_note_version(tid, original["id"])
        assert fetched["style"] == "detailed"
        reverted = checkpoint.revert_to_version(tid, original["id"])
        assert reverted["style"] == "detailed"

    def test_revert_nonexistent(self, checkpoint, task_factory):
        tid = task_factory()
        assert checkpoint.revert_to_version(tid, "nonexistent") is None


class TestCollections:
    def test_create_collection(self, checkpoint):
        col = checkpoint.create_collection("Test Collection", description="A test", tags=["ai", "ml"])
        assert col["name"] == "Test Collection"
        assert col["description"] == "A test"
        assert col["tags"] == ["ai", "ml"]

    def test_get_collections(self, checkpoint):
        checkpoint.create_collection("Col A")
        checkpoint.create_collection("Col B")
        cols = checkpoint.get_collections()
        assert len(cols) == 2
        names = {c["name"] for c in cols}
        assert "Col A" in names
        assert "Col B" in names

    def test_update_collection(self, checkpoint):
        col = checkpoint.create_collection("Old Name")
        checkpoint.update_collection(col["id"], name="New Name", description="Updated")
        cols = checkpoint.get_collections()
        updated = [c for c in cols if c["id"] == col["id"]][0]
        assert updated["name"] == "New Name"
        assert updated["description"] == "Updated"

    def test_delete_collection(self, checkpoint):
        col = checkpoint.create_collection("To Delete")
        checkpoint.delete_collection(col["id"])
        cols = checkpoint.get_collections()
        assert len(cols) == 0

    def test_add_note_to_collection(self, checkpoint, task_factory):
        tid = task_factory()
        col = checkpoint.create_collection("My Col")
        checkpoint.add_note_to_collection(col["id"], tid)
        notes = checkpoint.get_collection_notes(col["id"])
        assert tid in notes

    def test_remove_note_from_collection(self, checkpoint, task_factory):
        tid = task_factory()
        col = checkpoint.create_collection("My Col")
        checkpoint.add_note_to_collection(col["id"], tid)
        checkpoint.remove_note_from_collection(col["id"], tid)
        notes = checkpoint.get_collection_notes(col["id"])
        assert tid not in notes

    def test_collection_note_count(self, checkpoint, task_factory):
        t1 = task_factory()
        t2 = task_factory()
        col = checkpoint.create_collection("Count Test")
        checkpoint.add_note_to_collection(col["id"], t1)
        checkpoint.add_note_to_collection(col["id"], t2)
        cols = checkpoint.get_collections()
        assert cols[0]["note_count"] == 2

    def test_ungrouped_notes(self, checkpoint, task_factory):
        t1 = task_factory()
        t2 = task_factory()
        col = checkpoint.create_collection("Col")
        checkpoint.add_note_to_collection(col["id"], t1)
        ungrouped = checkpoint.get_ungrouped_notes()
        assert t1 not in ungrouped
        assert t2 in ungrouped


class TestFavorites:
    def test_toggle_favorite(self, checkpoint, task_factory):
        tid = task_factory()
        assert checkpoint.toggle_favorite(tid) is True  # Now favorited
        assert checkpoint.toggle_favorite(tid) is False  # Now unfavored

    def test_is_favorite(self, checkpoint, task_factory):
        tid = task_factory()
        assert checkpoint.is_favorite(tid) is False
        checkpoint.toggle_favorite(tid)
        assert checkpoint.is_favorite(tid) is True

    def test_get_favorites(self, checkpoint, task_factory):
        t1 = task_factory()
        t2 = task_factory()
        checkpoint.toggle_favorite(t1)
        checkpoint.toggle_favorite(t2)
        favs = checkpoint.get_favorites()
        assert len(favs) == 2
        assert t1 in favs
        assert t2 in favs


class TestPagination:
    def test_paginated_basic(self, checkpoint, task_factory):
        for i in range(5):
            task_factory(filename=f"video_{i}.mp4")
        result = checkpoint.get_tasks_paginated(page=1, size=3)
        assert len(result["items"]) == 3
        assert result["total"] == 5
        assert result["pages"] == 2

    def test_paginated_page_2(self, checkpoint, task_factory):
        for i in range(5):
            task_factory(filename=f"video_{i}.mp4")
        result = checkpoint.get_tasks_paginated(page=2, size=3)
        assert len(result["items"]) == 2

    def test_paginated_empty(self, checkpoint):
        result = checkpoint.get_tasks_paginated(page=1, size=10)
        assert len(result["items"]) == 0
        assert result["total"] == 0

    def test_get_all_tasks(self, checkpoint, task_factory):
        for i in range(3):
            task_factory()
        all_tasks = checkpoint.get_all_tasks()
        assert len(all_tasks) == 3