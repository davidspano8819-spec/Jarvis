from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from jarvis.app import Jarvis
from jarvis.brain.llm import build_request
from jarvis.brain.persona import Persona
from jarvis.brain.router import ModelRouter
from jarvis.config import Settings
from tests.conftest import FakeBackend


@pytest.mark.parametrize(
    ("text", "tier"),
    [
        ("Che ore sono?", "fast"),
        ("Buongiorno Jarvis", "fast"),
        ("Spiegami come funziona un mutuo", "smart"),
        ("Pianifica la mia settimana", "smart"),
        ("PENSACI BENE: conviene l'auto elettrica?", "deep"),
        ("parola " * 40, "smart"),
    ],
)
def test_router(settings: Settings, text: str, tier: str) -> None:
    route = ModelRouter(settings.brain).route(text)
    assert route.tier == tier
    assert route.model.model == settings.brain.models[route.tier].model


def test_router_uses_configured_model_ids(settings: Settings) -> None:
    models = {t: m.model for t, m in settings.brain.models.items()}
    assert models == {
        "fast": "claude-haiku-4-5",
        "smart": "claude-sonnet-5",
        "deep": "claude-opus-5-5",
    }


def test_build_request_per_tier(settings: Settings) -> None:
    fast = build_request(settings.brain.models["fast"], [], [])
    assert "thinking" not in fast and "output_config" not in fast
    deep = build_request(settings.brain.models["deep"], [], [])
    assert deep["thinking"] == {"type": "adaptive"}
    assert deep["output_config"] == {"effort": "high"}


def test_persona_and_context(settings: Settings) -> None:
    persona = Persona(settings.resolve(settings.brain.persona_path), settings.user)
    assert "Signore" in persona.text and "{title}" not in persona.text
    now = datetime(2026, 9, 27, 9, 5, tzinfo=ZoneInfo("Europe/Rome"))
    blocks = persona.system_blocks(now)
    assert blocks[0]["cache_control"] == {"type": "ephemeral"}
    assert "domenica 27 settembre 2026, ore 09:05" in blocks[1]["text"]
    assert "cache_control" not in blocks[1]


async def test_history_is_kept_and_trimmed(jarvis: Jarvis, backend: FakeBackend) -> None:
    brain = jarvis.brain
    for i in range(15):
        async for _ in brain.respond(f"domanda {i}"):
            pass
    assert len(brain.history) == jarvis.settings.brain.history_turns
    last_messages = backend.calls[-1]["messages"]
    assert last_messages[-1] == {"role": "user", "content": "domanda 14"}
    assert last_messages[0]["role"] == "user"
    brain.reset()
    assert brain.history == []


async def test_refusal_is_not_remembered(jarvis: Jarvis, backend: FakeBackend) -> None:
    backend.chunks, backend.stop_reason = [], "refusal"
    out = [d async for d in jarvis.brain.respond("richiesta")]
    assert "Temo di non poterla aiutare" in "".join(out)
    assert jarvis.brain.history == []
