"""Application config: loads config.yaml + environment variables.

Secrets come exclusively from .env / environment; config.yaml holds placeholders.
Compatible with legacy OPENAI_API_KEY / OPENAI_BASE_URL env vars.
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv_if_present(env_path: Path) -> None:
    if not env_path.exists():
        return
    try:
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)
    except Exception as exc:
        logger.warning("Failed to load .env (%s): %s", env_path, exc)


_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


def _expand_env(value: Any) -> Any:
    if isinstance(value, str):
        prev = None
        cur = value
        for _ in range(5):
            if prev == cur:
                break
            prev = cur

            def _sub(match: re.Match) -> str:
                name = match.group(1)
                default = match.group(2) if match.group(2) is not None else ""
                return os.environ.get(name, default)

            cur = _ENV_PATTERN.sub(_sub, cur)
        return cur
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    return value


@dataclass
class ProviderConfig:
    type: str = "openai"
    api_key: str = ""
    model: str = "gpt-4o-mini"
    base_url: str = "https://api.openai.com/v1"

    def to_dict(self):
        key = self.api_key
        return {
            "type": self.type, "model": self.model, "base_url": self.base_url,
            # 明文 key 绝不回传给客户端；留空表示保持当前配置
            "api_key": "", "api_key_set": bool(key),
            "api_key_masked": (key[:4] + "***" + key[-4:]) if len(key) > 12 else ("***" if key else ""),
        }

    def update(self, data: dict):
        if "type" in data and data["type"]:
            self.type = data["type"]
        if "model" in data and data["model"]:
            self.model = data["model"]
        if "base_url" in data and data["base_url"]:
            self.base_url = data["base_url"]
        if "api_key" in data and data["api_key"]:
            self.api_key = data["api_key"]


@dataclass
class ASRConfig:
    enabled: bool = False
    api_key: str = ""
    model: str = "whisper-1"
    base_url: str = "https://api.openai.com/v1"

    def to_dict(self):
        key = self.api_key
        return {
            "enabled": self.enabled, "model": self.model, "base_url": self.base_url,
            "api_key": "", "api_key_set": bool(key),
            "api_key_masked": (key[:4] + "***" + key[-4:]) if len(key) > 12 else ("***" if key else ""),
        }


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
    max_concurrent_tasks: int = 2


@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8000


@dataclass
class AppConfig:
    provider: ProviderConfig = field(default_factory=ProviderConfig)
    vlm: ProviderConfig = field(default_factory=ProviderConfig)
    asr: ASRConfig = field(default_factory=ASRConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    server: ServerConfig = field(default_factory=ServerConfig)

    def get_model_config(self) -> dict:
        return {
            "llm": self.provider.to_dict(),
            "vlm": self.vlm.to_dict(),
            "asr": self.asr.to_dict(),
        }

    def update_model_config(self, data: dict) -> dict:
        if "llm" in data:
            self.provider.update(data["llm"])
        if "vlm" in data:
            self.vlm.update(data["vlm"])
        if "asr" in data:
            d = data["asr"]
            if "enabled" in d:
                self.asr.enabled = bool(d["enabled"])
            if "model" in d and d["model"]:
                self.asr.model = d["model"]
            if "base_url" in d and d["base_url"]:
                self.asr.base_url = d["base_url"]
            if "api_key" in d and d["api_key"]:
                self.asr.api_key = d["api_key"]
        self.save()
        return self.get_model_config()

    def save(self, config_path=None):
        cfg_file = Path(config_path) if config_path else (_PROJECT_ROOT / 'config.yaml')
        if not cfg_file.exists():
            logger.warning('config.yaml not found, skipping save')
            return
        lines = cfg_file.read_text(encoding='utf-8').splitlines()

        def _set_val(lines, section, key, value):
            in_sec = False
            sec_indent = -1
            for i, line in enumerate(lines):
                stripped = line.lstrip()
                indent = len(line) - len(stripped)
                if stripped.startswith(section + ':'):
                    in_sec = True
                    sec_indent = indent
                    continue
                if in_sec:
                    if indent <= sec_indent and stripped and not stripped.startswith('#'):
                        break
                    if stripped.startswith(key + ':') and indent > sec_indent:
                        old_v = stripped[len(key)+1:].strip()
                        if old_v.startswith('"') and '}{' in old_v:
                            return
                        if old_v.startswith(chr(36)):
                            return
                        prefix = line[:len(line) - len(stripped)]
                        lines[i] = prefix + key + ': ' + str(value)
                        return

        # 安全：api_key 一律不写回 config.yaml，保留文件中的 ${ENV} 占位符，
        # 避免明文密钥落到被 Git 跟踪 / rw 挂载的配置文件里。
        for section, cfg_obj in [('provider', self.provider), ('vlm', self.vlm)]:
            _set_val(lines, section, 'type', cfg_obj.type)
            _set_val(lines, section, 'model', cfg_obj.model)
            _set_val(lines, section, 'base_url', cfg_obj.base_url)

        _set_val(lines, 'asr', 'enabled', str(self.asr.enabled).lower())
        _set_val(lines, 'asr', 'model', self.asr.model)
        _set_val(lines, 'asr', 'base_url', self.asr.base_url)

        for k in ('segment_duration', 'keyframe_interval', 'max_retries', 'retry_delay', 'max_concurrent_tasks'):
            _set_val(lines, 'processing', k, getattr(self.processing, k))

        cfg_file.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        logger.info('Config saved to %s', cfg_file)


    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "AppConfig":
        _load_dotenv_if_present(_PROJECT_ROOT / ".env")

        cfg_file = Path(config_path) if config_path else (_PROJECT_ROOT / "config.yaml")
        raw: dict = {}
        if cfg_file.exists():
            with cfg_file.open("r", encoding="utf-8") as fh:
                raw = yaml.safe_load(fh) or {}
            raw = _expand_env(raw)

        config = cls()

        if "provider" in raw and isinstance(raw["provider"], dict):
            config.provider = ProviderConfig(**{
                **config.provider.__dict__,
                **{k: v for k, v in raw["provider"].items() if v not in (None, "")},
            })
        if "vlm" in raw and isinstance(raw["vlm"], dict):
            config.vlm = ProviderConfig(**{
                **config.provider.__dict__,
                **{k: v for k, v in raw["vlm"].items() if v not in (None, "")},
            })
        else:
            config.vlm = ProviderConfig(**config.provider.__dict__)

        if "asr" in raw and isinstance(raw["asr"], dict):
            data = dict(raw["asr"])
            data.setdefault("api_key", config.provider.api_key)
            data.setdefault("base_url", config.provider.base_url)
            config.asr = ASRConfig(**{
                k: v for k, v in data.items()
                if k in {"enabled", "api_key", "model", "base_url"}
            })

        if "storage" in raw and isinstance(raw["storage"], dict):
            config.storage = StorageConfig(**{**config.storage.__dict__, **raw["storage"]})

        if "processing" in raw and isinstance(raw["processing"], dict):
            proc = dict(raw["processing"])
            for int_key in ("segment_duration", "keyframe_interval", "max_retries", "max_concurrent_tasks"):
                if int_key in proc:
                    try:
                        proc[int_key] = int(proc[int_key])
                    except (TypeError, ValueError):
                        proc.pop(int_key)
            if "retry_delay" in proc:
                try:
                    proc["retry_delay"] = float(proc["retry_delay"])
                except (TypeError, ValueError):
                    proc.pop("retry_delay")
            config.processing = ProcessingConfig(**{**config.processing.__dict__, **proc})

        if "server" in raw and isinstance(raw["server"], dict):
            srv = dict(raw["server"])
            if "port" in srv:
                try:
                    srv["port"] = int(srv["port"])
                except (TypeError, ValueError):
                    srv.pop("port")
            config.server = ServerConfig(**{**config.server.__dict__, **srv})

        # Legacy env var compat
        legacy_key = os.getenv("OPENAI_API_KEY")
        if legacy_key and not config.provider.api_key:
            config.provider.api_key = legacy_key
            if not config.vlm.api_key:
                config.vlm.api_key = legacy_key
        legacy_base = os.getenv("OPENAI_BASE_URL")
        if legacy_base and config.provider.base_url == "https://api.openai.com/v1":
            config.provider.base_url = legacy_base

        asr_env = os.getenv("ASR_ENABLED")
        if asr_env is not None:
            config.asr.enabled = asr_env.strip().lower() in {"1", "true", "yes", "on"}

        max_conc = os.getenv("MAX_CONCURRENT_TASKS")
        if max_conc:
            try:
                config.processing.max_concurrent_tasks = max(1, int(max_conc))
            except ValueError:
                pass

        return config


config = AppConfig.load()
