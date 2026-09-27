from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest

from jarvis.app import Jarvis, build_jarvis
from jarvis.brain.llm import StreamResult
from jarvis.config import ModelConfig, Settings, load_settings

ROOT = Path(__file__).resolve().parents[1]


class FakeBackend:
    """Streams scripted chunks; records every request it receives."""

    def __init__(
        self,
        chunks: list[str] | None = None,
        stop_reason: str = "end_turn",
        error: Exception | None = None,
    ) -> None:
        self.chunks = chunks if chunks is not None else ["Buongiorno, Signore. ", "Tutto bene."]
        self.stop_reason = stop_reason
        self.error = error
        self.calls: list[dict[str, Any]] = []

    async def stream(
        self,
        model: ModelConfig,
        system: list[dict[str, Any]],
        messages: list[dict[str, Any]],
        result: StreamResult,
    ) -> AsyncIterator[str]:
        self.calls.append({"model": model, "system": system, "messages": messages})
        for chunk in self.chunks:
            result.text += chunk
            yield chunk
        if self.error:
            raise self.error
        result.stop_reason = self.stop_reason
        result.model = model.model


@pytest.fixture
def settings() -> Settings:
    s = load_settings(ROOT / "config.yaml")
    s.logging.file = None
    return s


@pytest.fixture
def backend() -> FakeBackend:
    return FakeBackend()


@pytest.fixture
def jarvis(settings: Settings, backend: FakeBackend) -> Jarvis:
    return build_jarvis(settings, backend=backend)
