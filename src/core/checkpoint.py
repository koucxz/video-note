"""Checkpoint manager with thread-safe access and WAL mode."""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..models.task import ProcessingStage

logger = logging.getLogger(__name__)

_JSON_FIELDS = {"processing_overrides"}


class CheckpointManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(db_path, check_same_thread=False, isolation_level=None)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self._init_db()

    def _init_db(self) -> None:
        with self._lock:
            self.conn.execute(
                """CREATE TABLE IF NOT EXISTS checkpoints (
                    task_id TEXT, stage TEXT, progress REAL, data TEXT, updated_at TIMESTAMP,
                    PRIMARY KEY (task_id, stage))""")
            self.conn.execute(
                """CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY, video_hash TEXT, original_filename TEXT,
                    video_path TEXT, language TEXT DEFAULT 'zh', note_style TEXT DEFAULT 'standard',
                    status TEXT, stage TEXT, progress REAL,
                    created_at TIMESTAMP, updated_at TIMESTAMP, completed_at TIMESTAMP,
                    note_path TEXT, error TEXT, error_kind TEXT)""")
            for col, default in [("language", "zh"), ("note_style", "standard"), ("error_kind", "unknown"),
                                  ("processing_overrides", "{}"), ("total_tokens", "0")]:
                try:
                    col_type = "TEXT" if col != "total_tokens" else "INTEGER"
                    self.conn.execute(f"ALTER TABLE tasks ADD COLUMN {col} {col_type} DEFAULT '{default}'")
                except sqlite3.OperationalError:
                    pass

    def save_progress(self, task_id: str, stage: ProcessingStage, progress: float, data: dict) -> None:
        with self._lock:
            self.conn.execute(
                "INSERT OR REPLACE INTO checkpoints (task_id, stage, progress, data, updated_at) VALUES (?, ?, ?, ?, ?)",
                (task_id, stage.value, progress, json.dumps(data, ensure_ascii=False), datetime.now()))

    def get_resume_point(self, task_id: str) -> Optional[Tuple[ProcessingStage, dict]]:
        with self._lock:
            cur = self.conn.execute(
                "SELECT stage, data FROM checkpoints WHERE task_id = ? AND stage != 'completed' ORDER BY updated_at DESC LIMIT 1",
                (task_id,))
            row = cur.fetchone()
        if not row:
            return None
        try:
            return ProcessingStage(row[0]), json.loads(row[1] or "{}")
        except ValueError:
            return None

    def save_task(self, task) -> None:
        overrides_json = json.dumps(task.processing_overrides or {}, ensure_ascii=False)
        with self._lock:
            self.conn.execute(
                """INSERT OR REPLACE INTO tasks
                (id, video_hash, original_filename, video_path, language, note_style,
                 status, stage, progress, created_at, updated_at, completed_at,
                 note_path, error, error_kind, processing_overrides, total_tokens)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (task.id, task.video_hash, task.original_filename, task.video_path,
                 task.language, task.note_style, task.status.value, task.stage.value,
                 task.progress, task.created_at, task.updated_at, task.completed_at,
                 task.note_path, task.error, task.error_kind, overrides_json, task.total_tokens))

    def _row_to_dict(self, cur, row) -> dict:
        d = dict(zip((desc[0] for desc in cur.description), row))
        for f in _JSON_FIELDS:
            if f in d and isinstance(d[f], str):
                try:
                    d[f] = json.loads(d[f])
                except (json.JSONDecodeError, TypeError):
                    d[f] = {}
        return d

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            cur = self.conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = cur.fetchone()
            return self._row_to_dict(cur, row) if row else None

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        with self._lock:
            cur = self.conn.execute("SELECT * FROM tasks ORDER BY created_at DESC")
            return [self._row_to_dict(cur, r) for r in cur.fetchall()]

    def get_tasks_paginated(self, page: int = 1, size: int = 20) -> dict:
        with self._lock:
            cur = self.conn.execute("SELECT COUNT(*) FROM tasks")
            total = cur.fetchone()[0]
            offset = (page - 1) * size
            cur = self.conn.execute(
                "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (size, offset))
            items = [self._row_to_dict(cur, r) for r in cur.fetchall()]
            return {
                "items": items,
                "total": total,
                "page": page,
                "size": size,
                "pages": (total + size - 1) // size if size > 0 else 0,
            }

    def find_task_by_hash(self, video_hash: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            cur = self.conn.execute(
                "SELECT * FROM tasks WHERE video_hash = ? AND status = 'completed' ORDER BY completed_at DESC LIMIT 1",
                (video_hash,))
            row = cur.fetchone()
            return self._row_to_dict(cur, row) if row else None

    def update_task(self, task_id: str, **kwargs) -> None:
        if not kwargs:
            return
        allowed = {"video_hash", "original_filename", "video_path", "language", "note_style",
                    "status", "stage", "progress", "created_at", "updated_at", "completed_at",
                    "note_path", "error", "error_kind", "processing_overrides", "total_tokens"}
        safe = {}
        for k, v in kwargs.items():
            if k not in allowed:
                continue
            if k in _JSON_FIELDS and not isinstance(v, str):
                v = json.dumps(v, ensure_ascii=False)
            safe[k] = v
        if not safe:
            return
        set_clause = ", ".join(f"{k} = ?" for k in safe)
        values = list(safe.values()) + [task_id]
        with self._lock:
            self.conn.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", values)

    def delete_task(self, task_id: str) -> None:
        with self._lock:
            self.conn.execute("DELETE FROM checkpoints WHERE task_id = ?", (task_id,))
            self.conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    def reset_running_to_failed(self) -> int:
        with self._lock:
            cur = self.conn.execute(
                "UPDATE tasks SET status='failed', error=COALESCE(error,'Interrupted, click retry'), "
                "error_kind='interrupted', updated_at=? WHERE status IN ('processing','pending')",
                (datetime.now(),))
            return cur.rowcount or 0
