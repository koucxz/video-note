"""任务数据模型"""
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional

class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ProcessingStage(str, Enum):
    QUEUED = "queued"
    EXTRACTING_AUDIO = "extracting_audio"
    TRANSCRIBING = "transcribing"
    GENERATING_OUTLINE = "generating_outline"
    EXTRACTING_KEYFRAMES = "extracting_keyframes"
    ANALYZING_CONTENT = "analyzing_content"
    GENERATING_NOTE = "generating_note"
    COMPLETED = "completed"

@dataclass
class Task:
    id: str
    video_hash: str
    original_filename: str
    video_path: str
    language: str = "zh"
    status: TaskStatus = TaskStatus.PENDING
    stage: ProcessingStage = ProcessingStage.QUEUED
    progress: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    note_path: Optional[str] = None
    error: Optional[str] = None
