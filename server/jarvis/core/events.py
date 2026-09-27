"""Async in-process event bus decoupling Jarvis modules."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, TypeVar

log = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class Event:
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, kw_only=True)
class UserInput(Event):
    text: str
    source: str = "cli"


@dataclass(frozen=True, kw_only=True)
class StateChanged(Event):
    previous: str
    current: str


@dataclass(frozen=True, kw_only=True)
class ModelSelected(Event):
    tier: str
    model: str
    reason: str


@dataclass(frozen=True, kw_only=True)
class ResponseDelta(Event):
    text: str


@dataclass(frozen=True, kw_only=True)
class ResponseSentence(Event):
    """A complete sentence, ready to be spoken by the TTS."""

    text: str


@dataclass(frozen=True, kw_only=True)
class ResponseDone(Event):
    text: str
    model: str
    stop_reason: str | None = None


@dataclass(frozen=True, kw_only=True)
class ErrorOccurred(Event):
    module: str
    message: str


E = TypeVar("E", bound=Event)
Handler = Callable[[Any], Awaitable[None]]


class EventBus:
    """Publish/subscribe by event type. A failing handler never breaks the others."""

    def __init__(self) -> None:
        self._handlers: dict[type[Event], list[Handler]] = defaultdict(list)

    def subscribe(self, event_type: type[E], handler: Callable[[E], Awaitable[None]]) -> None:
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: type[E], handler: Callable[[E], Awaitable[None]]) -> None:
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    async def publish(self, event: Event) -> None:
        handlers = [
            h
            for event_type, hs in self._handlers.items()
            if isinstance(event, event_type)
            for h in hs
        ]
        if not handlers:
            return
        results = await asyncio.gather(*(h(event) for h in handlers), return_exceptions=True)
        for handler, result in zip(handlers, results, strict=True):
            if isinstance(result, Exception):
                log.error(
                    "event handler failed",
                    extra={"event": type(event).__name__, "handler": repr(handler)},
                    exc_info=result,
                )
