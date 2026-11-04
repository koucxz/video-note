"""Settings API - general settings and provider management."""
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from ..core.engine import get_engine

router = APIRouter()

# Provider storage file
_PROVIDERS_FILE = Path("./data/db/providers.json")


def _load_providers() -> list:
    if _PROVIDERS_FILE.exists():
        try:
            return json.loads(_PROVIDERS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save_providers(providers: list):
    _PROVIDERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _PROVIDERS_FILE.write_text(json.dumps(providers, ensure_ascii=False, indent=2), encoding="utf-8")


def _public_provider(p: dict) -> dict:
    """对外视图：剔除明文 api_key，只保留掩码与是否已配置。"""
    key = p.get("api_key") or ""
    out = {k: v for k, v in p.items() if k != "api_key"}
    out["api_key_set"] = bool(key)
    out["api_key_masked"] = "****" if key else ""
    return out


@router.get("/api/settings", tags=["settings"])
async def get_settings():
    engine = get_engine()
    cfg = engine.config
    return {
        "app_name": "VideoNote",
        "version": "1.2.0",
        "language": getattr(getattr(cfg, "language", None), "default", "zh"),
        "max_concurrent_tasks": cfg.processing.max_concurrent_tasks,
        "keyframe_interval": cfg.processing.keyframe_interval,
        "segment_duration": cfg.processing.segment_duration,
        "provider_type": cfg.provider.type,
        "provider_model": cfg.provider.model,
        "asr_enabled": cfg.asr.enabled,
    }


@router.put("/api/settings", tags=["settings"])
async def update_settings(body: dict):
    engine = get_engine()
    cfg = engine.config
    if "max_concurrent_tasks" in body:
        cfg.processing.max_concurrent_tasks = max(1, min(6, int(body["max_concurrent_tasks"])))
        engine.update_concurrency(cfg.processing.max_concurrent_tasks)
    if "keyframe_interval" in body:
        cfg.processing.keyframe_interval = max(10, min(120, int(body["keyframe_interval"])))
    if "segment_duration" in body:
        cfg.processing.segment_duration = max(60, min(1800, int(body["segment_duration"])))
    if "language" in body:
        if hasattr(cfg, "language"): cfg.language.default = body["language"]
    if "asr_enabled" in body:
        cfg.asr.enabled = bool(body["asr_enabled"])
    return {"message": "Settings updated"}


# Provider management

class ProviderCreate(BaseModel):
    name: str
    type: str = "openai"
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    vlm_model: str = ""
    asr_model: str = ""
    is_active: bool = False


class ProviderUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    vlm_model: Optional[str] = None
    asr_model: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/api/providers", tags=["providers"])
async def get_providers():
    return [_public_provider(p) for p in _load_providers()]


@router.post("/api/providers", tags=["providers"])
async def add_provider(data: ProviderCreate):
    import uuid
    providers = _load_providers()
    provider = {
        "id": str(uuid.uuid4())[:12],
        "name": data.name,
        "type": data.type,
        "api_key": data.api_key,
        "base_url": data.base_url,
        "model": data.model,
        "vlm_model": data.vlm_model,
        "asr_model": data.asr_model,
        "is_active": data.is_active,
    }
    providers.append(provider)
    _save_providers(providers)
    return _public_provider(provider)


@router.put("/api/providers/{provider_id}", tags=["providers"])
async def update_provider(provider_id: str, data: ProviderUpdate):
    providers = _load_providers()
    for p in providers:
        if p["id"] == provider_id:
            for k, v in data.model_dump(exclude_none=True).items():
                p[k] = v
            _save_providers(providers)
            return _public_provider(p)
    raise HTTPException(404, "Provider not found")


@router.delete("/api/providers/{provider_id}", tags=["providers"])
async def delete_provider(provider_id: str):
    providers = _load_providers()
    providers = [p for p in providers if p["id"] != provider_id]
    _save_providers(providers)
    return {"message": "Deleted"}


@router.post("/api/providers/{provider_id}/activate", tags=["providers"])
async def activate_provider(provider_id: str):
    providers = _load_providers()
    for p in providers:
        if p["id"] == provider_id:
            # Deactivate all, activate this one
            for pp in providers:
                pp["is_active"] = pp["id"] == provider_id
            _save_providers(providers)
            # Apply to engine config
            engine = get_engine()
            engine.config.provider.type = p["type"]
            engine.config.provider.api_key = p["api_key"]
            engine.config.provider.base_url = p["base_url"]
            engine.config.provider.model = p["model"]
            engine.ai = engine._init_ai_provider(engine.config)
            return {"message": f"Activated provider: {p['name']}"}
    raise HTTPException(404, "Provider not found")
