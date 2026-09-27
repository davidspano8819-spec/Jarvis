from __future__ import annotations

import pytest

from jarvis.core.events import Event, EventBus, StateChanged, UserInput
from jarvis.core.sentences import SentenceChunker
from jarvis.core.state import InvalidTransition, State, StateMachine


async def test_bus_delivers_by_type_and_subclass() -> None:
    bus = EventBus()
    got: list[str] = []

    async def on_input(e: UserInput) -> None:
        got.append(f"input:{e.text}")

    async def on_any(e: Event) -> None:
        got.append(f"any:{type(e).__name__}")

    bus.subscribe(UserInput, on_input)
    bus.subscribe(Event, on_any)
    await bus.publish(UserInput(text="ciao"))
    assert sorted(got) == ["any:UserInput", "input:ciao"]


async def test_bus_isolates_failing_handler() -> None:
    bus = EventBus()
    got: list[str] = []

    async def broken(e: UserInput) -> None:
        raise RuntimeError("boom")

    async def healthy(e: UserInput) -> None:
        got.append(e.text)

    bus.subscribe(UserInput, broken)
    bus.subscribe(UserInput, healthy)
    await bus.publish(UserInput(text="ok"))  # must not raise
    assert got == ["ok"]


async def test_state_machine_publishes_and_rejects_invalid() -> None:
    bus = EventBus()
    changes: list[tuple[str, str]] = []

    async def on_change(e: StateChanged) -> None:
        changes.append((e.previous, e.current))

    bus.subscribe(StateChanged, on_change)
    sm = StateMachine(bus)
    await sm.transition(State.LISTENING)
    await sm.transition(State.THINKING)
    await sm.transition(State.SPEAKING)
    await sm.transition(State.LISTENING)  # barge-in
    assert changes[-1] == ("speaking", "listening")
    with pytest.raises(InvalidTransition):
        await sm.transition(State.SPEAKING)


@pytest.mark.parametrize(
    ("chunks", "expected"),
    [
        (
            ["Buongiorno, Signore. Sono le ", "15 e 30. Tutto bene?"],
            ["Buongiorno, Signore.", "Sono le 15 e 30.", "Tutto bene?"],
        ),
        (["Il Sig. Rossi la ", "aspetta. Arrivo!"], ["Il Sig. Rossi la aspetta.", "Arrivo!"]),
        (["Costa 3.5 euro, ecc. e altro. Fine"], ["Costa 3.5 euro, ecc. e altro.", "Fine"]),
        (["Ne parla M. Rossi. Bene…  poi"], ["Ne parla M. Rossi.", "Bene…", "poi"]),
    ],
)
def test_sentence_chunker(chunks: list[str], expected: list[str]) -> None:
    chunker = SentenceChunker()
    out: list[str] = []
    for c in chunks:
        out.extend(chunker.feed(c))
    out.extend(chunker.flush())
    assert out == expected


def test_sentence_emitted_before_stream_ends() -> None:
    chunker = SentenceChunker()
    assert chunker.feed("Certo, Signore.") == []  # no trailing space yet: may continue
    assert chunker.feed(" Ecco") == ["Certo, Signore."]
