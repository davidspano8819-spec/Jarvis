"""The brain: routes a request, streams Claude's answer, keeps short-term memory."""

from __future__ import annotations

import logging
from collections import deque
from collections.abc import AsyncIterator
from typing import Any

from jarvis.brain.llm import LLMBackend, StreamResult
from jarvis.brain.persona import Persona
from jarvis.brain.router import ModelRouter
from jarvis.core.events import EventBus, ModelSelected

log = logging.getLogger(__name__)

REFUSAL_REPLY = "Temo di non poterla aiutare con questa richiesta, {title}."
TRUNCATED_SUFFIX = " Mi fermo qui: la risposta sarebbe troppo lunga per essere letta."


class Brain:
    def __init__(
        self,
        backend: LLMBackend,
        persona: Persona,
        router: ModelRouter,
        bus: EventBus,
        *,
        title: str,
        history_turns: int,
    ) -> None:
        self._backend = backend
        self._persona = persona
        self._router = router
        self._bus = bus
        self._title = title
        self._history: deque[tuple[str, str]] = deque(maxlen=history_turns)
        self.last_result: StreamResult | None = None

    def reset(self) -> None:
        self._history.clear()

    @property
    def history(self) -> list[tuple[str, str]]:
        return list(self._history)

    def _messages(self, text: str) -> list[dict[str, Any]]:
        # Text-only history keeps the conversation valid across model switches.
        messages: list[dict[str, Any]] = []
        for user, assistant in self._history:
            messages.append({"role": "user", "content": user})
            messages.append({"role": "assistant", "content": assistant})
        messages.append({"role": "user", "content": text})
        return messages

    async def respond(self, text: str) -> AsyncIterator[str]:
        route = self._router.route(text)
        await self._bus.publish(
            ModelSelected(tier=route.tier, model=route.model.model, reason=route.reason)
        )
        result = StreamResult(model=route.model.model)
        self.last_result = result
        async for delta in self._backend.stream(
            route.model, self._persona.system_blocks(), self._messages(text), result
        ):
            yield delta

        log.info(
            "llm turn",
            extra={
                "model": result.model,
                "tier": route.tier,
                "stop_reason": result.stop_reason,
                **result.usage,
            },
        )
        if result.stop_reason == "refusal":
            reply = REFUSAL_REPLY.format(title=self._title)
            result.text = reply
            yield reply
            return  # refused turns are not kept in memory
        if result.stop_reason == "max_tokens":
            result.text += TRUNCATED_SUFFIX
            yield TRUNCATED_SUFFIX
        if result.text.strip():
            self._history.append((text, result.text))
