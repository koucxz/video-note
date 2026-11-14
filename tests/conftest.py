"""Keep the test suite from writing tasks and uploads into the developer DB."""

import os
import tempfile
from pathlib import Path


_TEST_ROOT = Path(tempfile.mkdtemp(prefix="videonote-tests-"))
os.environ.setdefault("VIDEO_NOTE_DB", str(_TEST_ROOT / "test.db"))
os.environ.setdefault("VIDEO_NOTE_UPLOAD", str(_TEST_ROOT / "uploads"))
os.environ.setdefault("VIDEO_NOTE_OUTPUT", str(_TEST_ROOT / "output"))
