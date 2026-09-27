"""Load and validate configuration from config.yaml and secrets from .env."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

Effort = Literal["low", "medium", "high", "xhigh", "max"]
Tier = Literal["fast", "smart", "deep"]

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class UserConfig(BaseModel):
    title: str = "Signore"
    name: str = ""
    location: str = "Italia"
    timezone: str = "Europe/Rome"
    language: str = "it"


class ModelConfig(BaseModel):
    model: str
    max_tokens: int = Field(default=1024, gt=0)
    thinking: bool = False
    effort: Effort | None = None


class RouterConfig(BaseModel):
    deep_triggers: list[str] = Field(default_factory=lambda: ["pensaci bene"])
    smart_triggers: list[str] = Field(default_factory=list)
    smart_min_words: int = 30


class BrainConfig(BaseModel):
    persona_path: Path = Path("server/jarvis/brain/persona.md")
    history_turns: int = Field(default=12, ge=1)
    request_timeout_s: float = 60
    models: dict[Tier, ModelConfig]
    router: RouterConfig = Field(default_factory=RouterConfig)


class LoggingConfig(BaseModel):
    level: str = "INFO"
    file: Path | None = Path("logs/jarvis.log")


class Settings(BaseModel):
    user: UserConfig = Field(default_factory=UserConfig)
    brain: BrainConfig
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    root: Path = PROJECT_ROOT

    def resolve(self, path: Path) -> Path:
        """Resolve a config-relative path against the project root."""
        return path if path.is_absolute() else self.root / path


class Secrets(BaseModel):
    anthropic_api_key: str | None = None


def load_settings(config_path: Path | None = None) -> Settings:
    path = config_path or Path(os.environ.get("JARVIS_CONFIG", PROJECT_ROOT / "config.yaml"))
    with path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    return Settings.model_validate({**raw, "root": path.resolve().parent})


def load_secrets(env_path: Path | None = None) -> Secrets:
    load_dotenv(env_path or PROJECT_ROOT / ".env", override=False)
    return Secrets(anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY") or None)
