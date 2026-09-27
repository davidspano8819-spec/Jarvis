"""Wire the modules together. Every interface (CLI, API, Telegram) starts from here."""

from __future__ import annotations

from dataclasses import dataclass

from jarvis.brain.brain import Brain
from jarvis.brain.llm import AnthropicBackend, LLMBackend
from jarvis.brain.persona import Persona
from jarvis.brain.router import ModelRouter
from jarvis.config import Settings
from jarvis.core.events import EventBus
from jarvis.core.orchestrator import Orchestrator
from jarvis.core.state import StateMachine


@dataclass
class Jarvis:
    settings: Settings
    bus: EventBus
    state: StateMachine
    brain: Brain
    orchestrator: Orchestrator


def build_jarvis(
    settings: Settings, backend: LLMBackend | None = None, api_key: str | None = None
) -> Jarvis:
    bus = EventBus()
    state = StateMachine(bus)
    persona = Persona(settings.resolve(settings.brain.persona_path), settings.user)
    brain = Brain(
        backend or AnthropicBackend(api_key, settings.brain.request_timeout_s),
        persona,
        ModelRouter(settings.brain),
        bus,
        title=settings.user.title,
        history_turns=settings.brain.history_turns,
    )
    orchestrator = Orchestrator(bus, state, brain, title=settings.user.title)
    return Jarvis(settings, bus, state, brain, orchestrator)
