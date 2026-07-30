"""Task data models"""
from __future__ import annotations

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
    EXTRACTING_SUBTITLES = "extracting_subtitles"
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
    note_style: str = "standard"
    status: TaskStatus = TaskStatus.PENDING
    stage: ProcessingStage = ProcessingStage.QUEUED
    progress: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    note_path: Optional[str] = None
    error: Optional[str] = None
    error_kind: str = "unknown"
    processing_overrides: dict = field(default_factory=dict)
    total_tokens: int = 0
