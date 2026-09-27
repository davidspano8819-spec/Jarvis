"""Assistant state machine: idle → listening → thinking → speaking."""

from __future__ import annotations

from enum import StrEnum

from jarvis.core.events import EventBus, StateChanged


class State(StrEnum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"


# Any state may fall back to IDLE (errors, cancellations); SPEAKING → LISTENING is barge-in.
_ALLOWED: dict[State, set[State]] = {
    State.IDLE: {State.LISTENING, State.THINKING},
    State.LISTENING: {State.THINKING, State.IDLE},
    State.THINKING: {State.SPEAKING, State.IDLE},
    State.SPEAKING: {State.LISTENING, State.THINKING, State.IDLE},
}


class InvalidTransition(RuntimeError):
    pass


class StateMachine:
    def __init__(self, bus: EventBus) -> None:
        self._bus = bus
        self._state = State.IDLE

    @property
    def state(self) -> State:
        return self._state

    async def transition(self, new: State) -> None:
        if new == self._state:
            return
        if new not in _ALLOWED[self._state]:
            raise InvalidTransition(f"{self._state} → {new}")
        previous, self._state = self._state, new
        await self._bus.publish(StateChanged(previous=previous.value, current=new.value))
