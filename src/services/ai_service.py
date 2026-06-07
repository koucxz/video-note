"""AI service abstraction with optional ASR, separate LLM/VLM clients."""
from __future__ import annotations

import asyncio
import base64
import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

NOTE_STYLE_PROMPTS = {
    "standard": {
        "zh": "生成结构化的视频笔记，包含要点、细节和总结。",
        "en": "Generate structured video notes with key points, details, and summary.",
    },
    "summary": {
        "zh": "生成简洁的摘要，只保留核心要点，每段不超过2句话。",
        "en": "Generate a concise summary with only core points, max 2 sentences per section.",
    },
    "action": {
        "zh": "生成行动导向的笔记，提取所有可执行的建议、步骤和方法，用清单格式呈现。",
        "en": "Generate action-oriented notes, extract all actionable advice, steps and methods in checklist format.",
    },
    "academic": {
        "zh": "生成学术风格的笔记，包含概念定义、理论框架、论证逻辑和参考要点。",
        "en": "Generate academic-style notes with concept definitions, theoretical frameworks, reasoning logic, and reference points.",
    },
    "creative": {
        "zh": "生成生动有趣的笔记，使用比喻、类比和故事化表达，让内容更易理解和记忆。",
        "en": "Generate vivid and engaging notes using metaphors, analogies, and storytelling.",
    },
}


def classify_error(exc: BaseException) -> str:
    msg = (str(exc) or exc.__class__.__name__).lower()
    if any(s in msg for s in ("timeout", "timed out", "connection", "network", "dns", "ssl", "eof")):
        return "network"
    if any(s in msg for s in ("ffmpeg", "ffprobe")):
        return "ffmpeg"
    if any(s in msg for s in ("unsupported", "invalid format", "no such file")):
        return "format"
    if any(s in msg for s in ("401", "403", "429", "500", "502", "503", "openai", "api", "rate")):
        return "api"
    return "unknown"


def with_retry(max_retries: int = 3, base_delay: float = 2.0):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as exc:
                    last_error = exc
                    msg = str(exc).lower()
                    transient = any(s in msg for s in ("429", "rate", "timeout", "timed out", "connection", "500", "502", "503", "504"))
                    if not transient or attempt == max_retries - 1:
                        raise
                    delay = base_delay * (2 ** attempt)
                    logger.warning("Transient error (%s), retry %d/%d in %.1fs", exc.__class__.__name__, attempt + 1, max_retries, delay)
                    await asyncio.sleep(delay)
            if last_error:
                raise last_error
        return wrapper
    return decorator


class AIProvider(ABC):
    @abstractmethod
    async def transcribe_audio(self, audio_path: str, language: Optional[str] = None) -> dict:
        pass

    @abstractmethod
    async def analyze_frames(self, frame_paths: List[str], prompt: str) -> str:
        pass

    @abstractmethod
    async def generate_outline(self, transcript: str, language: str = "zh") -> dict:
        pass

    @abstractmethod
    async def generate_note(self, outline: dict, context: str, language: str = "zh", note_style: str = "standard") -> str:
        pass

    @property
    def asr_enabled(self) -> bool:
        return False


class OpenAIProvider(AIProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", base_url: str = "https://api.openai.com/v1",
                 vlm_api_key=None, vlm_model=None, vlm_base_url=None,
                 asr_enabled=False, asr_api_key=None, asr_model="whisper-1", asr_base_url=None):
        from openai import AsyncOpenAI

        if not api_key:
            logger.warning("LLM api_key is empty - check .env / config.yaml")

        self._llm = AsyncOpenAI(api_key=api_key or "missing", base_url=base_url)
        self.model = model

        self._vlm = AsyncOpenAI(api_key=vlm_api_key or api_key or "missing", base_url=vlm_base_url or base_url)
        self.vlm_model = vlm_model or model

        self._asr_enabled = bool(asr_enabled and (asr_api_key or api_key))
        if self._asr_enabled:
            self._asr = AsyncOpenAI(api_key=asr_api_key or api_key, base_url=asr_base_url or base_url)
            self.asr_model = asr_model
        else:
            self._asr = None
            self.asr_model = asr_model

        logger.info("LLM=%s @ %s", model, base_url)
        logger.info("VLM=%s @ %s", self.vlm_model, vlm_base_url or base_url)
        logger.info("ASR=%s", "enabled" if self._asr_enabled else "disabled")

    @property
    def asr_enabled(self) -> bool:
        return self._asr_enabled

    @with_retry(max_retries=3, base_delay=3.0)
    async def transcribe_audio(self, audio_path: str, language: Optional[str] = None) -> dict:
        if not self._asr_enabled:
            return {"text": "", "segments": [], "language": language or "zh", "asr_skipped": True}
        logger.info("Transcribing: %s", audio_path)
        with open(audio_path, "rb") as fh:
            response = await self._asr.audio.transcriptions.create(
                model=self.asr_model, file=fh, language=language, response_format="verbose_json")
        segments = getattr(response, "segments", None) or []
        return {
            "text": getattr(response, "text", "") or "",
            "segments": [{"start": getattr(s, "start", 0), "end": getattr(s, "end", 0), "text": getattr(s, "text", "")} for s in segments],
            "language": getattr(response, "language", language or "zh"),
        }

    @with_retry(max_retries=3, base_delay=3.0)
    async def analyze_frames(self, frame_paths: List[str], prompt: str) -> str:
        if not frame_paths:
            return ""
        
        # Sample frames if too many (max 20 for better coverage)
        max_frames = 20
        if len(frame_paths) > max_frames:
            step = max(1, len(frame_paths) // max_frames)
            frame_paths = frame_paths[::step][:max_frames]
        
        logger.info("Analyzing %d frames via VLM (batched)", len(frame_paths))
        
        # Batch frames: 5 per batch to avoid API limits
        batch_size = 5
        all_analyses = []
        
        for i in range(0, len(frame_paths), batch_size):
            batch = frame_paths[i:i + batch_size]
            batch_num = i//batch_size + 1
            total_batches = (len(frame_paths) + batch_size - 1)//batch_size
            content = [{"type": "text", "text": f"{prompt}\n\nFrame batch {batch_num}/{total_batches}:"}]
            
            for path in batch:
                p = Path(path)
                if not p.exists():
                    continue
                # Use streaming read for large files
                b64 = base64.b64encode(p.read_bytes()).decode()
                content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
            
            try:
                response = await self._vlm.chat.completions.create(
                    model=self.vlm_model, messages=[{"role": "user", "content": content}], max_tokens=2048)
                analysis = response.choices[0].message.content or ""
                if analysis:
                    all_analyses.append(analysis)
                    logger.info("Frame batch %d/%d analyzed", i//batch_size + 1, (len(frame_paths) + batch_size - 1)//batch_size)
            except Exception as e:
                logger.warning("Frame batch %d failed: %s", i//batch_size + 1, e)
                continue
        
        return "\n\n".join(all_analyses) if all_analyses else ""

    @with_retry(max_retries=3, base_delay=3.0)
    async def generate_outline(self, transcript: str, language: str = "zh") -> dict:
        logger.info("Generating outline (lang=%s)", language)
        max_chars = 10000
        if len(transcript) > max_chars:
            transcript = transcript[:max_chars] + "..."
        lang_name = "Chinese" if language == "zh" else "English"
        prompt = (f"Generate an outline from the transcript in {lang_name}.\n\n"
                  f"Transcript:\n{transcript}\n\n"
                  'Return JSON: {"title": str, "sections": [{"heading": str, "points": [str]}]}')
        response = await self._llm.chat.completions.create(
            model=self.model, messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"})
        text = response.choices[0].message.content or "{}"
        tokens = getattr(response, 'usage', None)
        total = (getattr(tokens, 'total_tokens', 0) or 0) if tokens else 0
        try:
            result = json.loads(text)
        except json.JSONDecodeError:
            result = {"title": "Untitled", "sections": [{"heading": "Content", "points": [text[:400]]}]}
        result["_tokens"] = total
        return result

    @with_retry(max_retries=3, base_delay=3.0)
    async def generate_note(self, outline: dict, context: str, language: str = "zh", note_style: str = "standard") -> str:
        logger.info("Generating note (lang=%s, style=%s)", language, note_style)
        lang_instruction = "请使用中文生成笔记。" if language == "zh" else "Please generate the note in English."
        style_instruction = NOTE_STYLE_PROMPTS.get(note_style, NOTE_STYLE_PROMPTS["standard"]).get(language, NOTE_STYLE_PROMPTS["standard"]["zh"])
        prompt = (f"Generate detailed video notes.\n\n{lang_instruction}\n\n"
                  f"Style requirement: {style_instruction}\n\n"
                  f"Outline:\n{json.dumps(outline, ensure_ascii=False, indent=2)}\n\n"
                  f"Context:\n{context}\n\nOutput in Markdown format:")
        response = await self._llm.chat.completions.create(
            model=self.model, messages=[{"role": "user", "content": prompt}], max_tokens=8192)
        tokens = getattr(response, 'usage', None)
        total = (getattr(tokens, 'total_tokens', 0) or 0) if tokens else 0
        return response.choices[0].message.content or "", total


class AnthropicProvider(AIProvider):
    """Anthropic Claude provider using the Anthropic SDK."""

    def __init__(self, api_key: str, model: str = 'claude-sonnet-4-20250514', base_url: str = 'https://api.anthropic.com',
                 vlm_api_key=None, vlm_model=None, vlm_base_url=None,
                 asr_enabled=False, asr_api_key=None, asr_model='whisper-1', asr_base_url=None):
        import anthropic
        if not api_key:
            logger.warning('Anthropic api_key is empty')
        self._client = anthropic.AsyncAnthropic(api_key=api_key or 'missing', base_url=base_url)
        self.model = model
        self.vlm_model = vlm_model or model
        # Anthropic does not have native audio transcription
        self._asr_enabled = False
        self.asr_model = asr_model
        logger.info('Anthropic LLM=%s @ %s', model, base_url)
        logger.info('Anthropic VLM=%s', self.vlm_model)

    @property
    def asr_enabled(self) -> bool:
        return False

    async def transcribe_audio(self, audio_path: str, language=None) -> dict:
        logger.warning('Anthropic does not support audio transcription - skipping ASR')
        return {'text': '', 'segments': [], 'language': language or 'zh', 'asr_skipped': True}

    @with_retry(max_retries=3, base_delay=3.0)
    async def analyze_frames(self, frame_paths: list, prompt: str) -> str:
        if not frame_paths:
            return ''
        max_frames = 20
        if len(frame_paths) > max_frames:
            step = max(1, len(frame_paths) // max_frames)
            frame_paths = frame_paths[::step][:max_frames]

        logger.info('Analyzing %d frames via Anthropic VLM', len(frame_paths))
        batch_size = 5
        all_analyses = []
        for i in range(0, len(frame_paths), batch_size):
            batch = frame_paths[i:i + batch_size]
            content_blocks = []
            for path in batch:
                p = Path(path)
                if not p.exists():
                    continue
                import base64 as b64mod
                b64 = b64mod.b64encode(p.read_bytes()).decode()
                content_blocks.append({
                    'type': 'image',
                    'source': {'type': 'base64', 'media_type': 'image/jpeg', 'data': b64},
                })
            content_blocks.append({'type': 'text', 'text': prompt})
            try:
                response = await self._client.messages.create(
                    model=self.vlm_model, max_tokens=2048,
                    messages=[{'role': 'user', 'content': content_blocks}],
                )
                text = ''.join(b.text for b in response.content if hasattr(b, 'text'))
                if text:
                    all_analyses.append(text)
            except Exception as e:
                logger.warning('Anthropic frame batch failed: %s', e)
                continue
        return '\n\n'.join(all_analyses) if all_analyses else ''

    @with_retry(max_retries=3, base_delay=3.0)
    async def generate_outline(self, transcript: str, language: str = 'zh') -> dict:
        logger.info('Generating outline via Anthropic (lang=%s)', language)
        max_chars = 10000
        if len(transcript) > max_chars:
            transcript = transcript[:max_chars] + '...'
        lang_name = 'Chinese' if language == 'zh' else 'English'
        prompt = (f'Generate an outline from the transcript in {lang_name}.\n\n'
                  f'Transcript:\n{transcript}\n\n'
                  'Return ONLY valid JSON (no markdown fences): {"title": str, "sections": [{"heading": str, "points": [str]}]}')
        response = await self._client.messages.create(
            model=self.model, max_tokens=4096,
            messages=[{'role': 'user', 'content': prompt}],
        )
        text = ''.join(b.text for b in response.content if hasattr(b, 'text')).strip()
        # Strip markdown fences if present
        if text.startswith('`'):
            text = re.sub(r'^`(?:json)?\s*', '', text)
            text = re.sub(r'\s*`$', '', text)
        tokens_in = getattr(response.usage, 'input_tokens', 0) or 0
        tokens_out = getattr(response.usage, 'output_tokens', 0) or 0
        try:
            result = json.loads(text)
        except json.JSONDecodeError:
            result = {'title': 'Untitled', 'sections': [{'heading': 'Content', 'points': [text[:400]]}]}
        result['_tokens'] = tokens_in + tokens_out
        return result

    @with_retry(max_retries=3, base_delay=3.0)
    async def generate_note(self, outline: dict, context: str, language: str = 'zh', note_style: str = 'standard') -> str:
        logger.info('Generating note via Anthropic (lang=%s, style=%s)', language, note_style)
        lang_instruction = 'Please generate the note in Chinese.' if language == 'zh' else 'Please generate the note in English.'
        style_instruction = NOTE_STYLE_PROMPTS.get(note_style, NOTE_STYLE_PROMPTS['standard']).get(language, NOTE_STYLE_PROMPTS['standard']['zh'])
        prompt = (f'Generate detailed video notes.\n\n{lang_instruction}\n\n'
                  f'Style requirement: {style_instruction}\n\n'
                  f'Outline:\n{json.dumps(outline, ensure_ascii=False, indent=2)}\n\n'
                  f'Context:\n{context}\n\nOutput in Markdown format:')
        response = await self._client.messages.create(
            model=self.model, max_tokens=8192,
            messages=[{'role': 'user', 'content': prompt}],
        )
        tokens_in = getattr(response.usage, 'input_tokens', 0) or 0
        tokens_out = getattr(response.usage, 'output_tokens', 0) or 0
        return ''.join(b.text for b in response.content if hasattr(b, 'text')), tokens_in + tokens_out
