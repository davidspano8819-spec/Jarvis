"""Orchestrator: turns user input into a streamed, sentence-chunked response."""

from __future__ import annotations

import asyncio
import logging

from jarvis.brain.brain import Brain
from jarvis.brain.llm import LLMError
from jarvis.core.events import (
    ErrorOccurred,
    EventBus,
    ResponseDelta,
    ResponseDone,
    ResponseSentence,
    UserInput,
)
from jarvis.core.sentences import SentenceChunker
from jarvis.core.state import State, StateMachine

log = logging.getLogger(__name__)

GENERIC_ERROR = "Qualcosa non ha funzionato nel mio ragionamento, {title}. Riprovi tra un attimo."


class Orchestrator:
    def __init__(self, bus: EventBus, state: StateMachine, brain: Brain, *, title: str) -> None:
        self._bus = bus
        self._state = state
        self._brain = brain
        self._title = title
        self._lock = asyncio.Lock()
        self._current: asyncio.Task[None] | None = None
        bus.subscribe(UserInput, self.handle)

    async def handle(self, event: UserInput) -> None:
        text = event.text.strip()
        if not text:
            return
        async with self._lock:
            self._current = asyncio.create_task(self._respond(text))
            try:
                await self._current
            except asyncio.CancelledError:
                log.info("response interrupted")
            finally:
                self._current = None
                await self._state.transition(State.IDLE)

    def interrupt(self) -> bool:
        """Cancel the response in progress (barge-in). Returns True if one was running."""
        if self._current and not self._current.done():
            self._current.cancel()
            return True
        return False

    async def _respond(self, text: str) -> None:
        await self._state.transition(State.THINKING)
        chunker = SentenceChunker()
        full = ""
        try:
            async for delta in self._brain.respond(text):
                full += delta
                await self._bus.publish(ResponseDelta(text=delta))
                for sentence in chunker.feed(delta):
                    await self._speak(sentence)
            for sentence in chunker.flush():
                await self._speak(sentence)
        except LLMError as exc:
            log.warning(
                "llm error",
                extra={"cause": type(exc.__cause__).__name__, "retryable": exc.retryable},
            )
            await self._fail("brain", exc.user_message)
            return
        except Exception:  # never let one bad turn kill the main loop
            log.exception("unexpected error while responding")
            await self._fail("brain", GENERIC_ERROR.format(title=self._title))
            return
        result = self._brain.last_result
        await self._bus.publish(
            ResponseDone(
                text=full,
                model=result.model if result else "",
                stop_reason=result.stop_reason if result else None,
            )
        )

    async def _speak(self, sentence: str) -> None:
        await self._state.transition(State.SPEAKING)
        await self._bus.publish(ResponseSentence(text=sentence))

    async def _fail(self, module: str, message: str) -> None:
        await self._bus.publish(ErrorOccurred(module=module, message=message))
