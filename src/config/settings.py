"""应用配置"""
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import yaml

@dataclass
class ProviderConfig:
    type: str = "openai"
    api_key: str = ""
    model: str = "gpt-4o"
    base_url: str = "https://api.openai.com/v1"

@dataclass
class StorageConfig:
    db_path: str = "./data/db/videonote.db"
    upload_dir: str = "./data/uploads"
    output_dir: str = "./data/output"

@dataclass
class ProcessingConfig:
    segment_duration: int = 300
    keyframe_interval: int = 30
    max_retries: int = 3
    retry_delay: float = 2.0

@dataclass
class AppConfig:
    provider: ProviderConfig = field(default_factory=ProviderConfig)
    vlm: ProviderConfig = field(default_factory=ProviderConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    
    @classmethod
    def load(cls, config_path: str = "config.yaml") -> "AppConfig":
        """从配置文件加载"""
        config = cls()
        
        if Path(config_path).exists():
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            
            if "provider" in data:
                config.provider = ProviderConfig(**data["provider"])
            if "vlm" in data:
                config.vlm = ProviderConfig(**data["vlm"])
            else:
                config.vlm = config.provider
            if "storage" in data:
                config.storage = StorageConfig(**data["storage"])
            if "processing" in data:
                config.processing = ProcessingConfig(**data["processing"])
        
        # 环境变量覆盖
        if os.getenv("OPENAI_API_KEY"):
            config.provider.api_key = os.getenv("OPENAI_API_KEY")
        if os.getenv("OPENAI_BASE_URL"):
            config.provider.base_url = os.getenv("OPENAI_BASE_URL")
        
        return config

# 全局配置实例
config = AppConfig.load()
