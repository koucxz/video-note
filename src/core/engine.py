"""视频笔记生成引擎"""
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from ..models.task import Task, TaskStatus, ProcessingStage
from ..core.checkpoint import CheckpointManager
from ..core.dedup import FileDeduplicator
from ..services.ai_service import AIProvider, OpenAIProvider
from ..services.audio_service import AudioService
from ..services.video_service import VideoService
from ..config.settings import AppConfig

logger = logging.getLogger(__name__)

class VideoNoteEngine:
    """视频笔记生成引擎"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.checkpoint = CheckpointManager(config.storage.db_path)
        self.dedup = FileDeduplicator(config.storage.upload_dir)
        self.ai = self._init_ai_provider(config)
        self.video_service = VideoService()
        self.audio_service = AudioService()
        
        Path(config.storage.output_dir).mkdir(parents=True, exist_ok=True)
    
    def _init_ai_provider(self, config: AppConfig) -> AIProvider:
        """初始化 AI 提供商"""
        if config.provider.type == "openai":
            return OpenAIProvider(
                api_key=config.provider.api_key,
                model=config.provider.model,
                base_url=config.provider.base_url,
                vlm_api_key=config.vlm.api_key,
                vlm_model=config.vlm.model,
                vlm_base_url=config.vlm.base_url
            )
        else:
            raise ValueError(f"不支持的 AI 提供商: {config.provider.type}")
    
    def create_task(self, filename: str, file_hash: str, video_path: str) -> Task:
        """创建新任务"""
        import uuid
        task = Task(
            id=str(uuid.uuid4()),
            video_hash=file_hash,
            original_filename=filename,
            video_path=str(video_path),
            status=TaskStatus.PENDING,
            stage=ProcessingStage.QUEUED,
            progress=0.0
        )
        self.checkpoint.save_task(task)
        return task
    
    async def process_video(self, task_id: str, video_path: str) -> str:
        """处理视频生成笔记"""
        self.checkpoint.update_task(
            task_id,
            status=TaskStatus.PROCESSING.value,
            stage=ProcessingStage.EXTRACTING_AUDIO.value,
            updated_at=datetime.now()
        )
        
        resume = self.checkpoint.get_resume_point(task_id)
        
        if resume:
            stage, data = resume
            logger.info(f"从 {stage.value} 恢复处理")
        else:
            stage = ProcessingStage.EXTRACTING_AUDIO
            data = {}
        
        stages = {
            ProcessingStage.EXTRACTING_AUDIO: self._extract_audio,
            ProcessingStage.TRANSCRIBING: self._transcribe,
            ProcessingStage.GENERATING_OUTLINE: self._generate_outline,
            ProcessingStage.EXTRACTING_KEYFRAMES: self._extract_keyframes,
            ProcessingStage.ANALYZING_CONTENT: self._analyze_content,
            ProcessingStage.GENERATING_NOTE: self._generate_note,
        }
        
        stage_list = list(stages.keys())
        start_idx = stage_list.index(stage) if stage in stage_list else 0
        
        for i in range(start_idx, len(stage_list)):
            current_stage = stage_list[i]
            
            try:
                self.checkpoint.update_task(
                    task_id,
                    stage=current_stage.value,
                    progress=i / len(stage_list),
                    updated_at=datetime.now()
                )
                
                data = await stages[current_stage](video_path, data)
                progress = (i + 1) / len(stage_list)
                
                self.checkpoint.save_progress(task_id, current_stage, progress, data)
                self.checkpoint.update_task(task_id, progress=progress, updated_at=datetime.now())
                
            except Exception as e:
                logger.error(f"阶段 {current_stage.value} 失败: {e}")
                self.checkpoint.save_progress(task_id, current_stage, i / len(stage_list), data)
                self.checkpoint.update_task(task_id, status=TaskStatus.FAILED.value, error=str(e), updated_at=datetime.now())
                raise
        
        note_path = data.get("note_path", "")
        self.checkpoint.save_progress(task_id, ProcessingStage.COMPLETED, 1.0, data)
        self.checkpoint.update_task(
            task_id,
            status=TaskStatus.COMPLETED.value,
            stage=ProcessingStage.COMPLETED.value,
            progress=1.0,
            note_path=note_path,
            completed_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        return note_path
    
    async def _extract_audio(self, video_path: str, data: dict) -> dict:
        audio_path = await self.audio_service.extract(video_path)
        data["audio_path"] = audio_path
        return data
    
    async def _transcribe(self, video_path: str, data: dict) -> dict:
        result = await self.ai.transcribe_audio(data["audio_path"])
        data["transcript"] = result
        return data
    
    async def _generate_outline(self, video_path: str, data: dict) -> dict:
        language = data["transcript"].get("language", "zh")
        outline = await self.ai.generate_outline(data["transcript"]["text"], language)
        data["outline"] = outline
        return data
    
    async def _extract_keyframes(self, video_path: str, data: dict) -> dict:
        interval = self.config.processing.keyframe_interval
        frames = await self.video_service.extract_keyframes(video_path, interval=interval)
        data["keyframes"] = frames
        return data
    
    async def _analyze_content(self, video_path: str, data: dict) -> dict:
        analysis = await self.ai.analyze_frames(
            data["keyframes"], 
            "请描述这些视频帧的内容，识别其中的关键信息、图表、文字等"
        )
        data["frame_analysis"] = analysis
        return data
    
    async def _generate_note(self, video_path: str, data: dict) -> dict:
        context = f"""转录内容:
{data['transcript']['text'][:3000]}

视频帧分析:
{data['frame_analysis']}"""
        
        note = await self.ai.generate_note(data["outline"], context)
        
        video_name = Path(video_path).stem
        note_path = Path(self.config.storage.output_dir) / f"{video_name}.md"
        note_path.write_text(note, encoding="utf-8")
        data["note_path"] = str(note_path)
        
        return data
    
    def retry_task(self, task_id: str):
        """重试失败的任务"""
        task = self.checkpoint.get_task(task_id)
        if not task:
            raise ValueError(f"任务不存在: {task_id}")
        if task["status"] != TaskStatus.FAILED.value:
            raise ValueError("只能重试失败的任务")
        
        self.checkpoint.update_task(task_id, status=TaskStatus.PENDING.value, error=None, updated_at=datetime.now())
        asyncio.create_task(self.process_video(task_id, task["video_path"]))

_engine: Optional[VideoNoteEngine] = None

def get_engine() -> VideoNoteEngine:
    global _engine
    if _engine is None:
        from ..config.settings import config
        _engine = VideoNoteEngine(config)
    return _engine
