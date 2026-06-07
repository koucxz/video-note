"""Model configuration API."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..core.engine import get_engine

router = APIRouter()


class ModelUpdate(BaseModel):
    llm: Optional[dict] = None
    vlm: Optional[dict] = None
    asr: Optional[dict] = None


@router.get("/api/config/models", tags=["config"],
    summary="Get model configuration",
    description="Get the current AI model settings (LLM, VLM, ASR).")
async def get_model_config():
    engine = get_engine()
    return engine.config.get_model_config()


@router.put("/api/config/models", tags=["config"],
    summary="Update model configuration",
    description="Update AI model settings. Changes take effect immediately.")
async def update_model_config(data: ModelUpdate):
    engine = get_engine()
    update_data = data.model_dump(exclude_none=True)
    result = engine.config.update_model_config(update_data)
    engine.ai = engine._init_ai_provider(engine.config)
    return result
