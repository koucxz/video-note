"""AI 服务抽象层"""
import json
import base64
import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)

def with_retry(max_retries=3, base_delay=2.0):
    """重试装饰器，指数退避"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if "429" in str(e) or "rate" in str(e).lower():
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"Rate limited, retry {attempt+1}/{max_retries} after {delay}s")
                        await asyncio.sleep(delay)
                    else:
                        raise
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
    async def generate_note(self, outline: dict, context: str) -> str:
        pass


class OpenAIProvider(AIProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o", base_url: str = "https://api.openai.com/v1",
                 vlm_api_key: str = None, vlm_model: str = None, vlm_base_url: str = None):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.vlm_client = AsyncOpenAI(api_key=vlm_api_key or api_key, base_url=vlm_base_url or base_url)
        self.vlm_model = vlm_model or model
        logger.info(f"LLM: {model} @ {base_url}")
        logger.info(f"VLM: {self.vlm_model} @ {vlm_base_url or base_url}")
    
    @with_retry(max_retries=3, base_delay=3.0)
    async def transcribe_audio(self, audio_path: str, language: Optional[str] = None) -> dict:
        logger.info(f"Transcribing: {audio_path}")
        try:
            with open(audio_path, "rb") as f:
                response = await self.client.audio.transcriptions.create(
                    model="whisper-1", file=f, language=language, response_format="verbose_json"
                )
            return {"text": response.text, "segments": [{"start": s.start, "end": s.end, "text": s.text} for s in response.segments], "language": response.language}
        except Exception as e:
            logger.warning(f"Whisper failed: {e}")
            return {"text": "", "segments": [], "language": language or "zh"}
    
    @with_retry(max_retries=3, base_delay=3.0)
    async def analyze_frames(self, frame_paths: List[str], prompt: str) -> str:
        logger.info(f"Analyzing {len(frame_paths)} frames")
        content = [{"type": "text", "text": prompt}]
        max_frames = 10
        if len(frame_paths) > max_frames:
            step = len(frame_paths) // max_frames
            frame_paths = frame_paths[::step][:max_frames]
        for path in frame_paths:
            if Path(path).exists():
                with open(path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
        response = await self.vlm_client.chat.completions.create(model=self.vlm_model, messages=[{"role": "user", "content": content}], max_tokens=4096)
        return response.choices[0].message.content
    
    @with_retry(max_retries=3, base_delay=3.0)
    async def generate_outline(self, transcript: str, language: str = "zh") -> dict:
        logger.info("Generating outline")
        max_chars = 10000
        if len(transcript) > max_chars:
            transcript = transcript[:max_chars] + "..."
        lang_name = "Chinese" if language.startswith("zh") else "English"
        prompt = f"Generate outline from transcript.\n\nTranscript:\n{transcript}\n\nReturn JSON: {{\"title\": str, \"sections\": [{{\"heading\": str, \"points\": [str]}}]}}"
        response = await self.client.chat.completions.create(model=self.model, messages=[{"role": "user", "content": prompt}], response_format={"type": "json_object"})
        return json.loads(response.choices[0].message.content)
    
    @with_retry(max_retries=3, base_delay=3.0)
    async def generate_note(self, outline: dict, context: str) -> str:
        logger.info("Generating note")
        prompt = f"Generate detailed video notes from outline and context.\n\nOutline:\n{json.dumps(outline, ensure_ascii=False, indent=2)}\n\nContext:\n{context}\n\nOutput in Markdown format:"
        response = await self.client.chat.completions.create(model=self.model, messages=[{"role": "user", "content": prompt}], max_tokens=8192)
        return response.choices[0].message.content
