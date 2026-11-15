"""Checkpoint manager with thread-safe access, WAL mode, and note versioning."""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..models.task import ProcessingStage

logger = logging.getLogger(__name__)

_JSON_FIELDS = {"processing_overrides"}


def _budget_day() -> str:
    """Token budgets roll over at Beijing midnight, matching the UI wording."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d")


class CheckpointManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(db_path, check_same_thread=False, isolation_level=None)
        self.conn.execute("PRAGMA foreign_keys=ON")
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
                    display_name TEXT DEFAULT '',
                    video_path TEXT, language TEXT DEFAULT 'zh', note_style TEXT DEFAULT 'standard',
                    status TEXT, stage TEXT, progress REAL,
                    created_at TIMESTAMP, updated_at TIMESTAMP, completed_at TIMESTAMP,
                    note_path TEXT, error TEXT, error_kind TEXT)""")
            # Note versions table
            self.conn.execute(
                """CREATE TABLE IF NOT EXISTS note_versions (
                    id TEXT PRIMARY KEY, task_id TEXT NOT NULL, version_num INTEGER NOT NULL,
                    content TEXT NOT NULL, source TEXT DEFAULT 'generated',
                    style TEXT DEFAULT '', model_name TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE)""")
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_note_versions_task ON note_versions(task_id, version_num)")
            # Collections table
            self.conn.execute(
                """CREATE TABLE IF NOT EXISTS collections (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT DEFAULT '',
                    cover TEXT DEFAULT '', tags TEXT DEFAULT '[]',
                    sort_order INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
            self.conn.execute(
                """CREATE TABLE IF NOT EXISTS collection_notes (
                    collection_id TEXT NOT NULL, note_id TEXT NOT NULL, sort_order INTEGER DEFAULT 0,
                    PRIMARY KEY (collection_id, note_id),
                    FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE,
                    FOREIGN KEY (note_id) REFERENCES tasks(id) ON DELETE CASCADE)""")
            # Favorites table
            self.conn.execute(
                """CREATE TABLE IF NOT EXISTS favorites (
                    task_id TEXT PRIMARY KEY, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE)""")
            self.conn.execute(
                """CREATE TABLE IF NOT EXISTS qa_sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    scope TEXT NOT NULL DEFAULT '{}',
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL)""")
            self.conn.execute(
                """CREATE TABLE IF NOT EXISTS qa_messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    sources TEXT NOT NULL DEFAULT '[]',
                    tokens INTEGER DEFAULT 0,
                    created_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES qa_sessions(id) ON DELETE CASCADE)""")
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_qa_sessions_updated ON qa_sessions(updated_at DESC)"
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_qa_messages_session ON qa_messages(session_id, created_at)"
            )
            # Daily token budget: one row per calendar day, incremented from real provider usage.
            self.conn.execute(
                """CREATE TABLE IF NOT EXISTS token_usage (
                    day TEXT PRIMARY KEY, tokens INTEGER NOT NULL DEFAULT 0,
                    calls INTEGER NOT NULL DEFAULT 0, updated_at TIMESTAMP)""")
            for col, default in [("display_name", ""), ("language", "zh"), ("note_style", "standard"), ("error_kind", "unknown"),
                                  ("processing_overrides", "{}"), ("total_tokens", "0"),
                                  ("platform", ""), ("video_url", ""), ("model_name", "")]:
                try:
                    col_type = "TEXT" if col != "total_tokens" else "INTEGER"
                    self.conn.execute(f"ALTER TABLE tasks ADD COLUMN {col} {col_type} DEFAULT '{default}'")
                except sqlite3.OperationalError:
                    pass

    # ── Task CRUD ──

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
            # ``save_task`` is also used while a task is being retried or
            # resumed.  Preserve a name set through the rename API when the
            # in-memory Task object predates that rename.
            cur = self.conn.execute("SELECT display_name FROM tasks WHERE id = ?", (task.id,))
            existing = cur.fetchone()
            display_name = getattr(task, "display_name", "") or (existing[0] if existing else "") or ""
            self.conn.execute(
                """INSERT OR REPLACE INTO tasks
                (id, video_hash, original_filename, display_name, video_path, language, note_style,
                 status, stage, progress, created_at, updated_at, completed_at,
                 note_path, error, error_kind, processing_overrides, total_tokens)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (task.id, task.video_hash, task.original_filename, display_name, task.video_path,
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
        allowed = {"video_hash", "original_filename", "display_name", "video_path", "language", "note_style",
                    "status", "stage", "progress", "created_at", "updated_at", "completed_at",
                    "note_path", "error", "error_kind", "processing_overrides", "total_tokens",
                    "platform", "video_url", "model_name"}
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
            self.conn.execute("DELETE FROM note_versions WHERE task_id = ?", (task_id,))
            self.conn.execute("DELETE FROM collection_notes WHERE note_id = ?", (task_id,))
            self.conn.execute("DELETE FROM favorites WHERE task_id = ?", (task_id,))
            self.conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    def reset_running_to_failed(self) -> int:
        with self._lock:
            cur = self.conn.execute(
                "UPDATE tasks SET status='failed', error=COALESCE(error,'Interrupted, click retry'), "
                "error_kind='interrupted', updated_at=? WHERE status IN ('processing','pending')",
                (datetime.now(),))
            return cur.rowcount or 0

    # ── RAG chat sessions ──

    def create_qa_session(self, title: str = "新会话", scope: Optional[dict] = None) -> dict:
        """Create a persisted RAG conversation with its current note scope."""
        session_id = str(uuid.uuid4())
        now = datetime.now()
        title = (title or "新会话").strip()[:120] or "新会话"
        scope = scope if isinstance(scope, dict) else {}
        with self._lock:
            self.conn.execute(
                """INSERT INTO qa_sessions (id, title, scope, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (session_id, title, json.dumps(scope, ensure_ascii=False), now, now),
            )
        return {
            "id": session_id,
            "title": title,
            "scope": scope,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "message_count": 0,
            "preview": "",
        }

    def get_qa_session(self, session_id: str) -> Optional[dict]:
        with self._lock:
            cur = self.conn.execute(
                "SELECT id, title, scope, created_at, updated_at FROM qa_sessions WHERE id = ?",
                (session_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            count_cur = self.conn.execute(
                "SELECT COUNT(*) FROM qa_messages WHERE session_id = ?", (session_id,)
            )
            count_row = count_cur.fetchone()
            preview_cur = self.conn.execute(
                """SELECT content FROM qa_messages
                   WHERE session_id = ? ORDER BY created_at DESC, rowid DESC LIMIT 1""",
                (session_id,),
            )
            preview_row = preview_cur.fetchone()
        try:
            scope = json.loads(row[2] or "{}")
        except (TypeError, json.JSONDecodeError):
            scope = {}
        return {
            "id": row[0],
            "title": row[1],
            "scope": scope if isinstance(scope, dict) else {},
            "created_at": row[3].isoformat() if isinstance(row[3], datetime) else str(row[3]),
            "updated_at": row[4].isoformat() if isinstance(row[4], datetime) else str(row[4]),
            "message_count": int(count_row[0] if count_row else 0),
            "preview": (preview_row[0] if preview_row else "")[:160],
        }

    def list_qa_sessions(self, limit: int = 50) -> List[dict]:
        limit = max(1, min(100, int(limit)))
        with self._lock:
            cur = self.conn.execute(
                """SELECT s.id, s.title, s.scope, s.created_at, s.updated_at,
                          COUNT(m.id) AS message_count,
                          COALESCE((SELECT m2.content FROM qa_messages m2
                                    WHERE m2.session_id = s.id
                                    ORDER BY m2.created_at DESC, m2.rowid DESC LIMIT 1), '') AS preview
                   FROM qa_sessions s
                   LEFT JOIN qa_messages m ON m.session_id = s.id
                   GROUP BY s.id
                   HAVING COUNT(m.id) > 0
                   ORDER BY s.updated_at DESC, s.rowid DESC
                   LIMIT ?""",
                (limit,),
            )
            rows = cur.fetchall()
        result = []
        for row in rows:
            try:
                scope = json.loads(row[2] or "{}")
            except (TypeError, json.JSONDecodeError):
                scope = {}
            result.append({
                "id": row[0],
                "title": row[1],
                "scope": scope if isinstance(scope, dict) else {},
                "created_at": row[3].isoformat() if isinstance(row[3], datetime) else str(row[3]),
                "updated_at": row[4].isoformat() if isinstance(row[4], datetime) else str(row[4]),
                "message_count": int(row[5] or 0),
                "preview": (row[6] or "")[:160],
            })
        return result

    def update_qa_session(self, session_id: str, title: Optional[str] = None,
                          scope: Optional[dict] = None) -> Optional[dict]:
        fields = []
        values = []
        if title is not None:
            clean_title = str(title).strip()[:120] or "新会话"
            fields.append("title = ?")
            values.append(clean_title)
        if scope is not None:
            fields.append("scope = ?")
            values.append(json.dumps(scope if isinstance(scope, dict) else {}, ensure_ascii=False))
        if not fields:
            return self.get_qa_session(session_id)
        fields.append("updated_at = ?")
        values.append(datetime.now())
        values.append(session_id)
        with self._lock:
            cur = self.conn.execute(
                f"UPDATE qa_sessions SET {', '.join(fields)} WHERE id = ?", values
            )
            if not cur.rowcount:
                return None
        return self.get_qa_session(session_id)

    def delete_qa_session(self, session_id: str) -> bool:
        with self._lock:
            cur = self.conn.execute("DELETE FROM qa_sessions WHERE id = ?", (session_id,))
            return bool(cur.rowcount)

    def get_qa_messages(self, session_id: str, limit: Optional[int] = None) -> List[dict]:
        with self._lock:
            if limit:
                # 问答只需要最近几轮；长会话不必把全部消息读进内存
                cur = self.conn.execute(
                    """SELECT id, session_id, role, content, sources, tokens, created_at
                       FROM qa_messages WHERE session_id = ?
                       ORDER BY created_at DESC, rowid DESC LIMIT ?""",
                    (session_id, int(limit)),
                )
                rows = list(reversed(cur.fetchall()))
            else:
                cur = self.conn.execute(
                    """SELECT id, session_id, role, content, sources, tokens, created_at
                       FROM qa_messages WHERE session_id = ?
                       ORDER BY created_at, rowid""",
                    (session_id,),
                )
                rows = cur.fetchall()
        result = []
        for row in rows:
            try:
                sources = json.loads(row[4] or "[]")
            except (TypeError, json.JSONDecodeError):
                sources = []
            result.append({
                "id": row[0],
                "session_id": row[1],
                "role": row[2],
                "content": row[3],
                "sources": sources if isinstance(sources, list) else [],
                "tokens": int(row[5] or 0),
                "created_at": row[6].isoformat() if isinstance(row[6], datetime) else str(row[6]),
            })
        return result

    def save_qa_exchange(self, session_id: Optional[str], question: str, answer: str,
                         sources: Optional[list] = None, tokens: int = 0,
                         scope: Optional[dict] = None) -> dict:
        """Atomically persist one exchange, creating a session only when needed."""
        user_id = str(uuid.uuid4())
        assistant_id = str(uuid.uuid4())
        now = datetime.now()
        sources = sources if isinstance(sources, list) else []
        scope = scope if isinstance(scope, dict) else {}
        with self._lock:
            self.conn.execute("BEGIN")
            try:
                if session_id:
                    exists = self.conn.execute(
                        "SELECT 1 FROM qa_sessions WHERE id = ?", (session_id,)
                    ).fetchone()
                    if not exists:
                        raise KeyError(f"QA session not found: {session_id}")
                else:
                    session_id = str(uuid.uuid4())
                    title = question.strip()[:30] or "新会话"
                    self.conn.execute(
                        """INSERT INTO qa_sessions (id, title, scope, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?)""",
                        (session_id, title, json.dumps(scope, ensure_ascii=False), now, now),
                    )
                payload = json.dumps(sources, ensure_ascii=False)
                self.conn.execute(
                    """INSERT INTO qa_messages
                       (id, session_id, role, content, sources, tokens, created_at)
                       VALUES (?, ?, 'user', ?, '[]', 0, ?)""",
                    (user_id, session_id, question, now),
                )
                self.conn.execute(
                    """INSERT INTO qa_messages
                       (id, session_id, role, content, sources, tokens, created_at)
                       VALUES (?, ?, 'assistant', ?, ?, ?, ?)""",
                    (assistant_id, session_id, answer, payload, int(tokens or 0), now),
                )
                self.conn.execute(
                    "UPDATE qa_sessions SET scope = ?, updated_at = ? WHERE id = ?",
                    (json.dumps(scope, ensure_ascii=False), now, session_id),
                )
                self.conn.execute("COMMIT")
            except Exception:
                self.conn.execute("ROLLBACK")
                raise
        return {
            "session_id": session_id,
            "user_message": {"id": user_id, "session_id": session_id, "role": "user", "content": question,
                              "sources": [], "tokens": 0, "created_at": now.isoformat()},
            "assistant_message": {"id": assistant_id, "session_id": session_id, "role": "assistant", "content": answer,
                                   "sources": sources, "tokens": int(tokens or 0), "created_at": now.isoformat()},
        }

    # ── Note Versions ──

    def add_note_version(self, task_id: str, content: str, source: str = "generated",
                         style: str = "", model_name: str = "") -> dict:
        """Add a new note version. Returns the version dict."""
        with self._lock:
            cur = self.conn.execute(
                "SELECT COALESCE(MAX(version_num), 0) FROM note_versions WHERE task_id = ?",
                (task_id,))
            max_ver = cur.fetchone()[0]
            version_num = max_ver + 1
            ver_id = str(uuid.uuid4())[:12]
            now = datetime.now()
            self.conn.execute(
                """INSERT INTO note_versions (id, task_id, version_num, content, source, style, model_name, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (ver_id, task_id, version_num, content, source, style, model_name, now))
            # Also update task's note_path to point to the latest version file
            note_dir = Path("./data/output")
            note_dir.mkdir(parents=True, exist_ok=True)
            note_file = note_dir / f"{task_id[:8]}.md"
            note_file.write_text(content, encoding="utf-8")
            self.update_task(task_id, note_path=str(note_file))
            return {"id": ver_id, "task_id": task_id, "version_num": version_num,
                    "content": content, "source": source, "style": style,
                    "model_name": model_name, "created_at": now.isoformat()}

    def get_note_versions(self, task_id: str) -> List[dict]:
        """Get all versions for a task, ordered by version_num."""
        with self._lock:
            cur = self.conn.execute(
                """SELECT id, task_id, version_num, content, source, style, model_name, created_at
                FROM note_versions WHERE task_id = ? ORDER BY version_num""",
                (task_id,))
            return [{"id": r[0], "task_id": r[1], "version_num": r[2], "content": r[3],
                      "source": r[4], "style": r[5], "model_name": r[6],
                      "created_at": r[7].isoformat() if isinstance(r[7], datetime) else str(r[7])}
                    for r in cur.fetchall()]

    def get_note_version(self, task_id: str, version_id: str) -> Optional[dict]:
        """Get a specific version."""
        with self._lock:
            cur = self.conn.execute(
                """SELECT id, task_id, version_num, content, source, style, model_name, created_at
                FROM note_versions WHERE task_id = ? AND id = ?""",
                (task_id, version_id))
            row = cur.fetchone()
            if not row:
                return None
            return {"id": row[0], "task_id": row[1], "version_num": row[2], "content": row[3],
                    "source": row[4], "style": row[5], "model_name": row[6],
                    "created_at": row[7].isoformat() if isinstance(row[7], datetime) else str(row[7])}

    def delete_note_version(self, task_id: str, version_id: str) -> bool:
        """Delete a version. Returns False if it's the last version."""
        with self._lock:
            cur = self.conn.execute(
                "SELECT COUNT(*) FROM note_versions WHERE task_id = ?", (task_id,))
            count = cur.fetchone()[0]
            if count <= 1:
                return False  # Don't delete the last version
            self.conn.execute(
                "DELETE FROM note_versions WHERE task_id = ? AND id = ?",
                (task_id, version_id))
            # Update task's note_path to latest remaining version
            cur = self.conn.execute(
                """SELECT id, content FROM note_versions WHERE task_id = ? ORDER BY version_num DESC LIMIT 1""",
                (task_id,))
            row = cur.fetchone()
            if row:
                note_dir = Path("./data/output")
                note_dir.mkdir(parents=True, exist_ok=True)
                note_file = note_dir / f"{task_id[:8]}.md"
                note_file.write_text(row[1], encoding="utf-8")
                self.update_task(task_id, note_path=str(note_file))
            return True

    def revert_to_version(self, task_id: str, version_id: str) -> Optional[dict]:
        """Revert to a previous version by creating a new version with its content."""
        ver = self.get_note_version(task_id, version_id)
        if not ver:
            return None
        return self.add_note_version(task_id, ver["content"], source="reverted",
                                     style=ver.get("style", ""), model_name=ver.get("model_name", ""))

    # ── Collections ──

    def create_collection(self, name: str, description: str = "", cover: str = "", tags: list = None) -> dict:
        col_id = str(uuid.uuid4())[:12]
        tags_json = json.dumps(tags or [], ensure_ascii=False)
        now = datetime.now()
        with self._lock:
            self.conn.execute(
                """INSERT INTO collections (id, name, description, cover, tags, sort_order, created_at)
                VALUES (?, ?, ?, ?, ?, 0, ?)""",
                (col_id, name, description, cover, tags_json, now))
        return {"id": col_id, "name": name, "description": description, "cover": cover,
                "tags": tags or [], "created_at": now.isoformat()}

    def get_collections(self) -> List[dict]:
        with self._lock:
            cur = self.conn.execute("SELECT * FROM collections ORDER BY sort_order, created_at DESC")
            result = []
            for row in cur.fetchall():
                d = dict(zip([desc[0] for desc in cur.description], row))
                try:
                    d["tags"] = json.loads(d.get("tags", "[]"))
                except (json.JSONDecodeError, TypeError):
                    d["tags"] = []
                # Get note count
                count_cur = self.conn.execute(
                    "SELECT COUNT(*) FROM collection_notes WHERE collection_id = ?", (d["id"],))
                d["note_count"] = count_cur.fetchone()[0]
                result.append(d)
            return result

    def update_collection(self, col_id: str, **kwargs) -> None:
        allowed = {"name", "description", "cover", "tags", "sort_order"}
        safe = {}
        for k, v in kwargs.items():
            if k not in allowed:
                continue
            if k == "tags" and isinstance(v, list):
                v = json.dumps(v, ensure_ascii=False)
            safe[k] = v
        if not safe:
            return
        set_clause = ", ".join(f"{k} = ?" for k in safe)
        values = list(safe.values()) + [col_id]
        with self._lock:
            self.conn.execute(f"UPDATE collections SET {set_clause} WHERE id = ?", values)

    def delete_collection(self, col_id: str) -> None:
        with self._lock:
            self.conn.execute("DELETE FROM collection_notes WHERE collection_id = ?", (col_id,))
            self.conn.execute("DELETE FROM collections WHERE id = ?", (col_id,))

    def add_note_to_collection(self, col_id: str, task_id: str) -> None:
        with self._lock:
            self.conn.execute(
                "INSERT OR IGNORE INTO collection_notes (collection_id, note_id) VALUES (?, ?)",
                (col_id, task_id))

    def remove_note_from_collection(self, col_id: str, task_id: str) -> None:
        with self._lock:
            self.conn.execute(
                "DELETE FROM collection_notes WHERE collection_id = ? AND note_id = ?",
                (col_id, task_id))

    def get_collection_notes(self, col_id: str) -> List[str]:
        with self._lock:
            cur = self.conn.execute(
                "SELECT note_id FROM collection_notes WHERE collection_id = ? ORDER BY sort_order",
                (col_id,))
            return [r[0] for r in cur.fetchall()]

    def get_ungrouped_notes(self) -> List[str]:
        """Get task IDs not in any collection."""
        with self._lock:
            cur = self.conn.execute(
                """SELECT id FROM tasks WHERE status = 'completed'
                AND id NOT IN (SELECT note_id FROM collection_notes)""")
            return [r[0] for r in cur.fetchall()]

    # ── Daily token usage ──

    def add_token_usage(self, tokens: int, day: Optional[str] = None) -> int:
        """Add provider-reported tokens to a calendar day and return the new total."""
        day = day or _budget_day()
        amount = int(tokens or 0)
        with self._lock:
            self.conn.execute(
                """INSERT INTO token_usage (day, tokens, calls, updated_at) VALUES (?, ?, 1, ?)
                   ON CONFLICT(day) DO UPDATE SET tokens = tokens + excluded.tokens,
                   calls = calls + 1, updated_at = excluded.updated_at""",
                (day, max(0, amount), datetime.now()))
            cur = self.conn.execute("SELECT tokens FROM token_usage WHERE day = ?", (day,))
            row = cur.fetchone()
            return int(row[0]) if row else 0

    def get_token_usage(self, day: Optional[str] = None) -> dict:
        day = day or _budget_day()
        with self._lock:
            cur = self.conn.execute(
                "SELECT tokens, calls FROM token_usage WHERE day = ?", (day,))
            row = cur.fetchone()
        return {"day": day, "tokens": int(row[0] or 0) if row else 0, "calls": int(row[1] or 0) if row else 0}

    def get_token_usage_history(self, days: int = 14) -> List[dict]:
        days = max(1, min(90, int(days)))
        with self._lock:
            cur = self.conn.execute(
                "SELECT day, tokens, calls FROM token_usage ORDER BY day DESC LIMIT ?", (days,))
            return [{"day": r[0], "tokens": int(r[1] or 0), "calls": int(r[2] or 0)} for r in cur.fetchall()]

    # ── Favorites ──

    def toggle_favorite(self, task_id: str) -> bool:
        """Toggle favorite. Returns True if now favorited."""
        with self._lock:
            cur = self.conn.execute("SELECT 1 FROM favorites WHERE task_id = ?", (task_id,))
            if cur.fetchone():
                self.conn.execute("DELETE FROM favorites WHERE task_id = ?", (task_id,))
                return False
            else:
                self.conn.execute("INSERT INTO favorites (task_id) VALUES (?)", (task_id,))
                return True

    def is_favorite(self, task_id: str) -> bool:
        with self._lock:
            cur = self.conn.execute("SELECT 1 FROM favorites WHERE task_id = ?", (task_id,))
            return bool(cur.fetchone())

    def get_favorites(self) -> List[str]:
        with self._lock:
            cur = self.conn.execute("SELECT task_id FROM favorites ORDER BY created_at DESC")
            return [r[0] for r in cur.fetchall()]

    def is_favorited(self, task_id: str) -> bool:
        with self._lock:
            cur = self.conn.execute("SELECT 1 FROM favorites WHERE task_id = ?", (task_id,))
            return bool(cur.fetchone())
