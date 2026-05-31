"""断点续传管理器"""
import sqlite3
import json
from datetime import datetime
from typing import Optional, Tuple
from ..models.task import ProcessingStage

class CheckpointManager:
    """断点续传管理器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                task_id TEXT,
                stage TEXT,
                progress REAL,
                data TEXT,
                updated_at TIMESTAMP,
                PRIMARY KEY (task_id, stage)
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                video_hash TEXT,
                original_filename TEXT,
                video_path TEXT,
                status TEXT,
                stage TEXT,
                progress REAL,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                completed_at TIMESTAMP,
                note_path TEXT,
                error TEXT
            )
        """)
        self.conn.commit()
    
    def save_progress(self, task_id: str, stage: ProcessingStage, 
                     progress: float, data: dict):
        """保存进度检查点"""
        now = datetime.now()
        self.conn.execute("""
            INSERT OR REPLACE INTO checkpoints 
            (task_id, stage, progress, data, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (task_id, stage.value, progress, json.dumps(data, ensure_ascii=False), now))
        self.conn.commit()
    
    def get_resume_point(self, task_id: str) -> Optional[Tuple[ProcessingStage, dict]]:
        """获取恢复点"""
        cursor = self.conn.execute("""
            SELECT stage, data FROM checkpoints 
            WHERE task_id = ? AND stage != 'completed'
            ORDER BY updated_at DESC LIMIT 1
        """, (task_id,))
        row = cursor.fetchone()
        if row:
            return ProcessingStage(row[0]), json.loads(row[1])
        return None
    
    def save_task(self, task):
        """保存任务"""
        self.conn.execute("""
            INSERT OR REPLACE INTO tasks 
            (id, video_hash, original_filename, video_path, status, stage, 
             progress, created_at, updated_at, completed_at, note_path, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task.id, task.video_hash, task.original_filename, task.video_path,
            task.status.value, task.stage.value, task.progress,
            task.created_at, task.updated_at, task.completed_at,
            task.note_path, task.error
        ))
        self.conn.commit()
    
    def get_task(self, task_id: str) -> Optional[dict]:
        """获取任务"""
        cursor = self.conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        )
        row = cursor.fetchone()
        if row:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
        return None
    
    def get_all_tasks(self) -> list:
        """获取所有任务"""
        cursor = self.conn.execute(
            "SELECT * FROM tasks ORDER BY created_at DESC"
        )
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def update_task(self, task_id: str, **kwargs):
        """更新任务字段"""
        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [task_id]
        self.conn.execute(
            f"UPDATE tasks SET {set_clause} WHERE id = ?",
            values
        )
        self.conn.commit()
    
    def delete_task(self, task_id: str):
        """删除任务及其检查点"""
        self.conn.execute("DELETE FROM checkpoints WHERE task_id = ?", (task_id,))
        self.conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self.conn.commit()

from pathlib import Path
