from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from jarvis.app import Jarvis, build_jarvis
from jarvis.brain.llm import LLMError, StreamResult
from jarvis.config import ModelConfig, Settings
from jarvis.core.events import (
    ErrorOccurred,
    Event,
    ModelSelected,
    ResponseDone,
    ResponseSentence,
    StateChanged,
    UserInput,
)
from jarvis.core.state import State
from tests.conftest import FakeBackend


def record(jarvis: Jarvis) -> list[Event]:
    events: list[Event] = []

    async def on_event(e: Event) -> None:
        events.append(e)

    jarvis.bus.subscribe(Event, on_event)
    return events


async def test_full_turn(jarvis: Jarvis) -> None:
    events = record(jarvis)
    await jarvis.bus.publish(UserInput(text="Buongiorno"))

    states = [(e.previous, e.current) for e in events if isinstance(e, StateChanged)]
    assert states == [("idle", "thinking"), ("thinking", "speaking"), ("speaking", "idle")]
    assert [e.text for e in events if isinstance(e, ResponseSentence)] == [
        "Buongiorno, Signore.",
        "Tutto bene.",
    ]
    selected = next(e for e in events if isinstance(e, ModelSelected))
    assert selected.tier == "fast"
    done = next(e for e in events if isinstance(e, ResponseDone))
    assert done.text == "Buongiorno, Signore. Tutto bene."
    assert jarvis.state.state == State.IDLE


async def test_llm_error_is_reported_and_loop_survives(settings: Settings) -> None:
    backend = FakeBackend(chunks=[], error=LLMError("Rete assente."))
    jarvis = build_jarvis(settings, backend=backend)
    events = record(jarvis)
    await jarvis.bus.publish(UserInput(text="ciao"))
    errors = [e for e in events if isinstance(e, ErrorOccurred)]
    assert [e.message for e in errors] == ["Rete assente."]
    assert jarvis.state.state == State.IDLE

    backend.error = None
    backend.chunks = ["Eccomi."]
    await jarvis.bus.publish(UserInput(text="ciao di nuovo"))
    assert any(isinstance(e, ResponseDone) for e in events)


async def test_unexpected_error_does_not_crash(settings: Settings) -> None:
    jarvis = build_jarvis(settings, backend=FakeBackend(chunks=["A"], error=KeyError("x")))
    events = record(jarvis)
    await jarvis.bus.publish(UserInput(text="ciao"))
    assert any(isinstance(e, ErrorOccurred) for e in events)
    assert jarvis.state.state == State.IDLE


class SlowBackend:
    async def stream(
        self,
        model: ModelConfig,
        system: list[dict[str, Any]],
        messages: list[dict[str, Any]],
        result: StreamResult,
    ) -> AsyncIterator[str]:
        yield "Inizio una lunga risposta. "
        await asyncio.sleep(10)
        yield "Mai detto."


async def test_interrupt_cancels_response(settings: Settings) -> None:
    jarvis = build_jarvis(settings, backend=SlowBackend())
    events = record(jarvis)
    task = asyncio.create_task(jarvis.bus.publish(UserInput(text="parla")))
    await asyncio.sleep(0.05)
    assert jarvis.orchestrator.interrupt() is True
    await asyncio.wait_for(task, 1)
    assert not any(isinstance(e, ResponseDone) for e in events)
    assert jarvis.state.state == State.IDLE
    assert jarvis.brain.history == []
