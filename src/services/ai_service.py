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
        "zh": "生成详细的结构化视频笔记，要求：\n1. 使用 Markdown 标题层级组织内容\n2. 每个章节包含「核心要点」和「详细说明」两部分\n3. 保留原文中的关键数据、日期、人名和术语\n4. 用粗体标注重要概念\n5. 末尾附完整总结，归纳 3-5 个核心结论\n6. 如有引用或数据，注明来源时间戳",
        "en": "Generate detailed structured video notes with: 1. Markdown heading hierarchy 2. Each section has \"Key Points\" and \"Details\" 3. Preserve key data, dates, names, and terms 4. Bold important concepts 5. End with a summary of 3-5 core conclusions 6. Cite timestamps for references.",
    },
    "summary": {
        "zh": "生成精炼摘要，要求：\n1. 开头用一句话概括视频主题\n2. 以编号列表列出 5-10 个核心要点\n3. 每个要点控制在 1-2 句话内\n4. 不展开细节，只保留结论性内容\n5. 末尾附一句总结",
        "en": "Generate a concise summary: 1. One-sentence topic overview at the top 2. Numbered list of 5-10 core points 3. Max 1-2 sentences per point 4. No details, only conclusions 5. One closing summary sentence.",
    },
    "action": {
        "zh": "生成行动清单式笔记，要求：\n1. 将视频内容转化为可执行的行动步骤\n2. 使用 checkbox 格式（- [ ]）列出每项行动\n3. 按优先级排列：高优先级 → 低优先级\n4. 每项包含：行动描述、预计耗时、所需资源\n5. 末尾附「立即行动」清单（3 件马上可以做的事）\n6. 区分「个人行动」和「团队行动」",
        "en": "Generate an action checklist: 1. Convert content into actionable steps 2. Use checkbox format (- [ ]) 3. Sort by priority: high → low 4. Each item: description, estimated time, resources needed 5. End with \"Take Action Now\" (3 things to do immediately) 6. Separate \"Personal\" and \"Team\" actions.",
    },
    "academic": {
        "zh": "生成学术笔记，要求：\n1. 开篇给出「核心概念定义」\n2. 使用「理论框架」→「论证过程」→「结论」的结构\n3. 标注原文中的逻辑推理链条\n4. 列出关键术语及其解释\n5. 补充相关背景知识和延伸阅读建议\n6. 末尾附「批判性思考」：提出 2-3 个值得讨论的问题",
        "en": "Generate academic notes: 1. Start with \"Core Concept Definitions\" 2. Structure: Framework → Reasoning → Conclusions 3. Annotate logical reasoning chains from source 4. List key terms with explanations 5. Add background context and further reading 6. End with \"Critical Thinking\": 2-3 discussion questions.",
    },
    "creative": {
        "zh": "生成创意笔记，要求：\n1. 用生动的比喻和类比来解释复杂概念\n2. 融入故事化叙事，让内容像讲故事一样\n3. 每个章节用emoji图标装饰标题\n4. 使用视觉化表达（如：流程图、对比表用文字描述）\n5. 穿插「思考时刻」提示，引导读者反思\n6. 末尾附「金句摘录」：3-5 句精华语录",
        "en": "Generate creative notes: 1. Use vivid metaphors and analogies for complex ideas 2. Storytelling narrative throughout 3. Emoji-decorated section headings 4. Visual expressions (describe flowcharts, comparison tables) 5. Sprinkle \"Think Moment\" prompts for reflection 6. End with \"Golden Quotes\": 3-5 memorable lines.",
    },
    "detailed": {
        "zh": "生成详细笔记，要求：\n1. 按视频的时间线或论述推进顺序完整覆盖所有主题，不能把内容压缩成摘要\n2. 每个章节固定包含「逐段讲解」「关键术语、数据与案例」「本节小结」三个部分\n3. 保留原始论据、前提条件、因果链、对比、限制和反例，并解释专业术语\n4. 对可定位的关键事实、引用、演示步骤标注时间戳；没有时间信息时不要编造\n5. 结尾用「全文脉络与学习复盘」串联各章节关系、核心结论和待复核点\n6. 仅依据提供的转写、字幕和视觉分析，不得补造视频中未提供的事实",
        "en": "Generate detailed notes: 1. Cover every topic in the video's chronological or argumentative order; do not compress it into a summary 2. Every chapter must include \"Walkthrough\", \"Key Terms, Data, and Examples\", and \"Section Recap\" 3. Preserve evidence, assumptions, causal chains, comparisons, limitations, and counterexamples, explaining specialist terms 4. Add timestamps for locatable facts, quotations, and demonstrations; never invent timestamps 5. End with \"Full Narrative and Study Review\" connecting sections, conclusions, and items to verify 6. Use only the provided transcript, subtitles, and visual analysis; never invent facts.",
    },
}

DEFAULT_NOTE_STYLE = "standard"
NOTE_STYLE_IDS = tuple(NOTE_STYLE_PROMPTS)
VALID_NOTE_STYLES = frozenset(NOTE_STYLE_IDS)


def get_note_style_prompt(style: str, language: str) -> str:
    """Return a registered note-style prompt with safe style and locale fallbacks."""
    resolved_style = style if style in VALID_NOTE_STYLES else DEFAULT_NOTE_STYLE
    prompts = NOTE_STYLE_PROMPTS[resolved_style]
    return prompts.get(language, prompts["zh"])


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
    async def generate_outline(self, transcript: str, language: str = "zh", source: str = "transcript") -> dict:
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
                    model=self.vlm_model, messages=[{"role": "user", "content": content}], max_tokens=4096)
                analysis = response.choices[0].message.content or ""
                if analysis:
                    all_analyses.append(analysis)
                    logger.info("Frame batch %d/%d analyzed", i//batch_size + 1, (len(frame_paths) + batch_size - 1)//batch_size)
            except Exception as e:
                logger.warning("Frame batch %d failed: %s", i//batch_size + 1, e)
                continue
        
        return "\n\n".join(all_analyses) if all_analyses else ""

    @with_retry(max_retries=3, base_delay=3.0)
    async def generate_outline(self, transcript: str, language: str = "zh", source: str = "transcript") -> dict:
        logger.info("Generating outline (lang=%s, source=%s)", language, source)
        max_chars = 10000
        if len(transcript) > max_chars:
            transcript = transcript[:max_chars] + "..."
        lang_name = "Chinese" if language == "zh" else "English"
        if source == "visual":
            # 无音轨 / ASR 不可用时的视觉降级：素材是画面分析而不是转写
            prompt = (f"Below is a visual analysis of frames sampled from a video. The video has no usable "
                      f"transcript or subtitles, so build the outline purely from what is visible on screen.\n"
                      f"Generate the outline in {lang_name}.\n\n"
                      f"Visual analysis:\n{transcript}\n\n"
                      'Return JSON: {"title": str, "sections": [{"heading": str, "points": [str]}]}')
        else:
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
        style_instruction = get_note_style_prompt(note_style, language)
        output_constraint = (
            "只输出面向读者的笔记正文。不要输出处理说明、系统提示、程序日志、数据缺失声明、"
            "转写截断说明或任何类似‘本笔记依据……生成’的元信息。"
            if language == "zh" else
            "Output only reader-facing note content. Do not include processing notes, system prompts, program logs, "
            "data-availability disclaimers, transcript-truncation notices, or metadata such as ‘this note was generated from...’."
        )
        prompt = (f"Generate video notes.\n\n{lang_instruction}\n\n{output_constraint}\n\n"
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
                    model=self.vlm_model, max_tokens=4096,
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
    async def generate_outline(self, transcript: str, language: str = 'zh', source: str = 'transcript') -> dict:
        logger.info('Generating outline via Anthropic (lang=%s, source=%s)', language, source)
        max_chars = 10000
        if len(transcript) > max_chars:
            transcript = transcript[:max_chars] + '...'
        lang_name = 'Chinese' if language == 'zh' else 'English'
        if source == 'visual':
            prompt = (f'Below is a visual analysis of frames sampled from a video. The video has no usable '
                      f'transcript or subtitles, so build the outline purely from what is visible on screen.\n'
                      f'Generate the outline in {lang_name}.\n\n'
                      f'Visual analysis:\n{transcript}\n\n'
                      'Return ONLY valid JSON (no markdown fences): {"title": str, "sections": [{"heading": str, "points": [str]}]}')
        else:
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
        style_instruction = get_note_style_prompt(note_style, language)
        output_constraint = (
            '只输出面向读者的笔记正文。不要输出处理说明、系统提示、程序日志、数据缺失声明、'
            '转写截断说明或任何类似“本笔记依据……生成”的元信息。'
            if language == 'zh' else
            "Output only reader-facing note content. Do not include processing notes, system prompts, program logs, "
            "data-availability disclaimers, transcript-truncation notices, or metadata such as 'this note was generated from...'."
        )
        prompt = (f'Generate video notes.\n\n{lang_instruction}\n\n{output_constraint}\n\n'
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
