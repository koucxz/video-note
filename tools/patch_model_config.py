import pathlib

# ===== 1. Backend: Add model config API =====
config_path = pathlib.Path(r"D:\code\video-note\src\config\settings.py")
t = config_path.read_text(encoding="utf-8")

# Add update methods to ProviderConfig
old_prov = '@dataclass\nclass ProviderConfig:\n    type: str = "openai"\n    api_key: str = ""\n    model: str = "gpt-4o-mini"\n    base_url: str = "https://api.openai.com/v1"'
new_prov = '@dataclass\nclass ProviderConfig:\n    type: str = "openai"\n    api_key: str = ""\n    model: str = "gpt-4o-mini"\n    base_url: str = "https://api.openai.com/v1"\n\n    def to_dict(self):\n        return {"type": self.type, "model": self.model, "base_url": self.base_url, "api_key_set": bool(self.api_key)}\n\n    def update(self, data: dict):\n        if "model" in data and data["model"]:\n            self.model = data["model"]\n        if "base_url" in data and data["base_url"]:\n            self.base_url = data["base_url"]\n        if "api_key" in data and data["api_key"]:\n            self.api_key = data["api_key"]'
t = t.replace(old_prov, new_prov, 1)

# Add to_dict to ASRConfig (find second base_url)
idx1 = t.find('class ASRConfig')
idx2 = t.find('base_url: str = "https://api.openai.com/v1"', idx1)
if idx2 > 0:
    insert = '\n\n    def to_dict(self):\n        return {"enabled": self.enabled, "model": self.model, "base_url": self.base_url, "api_key_set": bool(self.api_key)}'
    t = t[:idx2+len('base_url: str = "https://api.openai.com/v1"')] + insert + t[idx2+len('base_url: str = "https://api.openai.com/v1"'):]

# Add get/update methods to AppConfig
old_app = '    @classmethod\n    def load(cls, config_path: Optional[str] = None) -> "AppConfig":'
new_app = '    def get_model_config(self) -> dict:\n        return {\n            "llm": self.provider.to_dict(),\n            "vlm": self.vlm.to_dict(),\n            "asr": self.asr.to_dict(),\n        }\n\n    def update_model_config(self, data: dict) -> dict:\n        if "llm" in data:\n            self.provider.update(data["llm"])\n        if "vlm" in data:\n            self.vlm.update(data["vlm"])\n        if "asr" in data:\n            d = data["asr"]\n            if "enabled" in d:\n                self.asr.enabled = bool(d["enabled"])\n            if "model" in d and d["model"]:\n                self.asr.model = d["model"]\n            if "base_url" in d and d["base_url"]:\n                self.asr.base_url = d["base_url"]\n            if "api_key" in d and d["api_key"]:\n                self.asr.api_key = d["api_key"]\n        return self.get_model_config()\n\n    @classmethod\n    def load(cls, config_path: Optional[str] = None) -> "AppConfig":'
t = t.replace(old_app, new_app, 1)

config_path.write_text(t, encoding="utf-8")
print("settings.py done")

# ===== 2. Create model_config.py API =====
model_api = pathlib.Path(r"D:\code\video-note\src\api\model_config.py")
model_api.write_text('"""Model configuration API."\nfrom fastapi import APIRouter\nfrom ..core.engine import get_engine\n\nrouter = APIRouter()\n\n\n@router.get("/api/config/models")\nasync def get_model_config():\n    engine = get_engine()\n    return engine.config.get_model_config()\n\n\n@router.put("/api/config/models")\nasync def update_model_config(data: dict):\n    engine = get_engine()\n    result = engine.config.update_model_config(data)\n    engine.ai = engine._init_ai_provider(engine.config)\n    return result\n', encoding="utf-8")
print("model_config.py created")

# ===== 3. Register in api/__init__.py =====
api_init = pathlib.Path(r"D:\code\video-note\src\api\__init__.py")
t = api_init.read_text(encoding="utf-8")
if "model_config" not in t:
    t = t.replace(
        'from .storage import router as storage_router',
        'from .storage import router as storage_router\nfrom .model_config import router as model_config_router'
    )
    t = t.replace(
        '__all__ = ["upload_router", "task_router", "note_router", "storage_router"]',
        '__all__ = ["upload_router", "task_router", "note_router", "storage_router", "model_config_router"]'
    )
    api_init.write_text(t, encoding="utf-8")
    print("api/__init__.py done")

# ===== 4. Register in main.py =====
main_path = pathlib.Path(r"D:\code\video-note\src\main.py")
t = main_path.read_text(encoding="utf-8")
if "model_config_router" not in t:
    t = t.replace(
        'from .api import upload_router, task_router, note_router, storage_router',
        'from .api import upload_router, task_router, note_router, storage_router, model_config_router'
    )
    t = t.replace(
        'app.include_router(storage_router)',
        'app.include_router(storage_router)\napp.include_router(model_config_router)'
    )
    main_path.write_text(t, encoding="utf-8")
    print("main.py done")
