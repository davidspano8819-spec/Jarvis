"""Text CLI: talk to Jarvis from the terminal, with streamed answers."""

from __future__ import annotations

import asyncio
import sys

from jarvis.app import Jarvis
from jarvis.core.events import ErrorOccurred, ModelSelected, ResponseDelta, ResponseDone, UserInput

DIM, CYAN, RED, RESET = "\033[2m", "\033[36m", "\033[31m", "\033[0m"
EXIT_WORDS = {"/esci", "/exit", "esci", "exit", "quit"}
HELP = (
    f"{DIM}Comandi: /reset (dimentica la conversazione), /modello (mostra i modelli), "
    f"/esci. Aggiunga «pensaci bene» per il ragionamento approfondito.{RESET}"
)


class Cli:
    def __init__(self, jarvis: Jarvis, *, show_model: bool = True) -> None:
        self._jarvis = jarvis
        self._show_model = show_model
        self._started = False
        bus = jarvis.bus
        bus.subscribe(ModelSelected, self._on_model)
        bus.subscribe(ResponseDelta, self._on_delta)
        bus.subscribe(ResponseDone, self._on_done)
        bus.subscribe(ErrorOccurred, self._on_error)

    async def _on_model(self, event: ModelSelected) -> None:
        if self._show_model:
            print(f"{DIM}[{event.tier} · {event.model} · {event.reason}]{RESET}")

    async def _on_delta(self, event: ResponseDelta) -> None:
        if not self._started:
            sys.stdout.write(f"{CYAN}JARVIS:{RESET} ")
            self._started = True
        sys.stdout.write(event.text)
        sys.stdout.flush()

    async def _on_done(self, event: ResponseDone) -> None:
        print("\n")
        self._started = False

    async def _on_error(self, event: ErrorOccurred) -> None:
        prefix = "\n" if self._started else ""
        print(f"{prefix}{RED}JARVIS:{RESET} {event.message}\n")
        self._started = False

    def _handle_command(self, text: str) -> bool:
        if text == "/reset":
            self._jarvis.brain.reset()
            print(f"{DIM}Conversazione dimenticata.{RESET}\n")
        elif text == "/modello":
            for tier, cfg in self._jarvis.settings.brain.models.items():
                print(f"{DIM}{tier}: {cfg.model}{RESET}")
            print()
        elif text in {"/aiuto", "/help"}:
            print(HELP + "\n")
        else:
            return False
        return True

    async def run(self) -> None:
        title = self._jarvis.settings.user.title
        print(f"{CYAN}J.A.R.V.I.S.{RESET} in linea. Come posso esserle utile, {title}?")
        print(HELP + "\n")
        while True:
            try:
                text = (await asyncio.to_thread(input, "Lei: ")).strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not text:
                continue
            if text.lower() in EXIT_WORDS:
                break
            if self._handle_command(text):
                continue
            try:
                await self._jarvis.bus.publish(UserInput(text=text, source="cli"))
            except KeyboardInterrupt:
                self._jarvis.orchestrator.interrupt()
        print(f"{DIM}Buona giornata, {title}.{RESET}")
