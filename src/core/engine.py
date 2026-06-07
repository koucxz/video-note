"""VideoNote engine with ASR-optional pipeline, concurrency semaphore, task handle registry."""
import asyncio
import logging
import aiofiles
from datetime import datetime
from pathlib import Path
from typing import Optional, Set

from ..models.task import Task, TaskStatus, ProcessingStage
from ..core.checkpoint import CheckpointManager
from ..core.dedup import FileDeduplicator
from ..services.ai_service import AIProvider, OpenAIProvider, AnthropicProvider, classify_error
from ..services.audio_service import AudioService
from ..services.video_service import VideoService
from ..config.settings import AppConfig

logger = logging.getLogger(__name__)

# Default processing parameter bounds
_PARAM_BOUNDS = {
    "keyframe_interval": (10, 120),
    "segment_duration": (60, 1800),
    "max_concurrent_tasks": (1, 5),
}


def _clamp_param(name: str, value, bounds: dict = _PARAM_BOUNDS) -> int:
    """Clamp a numeric parameter to its valid range."""
    lo, hi = bounds.get(name, (0, 999999))
    return max(lo, min(hi, int(value)))


class VideoNoteEngine:
    async def _broadcast(self, task_id: str, data: dict):
        """Broadcast task update via WebSocket."""
        try:
            from ..api.ws_manager import ws_manager
            await ws_manager.broadcast_task_update(task_id, data)
        except Exception:
            pass  # Don't let WS errors break processing

    def __init__(self, config: AppConfig):
        self.config = config
        self.checkpoint = CheckpointManager(config.storage.db_path)
        self.dedup = FileDeduplicator(config.storage.upload_dir)
        self.ai = self._init_ai_provider(config)
        self.video_service = VideoService()
        self.audio_service = AudioService()
        Path(config.storage.output_dir).mkdir(parents=True, exist_ok=True)

        # Concurrency control
        max_conc = max(1, config.processing.max_concurrent_tasks)
        self._semaphore = asyncio.Semaphore(max_conc)
        self._max_concurrent = max_conc
        self._running_tasks: Set[asyncio.Task] = set()
        logger.info("Concurrency limit: %d", max_conc)

        # On startup, mark zombie processing tasks as failed
        zombies = self.checkpoint.reset_running_to_failed()
        if zombies:
            logger.info("Reset %d zombie tasks to failed", zombies)

    def _init_ai_provider(self, config: AppConfig) -> AIProvider:
        provider_kwargs = dict(
            api_key=config.provider.api_key,
            model=config.provider.model,
            base_url=config.provider.base_url,
            vlm_api_key=config.vlm.api_key,
            vlm_model=config.vlm.model,
            vlm_base_url=config.vlm.base_url,
            asr_enabled=config.asr.enabled,
            asr_api_key=config.asr.api_key,
            asr_model=config.asr.model,
            asr_base_url=config.asr.base_url,
        )
        if config.provider.type == "openai":
            return OpenAIProvider(**provider_kwargs)
        if config.provider.type == "anthropic":
            return AnthropicProvider(**provider_kwargs)
        raise ValueError(f"Unsupported AI provider: {config.provider.type}")

    def update_concurrency(self, new_limit: int) -> int:
        """Dynamically adjust concurrency limit. Returns the applied limit."""
        new_limit = _clamp_param("max_concurrent_tasks", new_limit)
        if new_limit == self._max_concurrent:
            return new_limit
        old = self._max_concurrent
        # Adjust semaphore: if increasing, release additional permits
        if new_limit > old:
            for _ in range(new_limit - old):
                self._semaphore.release()
        self._max_concurrent = new_limit
        self.config.processing.max_concurrent_tasks = new_limit
        logger.info("Concurrency limit changed: %d -> %d", old, new_limit)
        return new_limit

    def create_task(self, filename: str, file_hash: str, video_path: str,
                    language: str = "zh", note_style: str = "standard",
                    processing_overrides: Optional[dict] = None) -> Task:
        import uuid
        overrides = processing_overrides or {}
        task = Task(
            id=str(uuid.uuid4()), video_hash=file_hash,
            original_filename=filename, video_path=str(video_path),
            language=language, note_style=note_style,
            status=TaskStatus.PENDING, stage=ProcessingStage.QUEUED, progress=0.0,
            processing_overrides=overrides,
        )
        self.checkpoint.save_task(task)
        return task

    def _get_task_param(self, task_overrides: dict, name: str) -> int:
        """Get a processing parameter: task override > global config > default."""
        if name in task_overrides:
            return _clamp_param(name, task_overrides[name])
        return getattr(self.config.processing, name, _PARAM_BOUNDS.get(name, (0, 0))[0])

    async def process_video(self, task_id: str, video_path: str) -> str:
        async with self._semaphore:
            return await self._process_video_inner(task_id, video_path)

    async def _process_video_inner(self, task_id: str, video_path: str) -> str:
        self.checkpoint.update_task(task_id, status=TaskStatus.PROCESSING.value,
            stage=ProcessingStage.EXTRACTING_AUDIO.value, updated_at=datetime.now())

        task = self.checkpoint.get_task(task_id)
        language = (task or {}).get("language", "zh")
        note_style = (task or {}).get("note_style", "standard")
        task_overrides = (task or {}).get("processing_overrides", {})

        resume = self.checkpoint.get_resume_point(task_id)
        if resume:
            stage, data = resume
            logger.info("Resuming from %s", stage.value)
        else:
            stage = ProcessingStage.EXTRACTING_AUDIO
            data = {"language": language, "note_style": note_style}

        # Build stage list, skipping TRANSCRIBING if ASR is disabled
        all_stages = [
            ProcessingStage.EXTRACTING_AUDIO,
            ProcessingStage.TRANSCRIBING,
            ProcessingStage.GENERATING_OUTLINE,
            ProcessingStage.EXTRACTING_KEYFRAMES,
            ProcessingStage.ANALYZING_CONTENT,
            ProcessingStage.GENERATING_NOTE,
        ]
        stage_handlers = {
            ProcessingStage.EXTRACTING_AUDIO: self._extract_audio,
            ProcessingStage.TRANSCRIBING: self._transcribe,
            ProcessingStage.GENERATING_OUTLINE: self._generate_outline,
            ProcessingStage.EXTRACTING_KEYFRAMES: self._extract_keyframes,
            ProcessingStage.ANALYZING_CONTENT: self._analyze_content,
            ProcessingStage.GENERATING_NOTE: self._generate_note,
        }

        if not self.ai.asr_enabled:
            all_stages = [s for s in all_stages if s != ProcessingStage.TRANSCRIBING]

        stage_list = all_stages
        start_idx = stage_list.index(stage) if stage in stage_list else 0

        for i in range(start_idx, len(stage_list)):
            current_stage = stage_list[i]
            try:
                self.checkpoint.update_task(task_id, stage=current_stage.value,
                    progress=i / len(stage_list), updated_at=datetime.now())
                data["language"] = language
                data["note_style"] = note_style
                data["task_id"] = task_id
                data["task_overrides"] = task_overrides
                data = await stage_handlers[current_stage](video_path, data)
                progress = (i + 1) / len(stage_list)
                self.checkpoint.save_progress(task_id, current_stage, progress, data)
                self.checkpoint.update_task(task_id, progress=progress, updated_at=datetime.now())
                await self._broadcast(task_id, {"stage": current_stage.value, "progress": progress, "status": "processing"})
            except Exception as exc:
                error_kind = classify_error(exc)
                logger.error("Stage %s failed (%s): %s", current_stage.value, error_kind, exc)
                self.checkpoint.save_progress(task_id, current_stage, i / len(stage_list), data)
                await self._broadcast(task_id, {"status": "failed", "error": str(exc), "error_kind": error_kind})
                self.checkpoint.update_task(task_id, status=TaskStatus.FAILED.value,
                    error=str(exc), error_kind=error_kind, updated_at=datetime.now())
                raise

        note_path = data.get("note_path", "")
        self.checkpoint.save_progress(task_id, ProcessingStage.COMPLETED, 1.0, data)
        self._cleanup_temp_files(video_path)
        await self._broadcast(task_id, {"status": "completed", "progress": 1.0, "stage": "completed"})
        self.checkpoint.update_task(task_id, status=TaskStatus.COMPLETED.value,
            stage=ProcessingStage.COMPLETED.value, progress=1.0,
            note_path=note_path, completed_at=datetime.now(), updated_at=datetime.now())
        return note_path

    async def _extract_audio(self, video_path: str, data: dict) -> dict:
        data["audio_path"] = await self.audio_service.extract(video_path)
        return data

    async def _transcribe(self, video_path: str, data: dict) -> dict:
        data["transcript"] = await self.ai.transcribe_audio(data["audio_path"])
        return data

    async def _generate_outline(self, video_path: str, data: dict) -> dict:
        language = data.get("language", "zh")
        transcript_text = data.get("transcript", {}).get("text", "")
        if not transcript_text:
            transcript_text = f"Video file: {Path(video_path).stem}"
            if data.get("frame_analysis"):
                transcript_text += f"\n\nVisual content:\n{data['frame_analysis'][:2000]}"
        data["outline"] = await self.ai.generate_outline(transcript_text, language)
        return data

    async def _extract_keyframes(self, video_path: str, data: dict) -> dict:
        overrides = data.get("task_overrides", {})
        interval = self._get_task_param(overrides, "keyframe_interval")
        data["keyframes"] = await self.video_service.extract_keyframes(video_path, interval=interval)
        return data

    async def _analyze_content(self, video_path: str, data: dict) -> dict:
        language = data.get("language", "zh")
        prompt = "描述这些视频帧的内容" if language == "zh" else "Describe the content of these video frames"
        data["frame_analysis"] = await self.ai.analyze_frames(data["keyframes"], prompt)
        return data

    async def _generate_note(self, video_path: str, data: dict) -> dict:
        language = data.get("language", "zh")
        note_style = data.get("note_style", "standard")
        task_id = data.get("task_id", "")
        transcript_text = data.get("transcript", {}).get("text", "")
        frame_analysis = data.get("frame_analysis", "")
        context = f"转录内容:\n{transcript_text[:3000]}\n\n视频帧分析:\n{frame_analysis}" if transcript_text else f"视频文件名: {Path(video_path).name}\n\n视频帧分析:\n{frame_analysis}"
        note = await self.ai.generate_note(data["outline"], context, language, note_style)
        video_name = Path(video_path).stem
        note_path = Path(self.config.storage.output_dir) / f"{task_id[:8]}_{video_name}.md"
        async with aiofiles.open(note_path, "w", encoding="utf-8") as f:
            await f.write(note)
        data["note_path"] = str(note_path)
        return data

    def _cleanup_temp_files(self, video_path: str) -> None:
        """Clean up temp audio and frame files after processing."""
        import shutil
        video_name = Path(video_path).stem
        audio_path = Path("./data/temp") / f"{video_name}.m4a"
        old_audio = Path("./data/temp") / f"{video_name}.mp3"
        for p in (audio_path, old_audio):
            try:
                if p.exists():
                    p.unlink()
                    logger.info("Cleaned temp audio: %s", p)
            except OSError as e:
                logger.warning("Failed to clean %s: %s", p, e)
        frames_dir = Path("./data/temp/frames") / video_name
        try:
            if frames_dir.exists():
                shutil.rmtree(frames_dir)
                logger.info("Cleaned temp frames: %s", frames_dir)
        except OSError as e:
            logger.warning("Failed to clean %s: %s", frames_dir, e)

    def cancel_task(self, task_id: str):
        task = self.checkpoint.get_task(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        if task["status"] not in (TaskStatus.PROCESSING.value, TaskStatus.PENDING.value):
            raise ValueError("Can only cancel processing or pending tasks")
        self.checkpoint.update_task(task_id, status=TaskStatus.FAILED.value,
            error="Cancelled by user", error_kind="cancelled", updated_at=datetime.now())
        logger.info("Task cancelled: %s", task_id)

    def retry_task(self, task_id: str):
        task = self.checkpoint.get_task(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        if task["status"] != TaskStatus.FAILED.value:
            raise ValueError("Can only retry failed tasks")
        self.checkpoint.update_task(task_id, status=TaskStatus.PENDING.value,
            error=None, error_kind=None, updated_at=datetime.now())
        t = asyncio.create_task(self._tracked_process(task_id, task["video_path"]))
        self._running_tasks.add(t)
        t.add_done_callback(self._running_tasks.discard)

    async def _tracked_process(self, task_id: str, video_path: str):
        try:
            await self.process_video(task_id, video_path)
        except Exception as exc:
            logger.error("Process failed %s: %s", task_id, exc)


_engine: Optional[VideoNoteEngine] = None


def get_engine() -> VideoNoteEngine:
    global _engine
    if _engine is None:
        from ..config.settings import config
        _engine = VideoNoteEngine(config)
    return _engine
